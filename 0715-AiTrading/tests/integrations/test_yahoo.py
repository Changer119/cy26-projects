from datetime import date
from decimal import Decimal

import pytest
import yfinance

from ai_trading.integrations.market_data import (
    MarketDataProviderError,
    MarketDataProviderErrorKind,
    MarketDataRangeRequest,
    MarketDataRequest,
)
from ai_trading.integrations.yahoo import (
    YahooEodProvider,
    YahooRawBar,
    _YFinanceHistoryLoader,
)


class InMemoryYahooLoader:
    def __init__(self, result: YahooRawBar | None) -> None:
        self.result = result
        self.calls = 0

    def load(self, provider_symbol: str, trade_date: date) -> YahooRawBar | None:
        assert provider_symbol == "1810.HK"
        assert trade_date == date(2026, 7, 15)
        self.calls += 1
        return self.result

    def load_range(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
    ) -> tuple[YahooRawBar, ...]:
        assert provider_symbol == "1810.HK"
        assert start_date <= end_date
        self.calls += 1
        return () if self.result is None else (self.result,)


class FakeIndexer:
    def __getitem__(self, index: int) -> dict[str, object]:
        assert index == 0
        return {"Open": 20, "High": 21, "Low": 19, "Close": 20.5, "Volume": 1000}


class FakeFrame:
    empty = False
    iloc = FakeIndexer()

    class DateIndex:
        class DateValue:
            @staticmethod
            def date() -> date:
                return date(2026, 7, 15)

        def __getitem__(self, index: int) -> DateValue:
            assert index == 0
            return self.DateValue()

    index = DateIndex()

    def __len__(self) -> int:
        return 1


class RecordingTicker:
    def __init__(self) -> None:
        self.options: list[dict[str, object]] = []

    def history(self, **options: object) -> FakeFrame:
        assert options["repair"] is False
        self.options.append(options)
        return FakeFrame()


def make_request() -> MarketDataRequest:
    return MarketDataRequest(
        symbol="01810.HK",
        provider_symbol="1810.HK",
        trade_date=date(2026, 7, 15),
        currency="HKD",
    )


def make_range_request() -> MarketDataRangeRequest:
    return MarketDataRangeRequest(
        symbol="01810.HK",
        provider_symbol="1810.HK",
        start_date=date(2026, 7, 14),
        end_date=date(2026, 7, 15),
        currency="HKD",
    )


def make_raw_bar(high: str = "55.0") -> YahooRawBar:
    return YahooRawBar(
        trade_date=date(2026, 7, 15),
        open=Decimal("53.5"),
        high=Decimal(high),
        low=Decimal("53.0"),
        close=Decimal("54.5"),
        volume=50_000_000,
    )


def test_injected_loader_keeps_yfinance_and_network_out_of_unit_test() -> None:
    loader = InMemoryYahooLoader(make_raw_bar())
    provider = YahooEodProvider(loader=loader)

    bar = provider.fetch(make_request())

    assert loader.calls == 1
    assert bar.symbol == "01810.HK"
    assert bar.close == Decimal("54.5")
    assert bar.currency == "HKD"
    assert bar.source == "yahoo_yfinance"


def test_default_loader_disables_broken_yfinance_repair_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticker = RecordingTicker()
    monkeypatch.setattr(yfinance, "Ticker", lambda _symbol: ticker)

    result = _YFinanceHistoryLoader().load("603005.SS", date(2026, 7, 15))

    assert result is not None
    assert result.close == Decimal("20.5")
    assert ticker.options[0]["auto_adjust"] is False


def test_default_range_loader_uses_adjusted_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ticker = RecordingTicker()
    monkeypatch.setattr(yfinance, "Ticker", lambda _symbol: ticker)

    result = _YFinanceHistoryLoader().load_range(
        "603005.SS",
        date(2026, 7, 15),
        date(2026, 7, 15),
    )

    assert len(result) == 1
    assert ticker.options[0]["auto_adjust"] is True


def test_empty_history_is_classified_as_not_found() -> None:
    provider = YahooEodProvider(loader=InMemoryYahooLoader(None))

    with pytest.raises(MarketDataProviderError) as error:
        provider.fetch(make_request())

    assert error.value.kind is MarketDataProviderErrorKind.NOT_FOUND


def test_invalid_history_is_classified_as_invalid_response() -> None:
    provider = YahooEodProvider(loader=InMemoryYahooLoader(make_raw_bar(high="54.0")))

    with pytest.raises(MarketDataProviderError) as error:
        provider.fetch(make_request())

    assert error.value.kind is MarketDataProviderErrorKind.INVALID_RESPONSE


def test_provider_maps_range_rows_without_losing_real_dates() -> None:
    class RangeLoader(InMemoryYahooLoader):
        def load_range(
            self,
            provider_symbol: str,
            start_date: date,
            end_date: date,
        ) -> tuple[YahooRawBar, ...]:
            latest = make_raw_bar()
            earlier = YahooRawBar(
                trade_date=date(2026, 7, 14),
                open=Decimal("52"),
                high=Decimal("54"),
                low=Decimal("51"),
                close=Decimal("53"),
                volume=40_000_000,
            )
            return (latest, earlier)

    bars = YahooEodProvider(loader=RangeLoader(make_raw_bar())).fetch_range(make_range_request())

    assert tuple(item.trade_date for item in bars) == (date(2026, 7, 14), date(2026, 7, 15))
    assert all(item.source == "yahoo_yfinance" for item in bars)
