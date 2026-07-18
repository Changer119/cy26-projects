from datetime import date
from decimal import Decimal

from ai_trading.domain import (
    Currency,
    Instrument,
    InstrumentType,
    Market,
    OrderSide,
)
from ai_trading.trading.fees import FeeSchedule, calculate_fees


def instrument(instrument_type: InstrumentType) -> Instrument:
    return Instrument(
        instrument_id="603005.SH",
        name="测试标的",
        market=Market.SSE,
        currency=Currency.CNY,
        instrument_type=instrument_type,
        industry="测试行业",
        lot_size=100,
        is_tradable=True,
    )


def schedule() -> FeeSchedule:
    return FeeSchedule(
        schedule_id="a-share-simulation-v1",
        effective_from=date(2026, 1, 1),
        currency=Currency.CNY,
        commission_rate=Decimal("0.0003"),
        minimum_commission=Decimal("5"),
        transfer_rate=Decimal("0.00001"),
        stock_buy_tax_rate=Decimal("0"),
        stock_sell_tax_rate=Decimal("0.0005"),
    )


def test_stock_sale_includes_minimum_commission_transfer_and_sell_tax() -> None:
    result = calculate_fees(
        instrument(InstrumentType.STOCK),
        OrderSide.SELL,
        Decimal("10000"),
        date(2026, 7, 15),
        schedule(),
    )

    assert result.commission == Decimal("5.000000")
    assert result.transfer == Decimal("0.100000")
    assert result.tax == Decimal("5.000000")
    assert result.total == Decimal("10.100000")


def test_exchange_traded_fund_does_not_apply_stock_stamp_tax() -> None:
    result = calculate_fees(
        instrument(InstrumentType.ETF),
        OrderSide.SELL,
        Decimal("10000"),
        date(2026, 7, 15),
        schedule(),
    )

    assert result.tax == Decimal("0.000000")
    assert result.total == Decimal("5.100000")


def test_schedule_cannot_be_used_before_effective_date() -> None:
    try:
        calculate_fees(
            instrument(InstrumentType.STOCK),
            OrderSide.BUY,
            Decimal("10000"),
            date(2025, 12, 31),
            schedule(),
        )
    except ValueError as exc:
        assert "尚未生效" in str(exc)
    else:
        raise AssertionError("费率版本生效前必须拒绝计算")
