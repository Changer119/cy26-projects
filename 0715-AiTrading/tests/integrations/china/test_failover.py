from datetime import date
from decimal import Decimal

import pytest

from ai_trading.integrations.china.failover import FailoverMarketProvider
from ai_trading.integrations.market_data import (
    MarketBar,
    MarketDataProviderError,
    MarketDataProviderErrorKind,
    MarketDataRangeRequest,
    MarketDataRequest,
)

DAY = date(2026, 10, 28)
REQUEST = MarketDataRequest(
    symbol="600519.SH", provider_symbol="600519.SS", trade_date=DAY, currency="CNY"
)
RANGE = MarketDataRangeRequest(
    symbol=REQUEST.symbol,
    provider_symbol=REQUEST.provider_symbol,
    start_date=DAY,
    end_date=DAY,
    currency="CNY",
)


def bar(source: str, day: date = DAY) -> MarketBar:
    return MarketBar(
        symbol=REQUEST.symbol,
        trade_date=day,
        open=Decimal(10),
        high=Decimal(11),
        low=Decimal(9),
        close=Decimal(10),
        volume=100,
        currency="CNY",
        source=source,
    )


class Provider:
    def __init__(self, result: MarketBar | Exception | None) -> None:
        self.result = result
        self.calls = 0

    def fetch(self, request: MarketDataRequest) -> MarketBar:
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        assert self.result is not None
        return self.result

    def fetch_range(self, request: MarketDataRangeRequest) -> tuple[MarketBar, ...]:
        if self.result is None:
            self.calls += 1
            return ()
        return (self.fetch(REQUEST),)


def test_primary_success_does_not_call_backup() -> None:
    first, second = Provider(bar("akshare")), Provider(bar("tushare"))
    assert FailoverMarketProvider((first, second)).fetch(REQUEST).source == "akshare"
    assert second.calls == 0


@pytest.mark.parametrize(
    "failure",
    [
        TimeoutError(),
        ValueError(),
        MarketDataProviderError(MarketDataProviderErrorKind.NOT_FOUND, "missing"),
        bar("akshare", date(2026, 10, 27)),
    ],
)
def test_failure_or_stale_data_switches_transparently(failure: MarketBar | Exception) -> None:
    first, second = Provider(failure), Provider(bar("tushare"))
    assert FailoverMarketProvider((first, second)).fetch(REQUEST) == bar("tushare")


def test_empty_range_switches_and_primary_is_retried_next_request() -> None:
    first, second = Provider(None), Provider(bar("tushare"))
    provider = FailoverMarketProvider((first, second))
    assert provider.fetch_range(RANGE) == (bar("tushare"),)
    first.result = bar("akshare")
    assert provider.fetch_range(RANGE) == (bar("akshare"),)
    assert second.calls == 1


def test_all_failed_returns_safe_unified_error() -> None:
    provider = FailoverMarketProvider((Provider(ValueError("secret")), Provider(None)))
    with pytest.raises(MarketDataProviderError, match="全部行情源不可用") as error:
        provider.fetch_range(RANGE)
    assert "secret" not in str(error.value)


def test_truncated_history_switches_whole_range() -> None:
    request = MarketDataRangeRequest(
        symbol=REQUEST.symbol,
        provider_symbol=REQUEST.provider_symbol,
        start_date=date(2026, 10, 27),
        end_date=DAY,
        currency="CNY",
    )

    class CompleteProvider(Provider):
        def fetch_range(self, request: MarketDataRangeRequest) -> tuple[MarketBar, ...]:
            self.calls += 1
            return (bar("tushare", date(2026, 10, 27)), bar("tushare"))

    first, second = Provider(bar("akshare")), CompleteProvider(None)
    result = FailoverMarketProvider((first, second)).fetch_range(request)
    assert len(result) == 2
    assert all(item.source == "tushare" for item in result)


def test_wrong_symbol_switches_to_backup() -> None:
    wrong = bar("akshare").model_copy(update={"symbol": "000001.SZ"})
    assert (
        FailoverMarketProvider((Provider(wrong), Provider(bar("tushare")))).fetch(REQUEST).source
        == "tushare"
    )
