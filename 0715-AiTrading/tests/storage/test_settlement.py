from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import func, select

from ai_trading.domain import Currency, Order, OrderSide, OrderStatus
from ai_trading.storage import (
    DEFAULT_ACCOUNT_ID,
    CashBalanceRow,
    FillRow,
    OrderRow,
    PositionRow,
    TradingRepository,
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)
from ai_trading.storage.settlement import (
    SettlementError,
    SettlementRepository,
    SettlementRequest,
)

TRADE_DATE = date(2026, 7, 15)


def repositories(
    tmp_path: Path,
) -> tuple[TradingRepository, SettlementRepository]:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'settlement.db'}")
    create_schema(engine)
    sessions = create_session_factory(engine)
    trading = TradingRepository(sessions)
    trading.initialize_default_portfolio()
    return trading, SettlementRepository(sessions)


def pending_order(order_id: str = "order-1", quantity: int = 100) -> Order:
    return Order(
        order_id=order_id,
        account_id=DEFAULT_ACCOUNT_ID,
        instrument_id="603005.SH",
        trade_date=TRADE_DATE,
        side=OrderSide.BUY,
        quantity=quantity,
        limit_price=Decimal("20.20"),
        status=OrderStatus.PENDING_OPEN,
    )


def fill_request(
    order_id: str = "order-1",
    quantity: int = 100,
    price: Decimal = Decimal("20"),
) -> SettlementRequest:
    return SettlementRequest(
        fill_id=f"fill:{order_id}",
        order_id=order_id,
        account_id=DEFAULT_ACCOUNT_ID,
        instrument_id="603005.SH",
        trade_date=TRADE_DATE,
        side=OrderSide.BUY,
        quantity=quantity,
        price=price,
        fx_to_cny=Decimal("1"),
        fee_cny=Decimal("5"),
        fee_schedule_id="simulation-v1",
    )


def test_buy_fill_updates_cash_position_and_order_atomically(tmp_path: Path) -> None:
    trading, settlement = repositories(tmp_path)
    trading.create_order(pending_order())

    outcome = settlement.apply(fill_request())

    assert outcome.applied is True
    assert outcome.cash_cny_micros == 97_995_000_000
    assert outcome.position_quantity == 100
    with settlement.session() as session:
        order = session.get(OrderRow, "order-1")
        cash = session.get(CashBalanceRow, (DEFAULT_ACCOUNT_ID, Currency.CNY))
        position = session.get(PositionRow, (DEFAULT_ACCOUNT_ID, "603005.SH"))
        assert order is not None and order.status is OrderStatus.FILLED
        assert cash is not None and cash.available_micros == 97_995_000_000
        assert position is not None and position.average_cost_micros == 20_000_000
        assert session.scalar(select(func.count()).select_from(FillRow)) == 1


def test_replaying_same_order_is_idempotent(tmp_path: Path) -> None:
    trading, settlement = repositories(tmp_path)
    trading.create_order(pending_order())

    first = settlement.apply(fill_request())
    repeated = settlement.apply(fill_request())

    assert first.applied is True
    assert repeated.applied is False
    assert repeated.cash_cny_micros == first.cash_cny_micros
    assert repeated.position_quantity == first.position_quantity


def test_sale_releases_cash_and_closes_position(tmp_path: Path) -> None:
    trading, settlement = repositories(tmp_path)
    trading.create_order(pending_order())
    settlement.apply(fill_request())
    sell_date = date(2026, 7, 16)
    trading.create_order(
        Order(
            order_id="order-2",
            account_id=DEFAULT_ACCOUNT_ID,
            instrument_id="603005.SH",
            trade_date=sell_date,
            side=OrderSide.SELL,
            quantity=100,
            limit_price=Decimal("19.50"),
            status=OrderStatus.PENDING_OPEN,
        )
    )

    outcome = settlement.apply(
        SettlementRequest(
            fill_id="fill:order-2",
            order_id="order-2",
            account_id=DEFAULT_ACCOUNT_ID,
            instrument_id="603005.SH",
            trade_date=sell_date,
            side=OrderSide.SELL,
            quantity=100,
            price=Decimal("20"),
            fx_to_cny=Decimal("1"),
            fee_cny=Decimal("5"),
            fee_schedule_id="simulation-v1",
        )
    )

    assert outcome.applied is True
    assert outcome.cash_cny_micros == 99_990_000_000
    assert outcome.position_quantity == 0
    with settlement.session() as session:
        assert session.get(PositionRow, (DEFAULT_ACCOUNT_ID, "603005.SH")) is None
        assert session.scalar(select(func.count()).select_from(FillRow)) == 2


def test_insufficient_cash_rolls_back_without_fill(tmp_path: Path) -> None:
    trading, settlement = repositories(tmp_path)
    trading.create_order(pending_order(quantity=10_000))
    oversized = fill_request(quantity=10_000)

    with pytest.raises(SettlementError, match="现金不足"):
        settlement.apply(oversized)

    with settlement.session() as session:
        order = session.get(OrderRow, "order-1")
        cash = session.get(CashBalanceRow, (DEFAULT_ACCOUNT_ID, Currency.CNY))
        assert order is not None and order.status is OrderStatus.PENDING_OPEN
        assert cash is not None and cash.available_micros == 100_000_000_000
        assert session.scalar(select(func.count()).select_from(FillRow)) == 0
