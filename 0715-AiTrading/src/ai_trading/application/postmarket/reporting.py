from datetime import date, datetime
from zoneinfo import ZoneInfo

from ai_trading.application.models import WorkflowReport, WorkflowStatus
from ai_trading.storage.valuation import ValuationOutcome


def postmarket_timing_rejection(trade_date: date, now: datetime) -> str | None:
    if now.utcoffset() is None:
        return "POSTMARKET_TIMEZONE_MISSING"
    local = now.astimezone(ZoneInfo("Asia/Shanghai"))
    if trade_date.weekday() >= 5:
        return "NON_TRADING_DAY"
    if local.date() < trade_date:
        return "POSTMARKET_FUTURE_DATE"
    if local.date() == trade_date and (local.hour, local.minute) < (18, 0):
        return "POSTMARKET_CUTOFF_NOT_REACHED"
    return None


def postmarket_report(
    status: WorkflowStatus,
    trade_date: date,
    fills: int,
    reason: str,
    valuation: ValuationOutcome | None = None,
) -> WorkflowReport:
    return WorkflowReport(
        command="postmarket",
        status=status,
        trade_date=trade_date,
        fills_recorded=fills,
        nav_cny=None if valuation is None else valuation.nav_cny,
        daily_pnl_cny=None if valuation is None else valuation.daily_pnl_cny,
        total_pnl_cny=None if valuation is None else valuation.total_pnl_cny,
        drawdown=None if valuation is None else valuation.drawdown,
        reason=reason,
    )
