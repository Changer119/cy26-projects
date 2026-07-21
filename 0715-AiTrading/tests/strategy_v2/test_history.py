from datetime import date

from ai_trading.domain import Market
from ai_trading.strategy_v2.history import completed_session_dates, has_complete_history


def test_completed_sessions_use_exchange_calendar_not_weekdays() -> None:
    sessions = completed_session_dates(Market.SSE, date(2026, 2, 24), 5)

    assert sessions == (
        date(2026, 2, 10),
        date(2026, 2, 11),
        date(2026, 2, 12),
        date(2026, 2, 13),
        date(2026, 2, 24),
    )


def test_missing_expected_session_fails_closed() -> None:
    expected = completed_session_dates(Market.SSE, date(2026, 7, 15), 60)
    missing_one = (*expected[:10], *expected[11:])

    assert has_complete_history(Market.SSE, date(2026, 7, 15), expected)
    assert not has_complete_history(Market.SSE, date(2026, 7, 15), missing_one)
