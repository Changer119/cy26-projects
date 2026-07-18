from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from ai_trading.domain import Order, OrderSide, OrderStatus
from ai_trading.storage import (
    DEFAULT_ACCOUNT_ID,
    TradingRepository,
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)
from ai_trading.storage.settlement import SettlementRepository, SettlementRequest
from ai_trading.storage.valuation import ValuationMark, ValuationRepository


def test_daily_valuation_is_idempotent_and_attributes_profit(tmp_path: Path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'valuation.db'}")
    create_schema(engine)
    sessions = create_session_factory(engine)
    trading = TradingRepository(sessions)
    trading.initialize_default_portfolio()
    trade_date = date(2026, 7, 15)
    trading.create_order(
        Order(
            order_id="order-1",
            account_id=DEFAULT_ACCOUNT_ID,
            instrument_id="603005.SH",
            trade_date=trade_date,
            side=OrderSide.BUY,
            quantity=100,
            limit_price=Decimal("20.20"),
            status=OrderStatus.PENDING_OPEN,
        )
    )
    SettlementRepository(sessions).apply(
        SettlementRequest(
            fill_id="fill-1",
            order_id="order-1",
            account_id=DEFAULT_ACCOUNT_ID,
            instrument_id="603005.SH",
            trade_date=trade_date,
            side=OrderSide.BUY,
            quantity=100,
            price=Decimal("20"),
            fx_to_cny=Decimal("1"),
            fee_cny=Decimal("5"),
            fee_schedule_id="simulation-v1",
        )
    )
    valuations = ValuationRepository(sessions)
    marks = (
        ValuationMark(
            instrument_id="603005.SH",
            close=Decimal("21"),
            fx_to_cny=Decimal("1"),
        ),
    )

    first = valuations.record(DEFAULT_ACCOUNT_ID, trade_date, marks)
    repeated = valuations.record(DEFAULT_ACCOUNT_ID, trade_date, marks)
    next_day = valuations.record(
        DEFAULT_ACCOUNT_ID,
        trade_date + timedelta(days=1),
        (
            ValuationMark(
                instrument_id="603005.SH",
                close=Decimal("20"),
                fx_to_cny=Decimal("1"),
            ),
        ),
    )

    assert first.created is True
    assert repeated.created is False
    assert first.nav_cny == Decimal("100095")
    assert first.total_pnl_cny == Decimal("95")
    assert first.daily_pnl_cny == Decimal("95")
    assert first.unrealized_pnl_cny == Decimal("100")
    assert first.realized_pnl_cny == Decimal("0")
    assert first.fees_cny == Decimal("5")
    assert first.drawdown == Decimal("0")
    assert next_day.daily_pnl_cny == Decimal("-100")
