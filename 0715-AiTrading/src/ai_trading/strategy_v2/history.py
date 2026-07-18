from datetime import date
from typing import cast

from exchange_calendars import get_calendar  # type: ignore[import-untyped]

from ai_trading.domain import Market


def completed_session_dates(
    market: Market,
    end_date: date,
    count: int,
) -> tuple[date, ...]:
    """返回以 end_date 为末日的连续交易会话；日期必须本身可交易。"""

    if count <= 0:
        raise ValueError("交易会话数量必须为正数")
    calendar_name = "XHKG" if market is Market.HKEX else "XSHG"
    calendar = get_calendar(calendar_name)
    session = calendar.date_to_session(end_date, direction="none")
    return tuple(item.date() for item in calendar.sessions_window(session, -count))


def previous_session_date(market: Market, trade_date: date) -> date:
    calendar_name = "XHKG" if market is Market.HKEX else "XSHG"
    calendar = get_calendar(calendar_name)
    session = calendar.date_to_session(trade_date, direction="none")
    return cast(date, calendar.previous_session(session).date())


def has_complete_history(
    market: Market,
    end_date: date,
    actual_dates: tuple[date, ...],
) -> bool:
    try:
        expected = completed_session_dates(market, end_date, len(actual_dates))
    except ValueError:
        return False
    return len(actual_dates) >= 60 and actual_dates == expected
