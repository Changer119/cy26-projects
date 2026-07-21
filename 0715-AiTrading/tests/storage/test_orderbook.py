from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ai_trading.domain import (
    Currency,
    Order,
    OrderSide,
    OrderStatus,
    ProposalStatus,
    TradeAction,
    TradePlan,
    TradePlanStatus,
    TradeProposal,
)
from ai_trading.storage import (
    DEFAULT_ACCOUNT_ID,
    CashBalanceRow,
    OrderRow,
    TradePlanRow,
    TradingRepository,
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)
from ai_trading.storage.orderbook import FrozenOrder, OrderBatchRepository

TRADE_DATE = date(2026, 7, 15)


def plan(plan_id: str) -> TradePlan:
    proposals = tuple(
        TradeProposal(
            proposal_id=f"{plan_id}:{instrument_id}",
            instrument_id=instrument_id,
            action=TradeAction.BUY,
            current_quantity=0,
            target_quantity=100,
            delta_quantity=100,
            limit_price=Decimal(price),
            status=ProposalStatus.RISK_APPROVED,
            confidence=Decimal("0.8"),
        )
        for instrument_id, price in (
            ("603005.SH", "20.20"),
            ("600584.SH", "30.30"),
        )
    )
    return TradePlan(
        plan_id=plan_id,
        account_id=DEFAULT_ACCOUNT_ID,
        trade_date=TRADE_DATE,
        decision_asof=datetime(2026, 7, 15, 0, 35, tzinfo=UTC),
        status=TradePlanStatus.FROZEN,
        proposals=proposals,
    )


def frozen_orders(plan_id: str) -> tuple[FrozenOrder, ...]:
    return tuple(
        FrozenOrder(
            order=Order(
                order_id=f"{plan_id}:{instrument_id}",
                account_id=DEFAULT_ACCOUNT_ID,
                instrument_id=instrument_id,
                trade_date=TRADE_DATE,
                side=OrderSide.BUY,
                quantity=100,
                limit_price=Decimal(price),
                status=OrderStatus.PENDING_OPEN,
            ),
            reserved_cash_micros=reserved,
        )
        for instrument_id, price, reserved in (
            ("603005.SH", "20.20", 2_030_100_000),
            ("600584.SH", "30.30", 3_045_150_000),
        )
    )


def repository(tmp_path: Path) -> OrderBatchRepository:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'orderbook.db'}")
    create_schema(engine)
    sessions = create_session_factory(engine)
    TradingRepository(sessions).initialize_default_portfolio()
    return OrderBatchRepository(sessions)


def test_plan_orders_and_cash_reservation_freeze_in_one_transaction(tmp_path: Path) -> None:
    orderbook = repository(tmp_path)

    orderbook.freeze(plan("plan-1"), frozen_orders("plan-1"))

    with orderbook.session() as session:
        cash = session.get(CashBalanceRow, (DEFAULT_ACCOUNT_ID, Currency.CNY))
        assert cash is not None
        assert cash.available_micros == 94_924_750_000
        assert cash.reserved_micros == 5_075_250_000
        assert session.scalar(select(func.count()).select_from(TradePlanRow)) == 1
        assert session.scalar(select(func.count()).select_from(OrderRow)) == 2


def test_duplicate_order_rolls_back_new_plan_and_reservation(tmp_path: Path) -> None:
    orderbook = repository(tmp_path)
    orderbook.freeze(plan("plan-1"), frozen_orders("plan-1"))

    with pytest.raises(IntegrityError):
        orderbook.freeze(plan("plan-2"), frozen_orders("plan-2"))

    with orderbook.session() as session:
        cash = session.get(CashBalanceRow, (DEFAULT_ACCOUNT_ID, Currency.CNY))
        assert cash is not None
        assert cash.available_micros == 94_924_750_000
        assert cash.reserved_micros == 5_075_250_000
        assert session.get(TradePlanRow, "plan-2") is None
