"""Tiingo EOD 的同步 HTTPX 适配器。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, TypeAdapter, ValidationError

from .market_data import (
    MarketBar,
    MarketDataProviderError,
    MarketDataProviderErrorKind,
    MarketDataRangeRequest,
    MarketDataRequest,
)


class _TiingoPrice(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adj_open: Decimal | None = Field(default=None, alias="adjOpen")
    adj_high: Decimal | None = Field(default=None, alias="adjHigh")
    adj_low: Decimal | None = Field(default=None, alias="adjLow")
    adj_close: Decimal | None = Field(default=None, alias="adjClose")
    adj_volume: int | None = Field(default=None, alias="adjVolume")


_PRICE_LIST = TypeAdapter(list[_TiingoPrice])


class TiingoEodProvider:
    """只读取指定交易日, 不用临近日期静默补位。"""

    def __init__(
        self,
        api_token: SecretStr | None,
        client: httpx.Client,
        base_url: str = "https://api.tiingo.com",
    ) -> None:
        self._api_token = api_token
        self._client = client
        self._base_url = base_url.rstrip("/")

    def __repr__(self) -> str:
        return f"{type(self).__name__}(api_token=SecretStr('**********'))"

    def fetch(self, request: MarketDataRequest) -> MarketBar:
        bars = self._fetch_range(
            MarketDataRangeRequest(
                symbol=request.symbol,
                provider_symbol=request.provider_symbol,
                start_date=request.trade_date,
                end_date=request.trade_date,
                currency=request.currency,
            ),
            adjusted=False,
        )
        price = next((item for item in bars if item.trade_date == request.trade_date), None)
        if price is None:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.NOT_FOUND,
                "Tiingo 未返回目标交易日行情",
            )
        return price

    def fetch_range(self, request: MarketDataRangeRequest) -> tuple[MarketBar, ...]:
        return self._fetch_range(request, adjusted=True)

    def _fetch_range(
        self,
        request: MarketDataRangeRequest,
        *,
        adjusted: bool,
    ) -> tuple[MarketBar, ...]:
        token = self._read_token()
        url = f"{self._base_url}/tiingo/daily/{request.provider_symbol}/prices"
        try:
            response = self._client.get(
                url,
                params=(
                    ("startDate", request.start_date.isoformat()),
                    ("endDate", request.end_date.isoformat()),
                ),
                headers=(("Authorization", f"Token {token}"),),
            )
        except httpx.HTTPError as exc:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.UPSTREAM,
                "Tiingo 网络请求失败",
            ) from exc

        self._raise_for_status(response.status_code)
        try:
            prices = _PRICE_LIST.validate_json(response.content)
        except ValidationError as exc:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.INVALID_RESPONSE,
                "Tiingo 响应格式无效",
            ) from exc

        dates = tuple(item.date.date() for item in prices)
        if len(dates) != len(set(dates)):
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.INVALID_RESPONSE,
                "Tiingo 历史行情包含重复日期",
            )
        if any(item < request.start_date or item > request.end_date for item in dates):
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.INVALID_RESPONSE,
                "Tiingo 返回了请求区间之外的行情",
            )
        try:
            return tuple(
                self._market_bar(request, price, adjusted=adjusted)
                for price in sorted(prices, key=lambda item: item.date)
            )
        except ValidationError as exc:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.INVALID_RESPONSE,
                "Tiingo 返回了非法 OHLC 数据",
            ) from exc

    @staticmethod
    def _market_bar(
        request: MarketDataRangeRequest,
        price: _TiingoPrice,
        *,
        adjusted: bool,
    ) -> MarketBar:
        if adjusted:
            if (
                price.adj_open is None
                or price.adj_high is None
                or price.adj_low is None
                or price.adj_close is None
                or price.adj_volume is None
            ):
                raise MarketDataProviderError(
                    MarketDataProviderErrorKind.INVALID_RESPONSE,
                    "Tiingo 历史行情缺少复权字段",
                )
            open_price = price.adj_open
            high = price.adj_high
            low = price.adj_low
            close = price.adj_close
            volume = price.adj_volume
        else:
            open_price, high, low, close, volume = (
                price.open,
                price.high,
                price.low,
                price.close,
                price.volume,
            )
        return MarketBar(
            symbol=request.symbol,
            trade_date=price.date.date(),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            currency=request.currency,
            source="tiingo",
        )

    def _read_token(self) -> str:
        if self._api_token is None:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.CONFIGURATION,
                "未配置 Tiingo API Token, 行情已关闭",
            )
        token = self._api_token.get_secret_value().strip()
        if not token:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.CONFIGURATION,
                "Tiingo API Token 为空, 行情已关闭",
            )
        return token

    @staticmethod
    def _raise_for_status(status_code: int) -> None:
        if status_code in (401, 403):
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.AUTHENTICATION,
                "Tiingo 鉴权失败",
            )
        if status_code == 404:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.NOT_FOUND,
                "Tiingo 未找到证券或行情",
            )
        if status_code >= 400:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.UPSTREAM,
                f"Tiingo 上游请求失败 (HTTP {status_code})",
            )
