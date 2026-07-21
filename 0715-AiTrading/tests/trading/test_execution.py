from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from ai_trading.domain import Currency, Instrument, InstrumentType, Market, OrderSide
from ai_trading.trading.execution import (
    ExecutionStatus,
    MarketBar,
    OrderRequest,
    UnfilledReason,
    execute_opening_order,
)


def instrument(lot_size: int = 100) -> Instrument:
    return Instrument(
        instrument_id="603005.SH",
        name="晶方科技",
        market=Market.SSE,
        currency=Currency.CNY,
        instrument_type=InstrumentType.STOCK,
        lot_size=lot_size,
        is_tradable=True,
    )


def bar(
    opening: str = "100",
    volume: int = 100_000,
    suspended: bool = False,
    locked_up: bool = False,
    locked_down: bool = False,
) -> MarketBar:
    return MarketBar(
        instrument_id="603005.SH",
        session_date=date(2026, 7, 15),
        open_price=Decimal(opening),
        high_price=Decimal("110"),
        low_price=Decimal("90"),
        close_price=Decimal("105"),
        volume=volume,
        available_at=datetime(2026, 7, 15, 8, 30, tzinfo=UTC),
        suspended=suspended,
        locked_limit_up=locked_up,
        locked_limit_down=locked_down,
    )


def order(side: OrderSide, quantity: int = 100, limit: str = "101") -> OrderRequest:
    return OrderRequest(
        order_id="order-1",
        instrument=instrument(),
        side=side,
        quantity=quantity,
        limit_price=Decimal(limit),
    )


def test_opening_limit_order_is_all_or_none_with_adverse_slippage() -> None:
    result = execute_opening_order(
        order(OrderSide.BUY),
        bar(),
        slippage_rate=Decimal("0.002"),
    )

    assert result.status is ExecutionStatus.FILLED
    assert result.filled_quantity == 100
    assert result.fill_price == Decimal("100.200")


def test_slippage_never_crosses_limit_price() -> None:
    buy = execute_opening_order(
        order(OrderSide.BUY, limit="100.1"),
        bar(),
        slippage_rate=Decimal("0.002"),
    )
    sell = execute_opening_order(
        order(OrderSide.SELL, limit="99.9"),
        bar(),
        slippage_rate=Decimal("0.002"),
    )

    assert buy.fill_price == Decimal("100.1")
    assert sell.fill_price == Decimal("99.9")


@pytest.mark.parametrize(
    ("side", "opening", "limit"),
    (
        (OrderSide.BUY, "102", "101"),
        (OrderSide.SELL, "98", "99"),
    ),
)
def test_open_outside_limit_is_unfilled(side: OrderSide, opening: str, limit: str) -> None:
    result = execute_opening_order(order(side, limit=limit), bar(opening=opening), Decimal("0.002"))

    assert result.status is ExecutionStatus.UNFILLED
    assert result.reason is UnfilledReason.OUTSIDE_LIMIT
    assert result.filled_quantity == 0


@pytest.mark.parametrize(
    ("market_bar", "side", "reason"),
    (
        (bar(suspended=True), OrderSide.BUY, UnfilledReason.SUSPENDED),
        (bar(volume=0), OrderSide.BUY, UnfilledReason.ZERO_VOLUME),
        (bar(locked_up=True), OrderSide.BUY, UnfilledReason.LIMIT_LOCKED),
        (bar(locked_down=True), OrderSide.SELL, UnfilledReason.LIMIT_LOCKED),
    ),
)
def test_uncertain_opening_conditions_fail_closed(
    market_bar: MarketBar,
    side: OrderSide,
    reason: UnfilledReason,
) -> None:
    result = execute_opening_order(order(side), market_bar, Decimal("0.002"))

    assert result.status is ExecutionStatus.UNFILLED
    assert result.reason is reason


def test_order_must_follow_dynamic_board_lot() -> None:
    invalid = OrderRequest(
        order_id="odd",
        instrument=instrument(lot_size=200),
        side=OrderSide.BUY,
        quantity=100,
        limit_price=Decimal("101"),
    )

    result = execute_opening_order(invalid, bar(), Decimal("0.002"))

    assert result.status is ExecutionStatus.UNFILLED
    assert result.reason is UnfilledReason.INVALID_LOT


@pytest.mark.parametrize("slippage", (Decimal("-0.001"), Decimal("1")))
def test_invalid_slippage_is_rejected(slippage: Decimal) -> None:
    with pytest.raises(ValueError, match="滑点"):
        execute_opening_order(order(OrderSide.BUY), bar(), slippage)
