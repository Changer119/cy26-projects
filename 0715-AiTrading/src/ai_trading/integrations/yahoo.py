"""Yahoo EOD 适配器; yfinance 被隔离在可替换 Loader 后。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Protocol, cast

from pydantic import ValidationError

from .market_data import (
    MarketBar,
    MarketDataProviderError,
    MarketDataProviderErrorKind,
    MarketDataRangeRequest,
    MarketDataRequest,
)


@dataclass(frozen=True, slots=True)
class YahooRawBar:
    """从 yfinance 动态对象中抽离后的稳定数据结构。"""

    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class YahooHistoryLoader(Protocol):
    def load(self, provider_symbol: str, trade_date: date) -> YahooRawBar | None: ...

    def load_range(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
    ) -> tuple[YahooRawBar, ...]: ...


class _Row(Protocol):
    def __getitem__(self, column: str) -> object: ...


class _RowIndexer(Protocol):
    def __getitem__(self, index: int) -> _Row: ...


class _HistoryFrame(Protocol):
    @property
    def empty(self) -> bool: ...

    @property
    def iloc(self) -> _RowIndexer: ...

    @property
    def index(self) -> _DateIndexer: ...

    def __len__(self) -> int: ...


class _DateValue(Protocol):
    def date(self) -> date: ...


class _DateIndexer(Protocol):
    def __getitem__(self, index: int) -> _DateValue: ...


class _YFinanceHistoryLoader:
    """唯一允许接触 yfinance 动态返回类型的窄适配层。"""

    def load(self, provider_symbol: str, trade_date: date) -> YahooRawBar | None:
        history = self._download(provider_symbol, trade_date, trade_date, adjusted=False)
        if history.empty:
            return None
        row = history.iloc[0]
        return self._raw_bar(trade_date, row)

    def load_range(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
    ) -> tuple[YahooRawBar, ...]:
        history = self._download(provider_symbol, start_date, end_date, adjusted=True)
        if history.empty:
            return ()
        return tuple(
            self._raw_bar(history.index[index].date(), history.iloc[index])
            for index in range(len(history))
        )

    @staticmethod
    def _download(
        provider_symbol: str,
        start_date: date,
        end_date: date,
        *,
        adjusted: bool,
    ) -> _HistoryFrame:
        try:
            from yfinance import Ticker  # type: ignore[import-untyped]

            return cast(
                _HistoryFrame,
                Ticker(provider_symbol).history(
                    start=start_date.isoformat(),
                    end=(end_date + timedelta(days=1)).isoformat(),
                    interval="1d",
                    auto_adjust=adjusted,
                    actions=False,
                    repair=False,
                ),
            )
        except Exception as exc:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.UPSTREAM,
                "Yahoo/yfinance 行情请求失败",
            ) from exc

    @staticmethod
    def _raw_bar(trade_date: date, row: _Row) -> YahooRawBar:
        return YahooRawBar(
            trade_date=trade_date,
            open=_to_decimal(row["Open"]),
            high=_to_decimal(row["High"]),
            low=_to_decimal(row["Low"]),
            close=_to_decimal(row["Close"]),
            volume=_to_int(row["Volume"]),
        )


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, float, str)):
        raise MarketDataProviderError(
            MarketDataProviderErrorKind.INVALID_RESPONSE,
            "Yahoo/yfinance 返回了非数值价格",
        )
    try:
        converted = Decimal(str(value))
    except InvalidOperation as exc:
        raise MarketDataProviderError(
            MarketDataProviderErrorKind.INVALID_RESPONSE,
            "Yahoo/yfinance 返回了非数值价格",
        ) from exc
    if not converted.is_finite():
        raise MarketDataProviderError(
            MarketDataProviderErrorKind.INVALID_RESPONSE,
            "Yahoo/yfinance 返回了非有限价格",
        )
    return converted


def _to_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, float, str)):
        raise MarketDataProviderError(
            MarketDataProviderErrorKind.INVALID_RESPONSE,
            "Yahoo/yfinance 返回了非法成交量",
        )
    try:
        return int(value)
    except (ValueError, OverflowError) as exc:
        raise MarketDataProviderError(
            MarketDataProviderErrorKind.INVALID_RESPONSE,
            "Yahoo/yfinance 返回了非法成交量",
        ) from exc


class YahooEodProvider:
    """将可替换 Loader 的结果映射为统一 MarketBar。"""

    def __init__(self, loader: YahooHistoryLoader | None = None) -> None:
        self._loader = loader or _YFinanceHistoryLoader()

    def fetch(self, request: MarketDataRequest) -> MarketBar:
        raw = self._loader.load(request.provider_symbol, request.trade_date)
        if raw is None or raw.trade_date != request.trade_date:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.NOT_FOUND,
                "Yahoo/yfinance 未返回目标交易日行情",
            )
        return self._map_bar(request.symbol, request.currency, raw)

    def fetch_range(self, request: MarketDataRangeRequest) -> tuple[MarketBar, ...]:
        rows = self._loader.load_range(
            request.provider_symbol,
            request.start_date,
            request.end_date,
        )
        dates = tuple(item.trade_date for item in rows)
        if len(dates) != len(set(dates)) or any(
            item < request.start_date or item > request.end_date for item in dates
        ):
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.INVALID_RESPONSE,
                "Yahoo/yfinance 历史行情日期无效",
            )
        return tuple(
            self._map_bar(request.symbol, request.currency, row)
            for row in sorted(rows, key=lambda item: item.trade_date)
        )

    @staticmethod
    def _map_bar(symbol: str, currency: str, raw: YahooRawBar) -> MarketBar:
        try:
            return MarketBar(
                symbol=symbol,
                trade_date=raw.trade_date,
                open=raw.open,
                high=raw.high,
                low=raw.low,
                close=raw.close,
                volume=raw.volume,
                currency=currency,
                source="yahoo_yfinance",
            )
        except ValidationError as exc:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.INVALID_RESPONSE,
                "Yahoo/yfinance 返回了非法 OHLC 数据",
            ) from exc
