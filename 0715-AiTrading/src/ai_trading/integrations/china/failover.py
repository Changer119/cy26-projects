"""统一行情入口：逐源尝试，每次请求优先恢复主源。"""

import logging
from typing import Protocol

from ai_trading.integrations.market_data import (
    MarketBar,
    MarketDataProviderError,
    MarketDataProviderErrorKind,
    MarketDataRangeRequest,
    MarketDataRequest,
)

logger = logging.getLogger(__name__)


class MarketProvider(Protocol):
    def fetch(self, request: MarketDataRequest) -> MarketBar: ...

    def fetch_range(self, request: MarketDataRangeRequest) -> tuple[MarketBar, ...]: ...


class FailoverMarketProvider:
    def __init__(self, providers: tuple[MarketProvider, ...]) -> None:
        if not providers:
            raise ValueError("至少需要一个行情源")
        self._providers = providers

    def fetch(self, request: MarketDataRequest) -> MarketBar:
        for provider in self._providers:
            try:
                bar = provider.fetch(request)
                if (bar.symbol, bar.currency, bar.trade_date) != (
                    request.symbol,
                    request.currency,
                    request.trade_date,
                ):
                    raise ValueError("行情身份或日期不匹配")
                return bar
            except Exception as exc:
                self._log_failure(provider, request.symbol, exc)
        raise self._unavailable()

    def fetch_range(self, request: MarketDataRangeRequest) -> tuple[MarketBar, ...]:
        for provider in self._providers:
            try:
                bars = provider.fetch_range(request)
                dates = tuple(bar.trade_date for bar in bars)
                if (
                    not bars
                    or dates != tuple(sorted(set(dates)))
                    or any(
                        bar.symbol != request.symbol
                        or bar.currency != request.currency
                        or not request.start_date <= bar.trade_date <= request.end_date
                        for bar in bars
                    )
                ):
                    raise ValueError("历史行情为空或格式无效")
                # 交易日历完整性由应用层检查；主源截断不能静默用于策略。
                from exchange_calendars import get_calendar  # type: ignore[import-untyped]

                market = "XSHG"
                expected = tuple(
                    item.date()
                    for item in get_calendar(market).sessions_in_range(
                        request.start_date, request.end_date
                    )
                )
                if dates != expected:
                    raise ValueError("历史行情缺少交易会话")
                return bars
            except Exception as exc:
                self._log_failure(provider, request.symbol, exc)
        raise self._unavailable()

    @staticmethod
    def _log_failure(provider: MarketProvider, symbol: str, error: Exception) -> None:
        # 不记录上游异常正文，防止 Token 随 URL 或响应内容泄漏。
        logger.warning(
            "行情源失败，尝试备用源 provider=%s symbol=%s reason=%s",
            type(provider).__name__,
            symbol,
            str(error) if isinstance(error, MarketDataProviderError) else type(error).__name__,
        )

    @staticmethod
    def _unavailable() -> MarketDataProviderError:
        return MarketDataProviderError(
            MarketDataProviderErrorKind.UPSTREAM, "全部行情源不可用，未返回替代日期或陈旧数据"
        )
