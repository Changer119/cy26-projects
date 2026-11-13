"""共用行情路由、有限缓存和串行请求；不接触交易数据库。"""

import re
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime
from threading import RLock
from time import monotonic
from zoneinfo import ZoneInfo

from ai_trading.integrations.china.failover import FailoverMarketProvider, MarketProvider
from ai_trading.integrations.market_data import (
    MarketBar,
    MarketDataProviderError,
    MarketDataProviderErrorKind,
    MarketDataRangeRequest,
    MarketDataRequest,
)
from ai_trading.market_mcp.models import DailyResult, HistoryResult, SourcesResult, SourceState


def _now() -> datetime:
    return datetime.now(ZoneInfo("Asia/Shanghai"))


@dataclass(frozen=True)
class CacheEntry:
    bars: tuple[MarketBar, ...]
    fetched_at: datetime
    expires_at: float


class MarketService:
    def __init__(
        self,
        providers: tuple[tuple[str, MarketProvider], ...],
        cache_ttl: float = 300,
        cache_size: int = 128,
    ) -> None:
        if cache_ttl < 0 or cache_size < 1:
            raise ValueError("缓存时效不得为负数，容量必须为正数")
        self._providers = providers
        self._router = FailoverMarketProvider(tuple(provider for _, provider in providers))
        self._ttl = cache_ttl
        self._size = cache_size
        self._cache: OrderedDict[tuple[str, str, date, date], CacheEntry] = OrderedDict()
        self._lock = RLock()

    def daily(self, symbol: str, trade_date: date) -> DailyResult:
        symbol = self._validate(symbol, trade_date, trade_date)
        with self._lock:
            key = ("daily", symbol, trade_date, trade_date)
            entry = self._get(key)
            cached = entry is not None
            if entry is None:
                bar = self._router.fetch(
                    MarketDataRequest(
                        symbol=symbol,
                        provider_symbol=symbol,
                        trade_date=trade_date,
                        currency="CNY",
                    )
                )
                entry = self._put(key, (bar,))
            return DailyResult(bar=entry.bars[0], cached=cached, fetched_at=entry.fetched_at)

    def history(self, symbol: str, start_date: date, end_date: date) -> HistoryResult:
        symbol = self._validate(symbol, start_date, end_date)
        with self._lock:
            key = ("history", symbol, start_date, end_date)
            entry = self._get(key)
            cached = entry is not None
            if entry is None:
                bars = self._router.fetch_range(
                    MarketDataRangeRequest(
                        symbol=symbol,
                        provider_symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        currency="CNY",
                    )
                )
                entry = self._put(key, bars)
            return HistoryResult(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                bars=entry.bars,
                cached=cached,
                fetched_at=entry.fetched_at,
            )

    def check_sources(self, symbol: str, trade_date: date) -> SourcesResult:
        symbol = self._validate(symbol, trade_date, trade_date)
        request = MarketDataRequest(
            symbol=symbol, provider_symbol=symbol, trade_date=trade_date, currency="CNY"
        )
        states: list[SourceState] = []
        with self._lock:
            for name, provider in self._providers:
                try:
                    bar = provider.fetch(request)
                    if (bar.symbol, bar.currency, bar.trade_date) != (symbol, "CNY", trade_date):
                        raise MarketDataProviderError(
                            MarketDataProviderErrorKind.INVALID_RESPONSE,
                            "数据源返回的证券、币种或日期不匹配",
                        )
                    states.append(
                        SourceState(source=name, available=True, message="指定日线取数成功")
                    )
                except MarketDataProviderError as exc:
                    states.append(
                        SourceState(
                            source=name,
                            available=False,
                            error_kind=exc.kind.value,
                            message=str(exc),
                        )
                    )
                except Exception:
                    # 不向远端返回异常原因链或上游响应正文。
                    states.append(
                        SourceState(
                            source=name,
                            available=False,
                            error_kind="UPSTREAM",
                            message="指定日线不可用，请检查网络、Token 或权限",
                        )
                    )
        return SourcesResult(
            symbol=symbol, trade_date=trade_date, checked_at=_now(), sources=tuple(states)
        )

    def _get(self, key: tuple[str, str, date, date]) -> CacheEntry | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if entry.expires_at <= monotonic():
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return entry

    def _put(self, key: tuple[str, str, date, date], bars: tuple[MarketBar, ...]) -> CacheEntry:
        entry = CacheEntry(bars=bars, fetched_at=_now(), expires_at=monotonic() + self._ttl)
        self._cache[key] = entry
        self._cache.move_to_end(key)
        while len(self._cache) > self._size:
            self._cache.popitem(last=False)
        return entry

    @staticmethod
    def _validate(symbol: str, start: date, end: date) -> str:
        canonical = symbol.strip().upper()
        if re.fullmatch(r"(?:60\d{4}\.SH|68\d{4}\.SH|00\d{4}\.SZ|30\d{4}\.SZ)", canonical) is None:
            raise ValueError("仅支持沪深 A 股，代码格式例如 600584.SH 或 000001.SZ")
        if start > end or (end - start).days > 366:
            raise ValueError("日期必须递增，单次区间最多 366 天")
        if end > _now().date():
            raise ValueError("不接受未来日期")
        return canonical
