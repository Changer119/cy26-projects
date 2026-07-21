"""基于合格日线的保守开盘成交模型。"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from ai_trading.domain import Instrument, OrderSide


class ExecutionStatus(StrEnum):
    FILLED = "FILLED"
    UNFILLED = "UNFILLED"


class UnfilledReason(StrEnum):
    OUTSIDE_LIMIT = "OUTSIDE_LIMIT"
    SUSPENDED = "SUSPENDED"
    ZERO_VOLUME = "ZERO_VOLUME"
    LIMIT_LOCKED = "LIMIT_LOCKED"
    INVALID_LOT = "INVALID_LOT"
    NOT_TRADABLE = "NOT_TRADABLE"
    DATA_MISMATCH = "DATA_MISMATCH"


@dataclass(frozen=True, slots=True)
class MarketBar:
    instrument_id: str
    session_date: date
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    available_at: datetime
    suspended: bool = False
    locked_limit_up: bool = False
    locked_limit_down: bool = False


@dataclass(frozen=True, slots=True)
class OrderRequest:
    order_id: str
    instrument: Instrument
    side: OrderSide
    quantity: int
    limit_price: Decimal


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    order_id: str
    status: ExecutionStatus
    filled_quantity: int
    fill_price: Decimal | None
    reason: UnfilledReason | None


def _unfilled(order_id: str, reason: UnfilledReason) -> ExecutionResult:
    return ExecutionResult(order_id, ExecutionStatus.UNFILLED, 0, None, reason)


def execute_opening_order(
    order: OrderRequest,
    market_bar: MarketBar,
    slippage_rate: Decimal,
) -> ExecutionResult:
    """按全成或全不成语义成交, 不确定条件一律不成交。"""

    if slippage_rate < 0 or slippage_rate >= 1:
        raise ValueError("滑点比例必须在 [0, 1) 范围内")
    if market_bar.instrument_id != order.instrument.instrument_id:
        return _unfilled(order.order_id, UnfilledReason.DATA_MISMATCH)
    if not order.instrument.is_tradable:
        return _unfilled(order.order_id, UnfilledReason.NOT_TRADABLE)
    lot_size = order.instrument.lot_size
    if lot_size is None or order.quantity <= 0 or order.quantity % lot_size != 0:
        return _unfilled(order.order_id, UnfilledReason.INVALID_LOT)
    if market_bar.suspended:
        return _unfilled(order.order_id, UnfilledReason.SUSPENDED)
    if market_bar.volume == 0:
        return _unfilled(order.order_id, UnfilledReason.ZERO_VOLUME)
    if order.side is OrderSide.BUY and market_bar.locked_limit_up:
        return _unfilled(order.order_id, UnfilledReason.LIMIT_LOCKED)
    if order.side is OrderSide.SELL and market_bar.locked_limit_down:
        return _unfilled(order.order_id, UnfilledReason.LIMIT_LOCKED)

    opening = market_bar.open_price
    if order.side is OrderSide.BUY:
        if opening > order.limit_price:
            return _unfilled(order.order_id, UnfilledReason.OUTSIDE_LIMIT)
        price = min(opening * (Decimal("1") + slippage_rate), order.limit_price)
    else:
        if opening < order.limit_price:
            return _unfilled(order.order_id, UnfilledReason.OUTSIDE_LIMIT)
        price = max(opening * (Decimal("1") - slippage_rate), order.limit_price)

    return ExecutionResult(
        order_id=order.order_id,
        status=ExecutionStatus.FILLED,
        filled_quantity=order.quantity,
        fill_price=price,
        reason=None,
    )
