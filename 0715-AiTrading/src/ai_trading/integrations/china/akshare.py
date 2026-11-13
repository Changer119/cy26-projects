"""AKShare 东方财富日线：单日不复权，策略历史前复权。"""

from typing import Protocol, cast

from ai_trading.integrations.china.common import number, shares, stock_code, trading_date
from ai_trading.integrations.market_data import (
    MarketBar,
    MarketDataProviderError,
    MarketDataProviderErrorKind,
    MarketDataRangeRequest,
    MarketDataRequest,
)


class Row(Protocol):
    def __getitem__(self, column: str) -> object: ...


class Indexer(Protocol):
    def __getitem__(self, index: int) -> Row: ...


class Frame(Protocol):
    @property
    def iloc(self) -> Indexer: ...

    def __len__(self) -> int: ...


class HistoryLoader(Protocol):
    def load(self, symbol: str, start: str, end: str, adjusted: bool) -> Frame: ...


class AkshareLoader:
    def load(self, symbol: str, start: str, end: str, adjusted: bool) -> Frame:
        import akshare as ak  # type: ignore[import-untyped]

        return cast(
            Frame,
            ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start,
                end_date=end,
                adjust="hfq" if adjusted else "",
                timeout=20,
            ),
        )


class AkshareEodProvider:
    def __init__(self, loader: HistoryLoader | None = None) -> None:
        self._loader = loader or AkshareLoader()

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
                MarketDataProviderErrorKind.NOT_FOUND, "AKShare 未返回目标交易日"
            )
        return bars[0]

    def fetch_range(self, request: MarketDataRangeRequest) -> tuple[MarketBar, ...]:
        bars = self._fetch(request, adjusted=True)
        if not bars:
            return ()
        latest = self.fetch(
            MarketDataRequest(
                symbol=request.symbol,
                provider_symbol=request.provider_symbol,
                trade_date=bars[-1].trade_date,
                currency=request.currency,
            )
        )
        ratio = latest.close / bars[-1].close
        return tuple(
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
            for bar in bars
        )

    def _fetch(self, request: MarketDataRangeRequest, *, adjusted: bool) -> tuple[MarketBar, ...]:
        numeric, _ = stock_code(request.symbol, request.currency)
        try:
            frame = self._loader.load(
                numeric,
                request.start_date.strftime("%Y%m%d"),
                request.end_date.strftime("%Y%m%d"),
                adjusted,
            )
            bars: list[MarketBar] = []
            for index in range(len(frame)):
                row = frame.iloc[index]
                bars.append(
                    MarketBar(
                        symbol=request.symbol,
                        trade_date=trading_date(row["日期"]),
                        open=number(row["开盘"]),
                        high=number(row["最高"]),
                        low=number(row["最低"]),
                        close=number(row["收盘"]),
                        volume=shares(row["成交量"]),
                        currency=request.currency,
                        source="akshare",
                    )
                )
            return tuple(sorted(bars, key=lambda bar: bar.trade_date))
        except Exception as exc:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.UPSTREAM,
                f"AKShare 行情请求或数据校验失败 ({type(exc).__name__})",
            ) from None
