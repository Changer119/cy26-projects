"""不可变模拟账本及可重放绩效计算。"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ai_trading.domain import Instrument, OrderSide


class LedgerError(ValueError):
    pass


class MissingPriceMark(LedgerError):
    pass


@dataclass(frozen=True, slots=True)
class Fill:
    fill_id: str
    instrument: Instrument
    side: OrderSide
    quantity: int
    price: Decimal
    fx_to_cny: Decimal
    fee_cny: Decimal

    @property
    def notional_cny(self) -> Decimal:
        return self.price * self.quantity * self.fx_to_cny


@dataclass(frozen=True, slots=True)
class LedgerPosition:
    instrument: Instrument
    quantity: int
    cost_cny: Decimal


@dataclass(frozen=True, slots=True)
class LedgerState:
    cash_cny: Decimal
    positions: tuple[LedgerPosition, ...]
    realized_gross_pnl_cny: Decimal
    cumulative_fees_cny: Decimal

    @classmethod
    def initial(cls, cash_cny: Decimal) -> "LedgerState":
        return cls(cash_cny, (), Decimal("0"), Decimal("0"))


@dataclass(frozen=True, slots=True)
class LedgerUpdate:
    state: LedgerState
    realized_gross_pnl_cny: Decimal


@dataclass(frozen=True, slots=True)
class PriceMark:
    instrument_id: str
    price: Decimal
    fx_to_cny: Decimal


@dataclass(frozen=True, slots=True)
class PerformanceAttribution:
    nav_cny: Decimal
    realized_gross_pnl_cny: Decimal
    unrealized_pnl_cny: Decimal
    fees_cny: Decimal
    total_pnl_cny: Decimal


@dataclass(frozen=True, slots=True)
class DailyNav:
    trade_date: date
    nav_cny: Decimal


@dataclass(frozen=True, slots=True)
class DrawdownMetric:
    rate: Decimal
    peak_date: date
    trough_date: date


def _position(state: LedgerState, instrument_id: str) -> LedgerPosition | None:
    return next(
        (item for item in state.positions if item.instrument.instrument_id == instrument_id),
        None,
    )


def _replace_position(
    positions: tuple[LedgerPosition, ...],
    replacement: LedgerPosition | None,
    instrument_id: str,
) -> tuple[LedgerPosition, ...]:
    retained = tuple(item for item in positions if item.instrument.instrument_id != instrument_id)
    return retained if replacement is None else (*retained, replacement)


def apply_fill(state: LedgerState, fill: Fill) -> LedgerUpdate:
    """返回新账本, 不修改输入状态。"""

    if fill.quantity <= 0 or fill.price <= 0 or fill.fx_to_cny <= 0 or fill.fee_cny < 0:
        raise LedgerError("成交数量、价格、汇率或费用非法")
    existing = _position(state, fill.instrument.instrument_id)
    notional = fill.notional_cny
    replacement: LedgerPosition | None

    if fill.side is OrderSide.BUY:
        new_cash = state.cash_cny - notional - fill.fee_cny
        if new_cash < 0:
            raise LedgerError("现金不足")
        old_quantity = existing.quantity if existing is not None else 0
        old_cost = existing.cost_cny if existing is not None else Decimal("0")
        replacement = LedgerPosition(
            instrument=fill.instrument,
            quantity=old_quantity + fill.quantity,
            cost_cny=old_cost + notional,
        )
        realized = Decimal("0")
    else:
        if existing is None or fill.quantity > existing.quantity:
            raise LedgerError("持仓不足")
        cost_released = existing.cost_cny * fill.quantity / existing.quantity
        realized = notional - cost_released
        new_cash = state.cash_cny + notional - fill.fee_cny
        remaining = existing.quantity - fill.quantity
        replacement = (
            None
            if remaining == 0
            else LedgerPosition(existing.instrument, remaining, existing.cost_cny - cost_released)
        )

    new_state = LedgerState(
        cash_cny=new_cash,
        positions=_replace_position(
            state.positions,
            replacement,
            fill.instrument.instrument_id,
        ),
        realized_gross_pnl_cny=state.realized_gross_pnl_cny + realized,
        cumulative_fees_cny=state.cumulative_fees_cny + fill.fee_cny,
    )
    return LedgerUpdate(new_state, realized)


def _mark(marks: tuple[PriceMark, ...], instrument_id: str) -> PriceMark:
    result = next((item for item in marks if item.instrument_id == instrument_id), None)
    if result is None:
        raise MissingPriceMark(f"缺少估值价格: {instrument_id}")
    return result


def calculate_nav(state: LedgerState, marks: tuple[PriceMark, ...]) -> Decimal:
    market_value = sum(
        (
            _mark(marks, item.instrument.instrument_id).price
            * item.quantity
            * _mark(marks, item.instrument.instrument_id).fx_to_cny
            for item in state.positions
        ),
        Decimal("0"),
    )
    return state.cash_cny + market_value


def attribute_performance(
    state: LedgerState,
    marks: tuple[PriceMark, ...],
    initial_nav_cny: Decimal,
) -> PerformanceAttribution:
    nav = calculate_nav(state, marks)
    unrealized = sum(
        (
            _mark(marks, item.instrument.instrument_id).price
            * item.quantity
            * _mark(marks, item.instrument.instrument_id).fx_to_cny
            - item.cost_cny
            for item in state.positions
        ),
        Decimal("0"),
    )
    total = state.realized_gross_pnl_cny + unrealized - state.cumulative_fees_cny
    if total != nav - initial_nav_cny:
        raise LedgerError("绩效归因与净值变化不一致")
    return PerformanceAttribution(
        nav,
        state.realized_gross_pnl_cny,
        unrealized,
        state.cumulative_fees_cny,
        total,
    )


def calculate_max_drawdown(navs: tuple[DailyNav, ...]) -> DrawdownMetric:
    if not navs:
        raise LedgerError("净值序列不能为空")
    peak_nav = navs[0].nav_cny
    peak_date = navs[0].trade_date
    result = DrawdownMetric(Decimal("0"), peak_date, peak_date)
    for item in navs:
        if item.nav_cny > peak_nav:
            peak_nav = item.nav_cny
            peak_date = item.trade_date
        drawdown = (peak_nav - item.nav_cny) / peak_nav
        if drawdown > result.rate:
            result = DrawdownMetric(drawdown, peak_date, item.trade_date)
    return result
