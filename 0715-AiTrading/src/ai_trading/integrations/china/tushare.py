"""通过官方 HTTP API 访问 Tushare，凭据仅发送给 HTTPS 官方端点。"""

from decimal import Decimal

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from ai_trading.integrations.china.common import number, shares, stock_code, trading_date
from ai_trading.integrations.market_data import (
    MarketBar,
    MarketDataProviderError,
    MarketDataProviderErrorKind,
    MarketDataRangeRequest,
    MarketDataRequest,
)


class _Params(BaseModel):
    ts_code: str
    start_date: str
    end_date: str


class _Query(BaseModel):
    api_name: str
    token: str
    params: _Params
    fields: str


class _Data(BaseModel):
    fields: list[str]
    items: list[list[str | int | float | None]]


class _Response(BaseModel):
    model_config = ConfigDict(extra="ignore")
    code: int
    msg: str | None = Field(default=None, repr=False)
    data: _Data | None = None


class TushareEodProvider:
    def __init__(self, api_token: SecretStr | None, client: httpx.Client) -> None:
        self._token = api_token
        self._client = client

    def fetch(self, request: MarketDataRequest) -> MarketBar:
        bars = self._fetch(
            MarketDataRangeRequest(
                symbol=request.symbol,
                provider_symbol=request.provider_symbol,
                start_date=request.trade_date,
                end_date=request.trade_date,
                currency=request.currency,
            ),
            adjusted=False,
        )
        if len(bars) != 1 or bars[0].trade_date != request.trade_date:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.NOT_FOUND, "Tushare 未返回目标交易日"
            )
        return bars[0]

    def fetch_range(self, request: MarketDataRangeRequest) -> tuple[MarketBar, ...]:
        return self._fetch(request, adjusted=True)

    def _query(self, api: str, code: str, request: MarketDataRangeRequest, fields: str) -> _Data:
        token = "" if self._token is None else self._token.get_secret_value().strip()
        if not token:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.CONFIGURATION, "未配置 TUSHARE_TOKEN"
            )
        body = _Query(
            api_name=api,
            token=token,
            params=_Params(
                ts_code=code,
                start_date=request.start_date.strftime("%Y%m%d"),
                end_date=request.end_date.strftime("%Y%m%d"),
            ),
            fields=fields,
        )
        response = self._client.post(
            "https://api.tushare.pro",
            content=body.model_dump_json(),
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        response.raise_for_status()
        result = _Response.model_validate_json(response.content)
        if result.code != 0:
            message = result.msg or ""
            if "权限" in message or "积分" in message:
                reason = "接口权限不足"
            elif "频" in message or "次数" in message:
                reason = "请求频率或额度受限"
            else:
                reason = "请求被拒绝，请检查 Token、权限或频率"
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.UPSTREAM,
                f"Tushare {reason} (api={api}, code={result.code})",
            )
        if result.data is None or result.data.fields != fields.split(","):
            raise ValueError("Tushare 字段顺序或数据结构无效")
        return result.data

    def _fetch(self, request: MarketDataRangeRequest, *, adjusted: bool) -> tuple[MarketBar, ...]:
        _, code = stock_code(request.symbol, request.currency)
        try:
            data = self._query("daily", code, request, "ts_code,trade_date,open,high,low,close,vol")
            bars: list[MarketBar] = []
            for row in data.items:
                if len(row) != 7 or row[0] != code:
                    raise ValueError("Tushare 证券或行长度不匹配")
                bars.append(
                    MarketBar(
                        symbol=request.symbol,
                        trade_date=trading_date(row[1]),
                        open=number(row[2]),
                        high=number(row[3]),
                        low=number(row[4]),
                        close=number(row[5]),
                        volume=shares(row[6]),
                        currency=request.currency,
                        source="tushare",
                    )
                )
            bars.sort(key=lambda bar: bar.trade_date)
            if adjusted and bars:
                bars = self._adjust(bars, code, request)
            return tuple(bars)
        except MarketDataProviderError:
            raise
        except Exception:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.INVALID_RESPONSE, "Tushare 网络请求或数据校验失败"
            ) from None

    def _adjust(
        self, bars: list[MarketBar], code: str, request: MarketDataRangeRequest
    ) -> list[MarketBar]:
        data = self._query("adj_factor", code, request, "ts_code,trade_date,adj_factor")
        factors: list[tuple[object, Decimal]] = []
        for row in data.items:
            if len(row) != 3 or row[0] != code or number(row[2]) <= 0:
                raise ValueError("复权因子无效")
            factors.append((trading_date(row[1]), number(row[2])))
        dates = tuple(item[0] for item in factors)
        if len(dates) != len(set(dates)) or any(bar.trade_date not in dates for bar in bars):
            raise ValueError("复权因子缺失或重复")
        base = next(factor for day, factor in factors if day == bars[-1].trade_date)
        result: list[MarketBar] = []
        for bar in bars:
            ratio = next(factor for day, factor in factors if day == bar.trade_date) / base
            result.append(
                MarketBar(
                    symbol=bar.symbol,
                    trade_date=bar.trade_date,
                    open=bar.open * ratio,
                    high=bar.high * ratio,
                    low=bar.low * ratio,
                    close=bar.close * ratio,
                    volume=bar.volume,
                    currency=bar.currency,
                    source=bar.source,
                )
            )
        return result
