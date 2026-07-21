"""带生效日期的可审计模拟费率计算。"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_UP, Decimal

from ai_trading.domain import Currency, Instrument, InstrumentType, OrderSide

FEE_QUANTUM = Decimal("0.000001")


@dataclass(frozen=True, slots=True)
class FeeSchedule:
    schedule_id: str
    effective_from: date
    currency: Currency
    commission_rate: Decimal
    minimum_commission: Decimal
    transfer_rate: Decimal
    stock_buy_tax_rate: Decimal
    stock_sell_tax_rate: Decimal

    def __post_init__(self) -> None:
        rates = (
            self.commission_rate,
            self.minimum_commission,
            self.transfer_rate,
            self.stock_buy_tax_rate,
            self.stock_sell_tax_rate,
        )
        if not self.schedule_id.strip() or any(rate < 0 for rate in rates):
            raise ValueError("费率版本和各项费率必须有效")


@dataclass(frozen=True, slots=True)
class FeeBreakdown:
    schedule_id: str
    commission: Decimal
    transfer: Decimal
    tax: Decimal
    total: Decimal


def _round_up(amount: Decimal) -> Decimal:
    return amount.quantize(FEE_QUANTUM, rounding=ROUND_UP)


def calculate_fees(
    instrument: Instrument,
    side: OrderSide,
    notional: Decimal,
    trade_date: date,
    schedule: FeeSchedule,
) -> FeeBreakdown:
    if notional <= 0:
        raise ValueError("成交金额必须为正数")
    if instrument.currency is not schedule.currency:
        raise ValueError("证券币种与费率版本不匹配")
    if trade_date < schedule.effective_from:
        raise ValueError("费率版本在成交日尚未生效")

    commission = _round_up(max(notional * schedule.commission_rate, schedule.minimum_commission))
    transfer = _round_up(notional * schedule.transfer_rate)
    tax_rate = Decimal(0)
    if instrument.instrument_type is InstrumentType.STOCK:
        tax_rate = (
            schedule.stock_buy_tax_rate if side is OrderSide.BUY else schedule.stock_sell_tax_rate
        )
    tax = _round_up(notional * tax_rate)
    total = commission + transfer + tax
    return FeeBreakdown(
        schedule_id=schedule.schedule_id,
        commission=commission,
        transfer=transfer,
        tax=tax,
        total=total,
    )
