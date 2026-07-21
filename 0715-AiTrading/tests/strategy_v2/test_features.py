from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from ai_trading.strategy_v2.features import calculate_features
from ai_trading.strategy_v2.models import HistoricalBar

SHANGHAI = ZoneInfo("Asia/Shanghai")
START = date(2026, 1, 1)


def history(count: int = 60) -> tuple[HistoricalBar, ...]:
    result: tuple[HistoricalBar, ...] = ()
    for index in range(count):
        close = Decimal(41 + index)
        session = START + timedelta(days=index)
        result += (
            HistoricalBar(
                trade_date=session,
                open=close - Decimal(1),
                high=close + Decimal(2),
                low=close - Decimal(2),
                close=close,
                volume=2_000,
                available_at=datetime.combine(
                    session,
                    datetime.min.time(),
                    SHANGHAI,
                ).replace(hour=18),
            ),
        )
    return result


def test_sixty_completed_sessions_produce_auditable_features() -> None:
    bars = history()

    features = calculate_features(
        "603005.SH",
        bars,
        datetime(2026, 3, 2, 7, 50, tzinfo=SHANGHAI),
    )

    assert features.history_sessions == 60
    assert features.as_of == bars[-1].trade_date
    assert features.close == Decimal("100")
    assert features.sma_20 == Decimal("90.5")
    assert features.sma_60 == Decimal("70.5")
    assert features.atr_20 == Decimal("4")
    assert features.average_volume_20 == 2_000
    assert features.support_20 == Decimal("79")
    assert features.resistance_20 == Decimal("102")


def test_fewer_than_sixty_sessions_fail_closed() -> None:
    with pytest.raises(ValueError, match="60"):
        calculate_features(
            "603005.SH",
            history(59),
            datetime(2026, 3, 2, 7, 50, tzinfo=SHANGHAI),
        )


def test_unsorted_or_future_history_is_rejected() -> None:
    bars = history()
    with pytest.raises(ValueError, match="严格递增"):
        calculate_features(
            "603005.SH",
            (*bars[:-2], bars[-1], bars[-2]),
            datetime(2026, 3, 2, 7, 50, tzinfo=SHANGHAI),
        )

    future = bars[-1].model_copy(
        update={"available_at": datetime(2026, 3, 2, 8, 0, tzinfo=SHANGHAI)}
    )
    with pytest.raises(ValueError, match="未来"):
        calculate_features(
            "603005.SH",
            (*bars[:-1], future),
            datetime(2026, 3, 2, 7, 50, tzinfo=SHANGHAI),
        )


def test_unadjusted_corporate_action_gap_is_rejected() -> None:
    bars = history()
    split_like = bars[30].model_copy(
        update={
            "open": Decimal("20"),
            "high": Decimal("22"),
            "low": Decimal("18"),
            "close": Decimal("20"),
        }
    )

    with pytest.raises(ValueError, match="除权"):
        calculate_features(
            "603005.SH",
            (*bars[:30], split_like, *bars[31:]),
            datetime(2026, 3, 2, 7, 50, tzinfo=SHANGHAI),
        )
