from datetime import date
from decimal import Decimal
from pathlib import Path

from ai_trading.application.evidence import DualSourceEvidenceLoader
from ai_trading.application.store import ApplicationStore
from ai_trading.domain import Market
from ai_trading.integrations.market_data import (
    MarketBar,
    MarketDataQualityGate,
    MarketDataRangeRequest,
    MarketDataRequest,
)
from ai_trading.strategy_v2.history import completed_session_dates


class RangeProvider:
    def __init__(self, source: str, count: int, *, missing_session: bool = False) -> None:
        self.source = source
        self.count = count
        self.missing_session = missing_session
        self.range_calls = 0

    def fetch(self, request: MarketDataRequest) -> MarketBar:
        raise AssertionError(f"盘前 V2 不应逐日拉取: {request.symbol}")

    def fetch_range(self, request: MarketDataRangeRequest) -> tuple[MarketBar, ...]:
        self.range_calls += 1
        extra = 1 if self.missing_session else 0
        dates = completed_session_dates(Market.SSE, request.end_date, self.count + extra)
        if self.missing_session:
            dates = (*dates[:10], *dates[11:])
        return tuple(
            MarketBar(
                symbol=request.symbol,
                trade_date=session_date,
                open=Decimal(40 + index),
                high=Decimal(42 + index),
                low=Decimal(39 + index),
                close=Decimal(41 + index),
                volume=1_000_000 + index,
                currency=request.currency,
                source=self.source,
            )
            for index, session_date in enumerate(dates)
        )


def loader(
    tmp_path: Path,
    count: int = 60,
    *,
    missing_session: bool = False,
) -> tuple[DualSourceEvidenceLoader, RangeProvider]:
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'v2-evidence.db'}")
    store.initialize()
    primary = RangeProvider("yahoo_yfinance", count, missing_session=missing_session)
    secondary = RangeProvider("tiingo", count, missing_session=missing_session)
    return (
        DualSourceEvidenceLoader(
            store,
            primary,
            secondary,
            MarketDataQualityGate(Decimal("50")),
        ),
        primary,
    )


def test_premarket_loads_one_range_per_a_share_and_builds_features(tmp_path: Path) -> None:
    evidence, primary = loader(tmp_path)

    batch = evidence.load(date(2026, 7, 16))

    assert primary.range_calls == 2
    assert tuple(item.instrument_id for item in batch.qualified) == (
        "600584.SH",
        "603005.SH",
    )
    assert tuple(item.instrument_id for item in batch.strategy_features) == (
        "600584.SH",
        "603005.SH",
    )
    assert all(item.history_sessions == 60 for item in batch.strategy_features)
    assert all(item.atr_20 == Decimal("3") for item in batch.strategy_features)
    assert batch.unavailable_instrument_ids == ("01810.HK", "02513.HK")


def test_fifty_nine_history_bars_make_the_instrument_unavailable(tmp_path: Path) -> None:
    evidence, _ = loader(tmp_path, count=59)

    batch = evidence.load(date(2026, 7, 16))

    assert batch.qualified == ()
    assert batch.strategy_features == ()
    assert set(batch.unavailable_instrument_ids) == {
        "600584.SH",
        "603005.SH",
        "01810.HK",
        "02513.HK",
    }


def test_missing_exchange_session_makes_history_unavailable(tmp_path: Path) -> None:
    evidence, _ = loader(tmp_path, missing_session=True)

    batch = evidence.load(date(2026, 7, 16))

    assert batch.qualified == ()
    assert batch.strategy_features == ()
