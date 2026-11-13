from datetime import date
from decimal import Decimal

import pytest

from ai_trading.integrations.market_data import (
    MarketBar,
    MarketDataProviderError,
    MarketDataRangeRequest,
    MarketDataRequest,
)
from ai_trading.market_mcp.service import MarketService

DAY = date(2026, 10, 28)


class Provider:
    def __init__(self, source: str = "tushare", fail: bool = False) -> None:
        self.source = source
        self.fail = fail
        self.calls = 0

    def fetch(self, request: MarketDataRequest) -> MarketBar:
        self.calls += 1
        if self.fail:
            raise TimeoutError("secret")
        return MarketBar(
            symbol=request.symbol,
            trade_date=request.trade_date,
            open=Decimal(10),
            high=Decimal(11),
            low=Decimal(9),
            close=Decimal(10),
            volume=10000,
            currency="CNY",
            source=self.source,
        )

    def fetch_range(self, request: MarketDataRangeRequest) -> tuple[MarketBar, ...]:
        return (
            self.fetch(
                MarketDataRequest(
                    symbol=request.symbol,
                    provider_symbol=request.provider_symbol,
                    trade_date=request.end_date,
                    currency="CNY",
                )
            ),
        )


def make_service(first: Provider, second: Provider, ttl: float = 300) -> MarketService:
    return MarketService((("akshare", first), ("tushare", second)), cache_ttl=ttl)


def test_daily_uses_backup_and_shares_cached_result() -> None:
    first, second = Provider("akshare", fail=True), Provider()
    service = make_service(first, second)
    one = service.daily("600584.SH", DAY)
    two = service.daily("600584.sh", DAY)
    assert one.bar.source == "tushare"
    assert one.cached is False and two.cached is True
    assert first.calls == second.calls == 1


def test_cache_expiry_retries_source() -> None:
    provider = Provider()
    service = make_service(provider, Provider(), ttl=0)
    service.daily("600584.SH", DAY)
    service.daily("600584.SH", DAY)
    assert provider.calls == 2


def test_failures_are_not_cached_and_recovery_works() -> None:
    first, second = Provider(fail=True), Provider(fail=True)
    service = make_service(first, second)
    with pytest.raises(MarketDataProviderError):
        service.daily("600584.SH", DAY)
    second.fail = False
    assert service.daily("600584.SH", DAY).bar.source == "tushare"


@pytest.mark.parametrize("symbol", ["01810.HK", "600584", "../../.env", "510300.SH"])
def test_rejects_unsupported_symbol_before_network(symbol: str) -> None:
    first, second = Provider(), Provider()
    with pytest.raises(ValueError):
        make_service(first, second).daily(symbol, DAY)
    assert first.calls == second.calls == 0


def test_range_rejects_reversed_or_excessive_dates() -> None:
    service = make_service(Provider(), Provider())
    with pytest.raises(ValueError):
        service.history("600584.SH", DAY, date(2026, 1, 1))
    with pytest.raises(ValueError):
        service.history("600584.SH", date(2020, 1, 1), DAY)


def test_probe_returns_real_per_source_outcomes_without_secrets() -> None:
    result = make_service(Provider(fail=True), Provider()).check_sources("600584.SH", DAY)
    assert result.sources[0].available is False
    assert result.sources[1].available is True
    assert "secret" not in result.model_dump_json()


def test_history_returns_explicit_adjustment_and_cache() -> None:
    service = make_service(Provider(), Provider())
    result = service.history("600584.SH", DAY, DAY)
    assert result.adjustment == "qfq_at_end"
    assert result.bars[0].trade_date == DAY
    assert service.history("600584.SH", DAY, DAY).cached is True


def test_parallel_requests_share_one_upstream_fetch() -> None:
    from concurrent.futures import ThreadPoolExecutor

    first = Provider()
    service = make_service(first, Provider())
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = tuple(executor.map(lambda _: service.daily("600584.SH", DAY), range(4)))
    assert first.calls == 1
    assert sum(not result.cached for result in results) == 1


def test_cache_is_bounded_and_evicts_oldest_entry() -> None:
    first = Provider()
    service = MarketService((("akshare", first),), cache_size=1)
    service.daily("600584.SH", DAY)
    service.daily("603005.SH", DAY)
    service.daily("600584.SH", DAY)
    assert first.calls == 3


def test_source_probe_preserves_safe_provider_error_classification() -> None:
    from ai_trading.integrations.market_data import MarketDataProviderErrorKind

    class MissingToken(Provider):
        def fetch(self, request: MarketDataRequest) -> MarketBar:
            raise MarketDataProviderError(
                MarketDataProviderErrorKind.CONFIGURATION, "未配置 TUSHARE_TOKEN"
            )

    result = make_service(Provider(), MissingToken()).check_sources("600584.SH", DAY)
    assert result.sources[1].error_kind == "CONFIGURATION"
    assert result.sources[1].message == "未配置 TUSHARE_TOKEN"
