from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ai_trading.api.schemas import AccountResponse
from ai_trading.config import Settings
from ai_trading.domain import Currency
from ai_trading.storage import DEFAULT_ACCOUNT_ID
from ai_trading.storage.ledger_tables import DailyValuationRow
from ai_trading.storage.tables import AccountRow, CashBalanceRow


def account_snapshot(
    session_factory: sessionmaker[Session],
    settings: Settings,
    database_initialized: bool,
) -> AccountResponse:
    initial_cash = settings.initial_cash_cny_micros
    if not database_initialized:
        return empty_account(initial_cash)
    with session_factory() as session:
        account = session.get(AccountRow, DEFAULT_ACCOUNT_ID)
        if account is None:
            return empty_account(initial_cash)
        valuations = tuple(
            session.scalars(
                select(DailyValuationRow)
                .where(DailyValuationRow.account_id == account.id)
                .order_by(DailyValuationRow.trade_date)
            )
        )
        if valuations:
            latest = valuations[-1]
            pnl_micros = latest.nav_cny_micros - initial_cash
            return AccountResponse(
                initial_cash_micros=initial_cash,
                cash_micros=latest.cash_cny_micros,
                market_value_micros=max(
                    latest.nav_cny_micros - latest.cash_cny_micros,
                    0,
                ),
                nav_micros=latest.nav_cny_micros,
                pnl_micros=pnl_micros,
                return_bps=(pnl_micros * 10_000 // initial_cash if initial_cash else 0),
                max_drawdown_bps=max(item.drawdown_micros for item in valuations) // 100,
                updated_at=latest.created_at,
            )
        cash = session.get(CashBalanceRow, (account.id, Currency.CNY))
        cash_micros = 0 if cash is None else cash.available_micros + cash.reserved_micros
        pnl_micros = cash_micros - initial_cash
        return AccountResponse(
            initial_cash_micros=initial_cash,
            cash_micros=cash_micros,
            market_value_micros=0,
            nav_micros=cash_micros,
            pnl_micros=pnl_micros,
            return_bps=(pnl_micros * 10_000 // initial_cash if initial_cash else 0),
            max_drawdown_bps=0,
            updated_at=account.created_at,
        )


def empty_account(initial_cash: int) -> AccountResponse:
    return AccountResponse(
        initial_cash_micros=initial_cash,
        cash_micros=0,
        market_value_micros=0,
        nav_micros=0,
        pnl_micros=0,
        return_bps=0,
        max_drawdown_bps=0,
        updated_at=datetime(1970, 1, 1, tzinfo=UTC),
    )
