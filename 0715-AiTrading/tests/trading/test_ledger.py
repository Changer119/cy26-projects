from datetime import date
from decimal import Decimal

from ai_trading.domain import Currency, Instrument, InstrumentType, Market, OrderSide
from ai_trading.trading.ledger import (
    DailyNav,
    Fill,
    LedgerState,
    PriceMark,
    apply_fill,
    attribute_performance,
    calculate_max_drawdown,
    calculate_nav,
)


def instrument(currency: Currency = Currency.CNY) -> Instrument:
    market = Market.SSE if currency is Currency.CNY else Market.HKEX
    return Instrument(
        instrument_id="603005.SH" if market is Market.SSE else "01810.HK",
        name="测试标的",
        market=market,
        currency=currency,
        instrument_type=InstrumentType.STOCK,
        lot_size=100,
        is_tradable=True,
    )


def test_ledger_buy_and_sell_are_pure_and_track_cost_profit_and_fees() -> None:
    original = LedgerState.initial(Decimal("100000"))
    bought = apply_fill(
        original,
        Fill("buy", instrument(), OrderSide.BUY, 100, Decimal("100"), Decimal("1"), Decimal("10")),
    )
    sold = apply_fill(
        bought.state,
        Fill("sell", instrument(), OrderSide.SELL, 40, Decimal("120"), Decimal("1"), Decimal("5")),
    )

    assert original.cash_cny == Decimal("100000")
    assert bought.state.cash_cny == Decimal("89990")
    assert sold.state.cash_cny == Decimal("94785")
    assert sold.state.positions[0].quantity == 60
    assert sold.state.positions[0].cost_cny == Decimal("6000")
    assert sold.state.realized_gross_pnl_cny == Decimal("800")
    assert sold.state.cumulative_fees_cny == Decimal("15")


def test_nav_handles_hkd_fx_without_binary_floating_point() -> None:
    state = apply_fill(
        LedgerState.initial(Decimal("100000")),
        Fill(
            "hk-buy",
            instrument(Currency.HKD),
            OrderSide.BUY,
            100,
            Decimal("10"),
            Decimal("0.92"),
            Decimal("0"),
        ),
    ).state
    marks = (PriceMark("01810.HK", Decimal("12"), Decimal("0.91")),)

    assert calculate_nav(state, marks) == Decimal("100172")


def test_performance_attribution_reconciles_exactly_to_nav_change() -> None:
    original = LedgerState.initial(Decimal("100000"))
    state = apply_fill(
        original,
        Fill("buy", instrument(), OrderSide.BUY, 100, Decimal("100"), Decimal("1"), Decimal("10")),
    ).state
    attribution = attribute_performance(
        state,
        (PriceMark("603005.SH", Decimal("105"), Decimal("1")),),
        initial_nav_cny=Decimal("100000"),
    )

    assert attribution.realized_gross_pnl_cny == Decimal("0")
    assert attribution.unrealized_pnl_cny == Decimal("500")
    assert attribution.fees_cny == Decimal("10")
    assert attribution.total_pnl_cny == Decimal("490")
    assert attribution.total_pnl_cny == attribution.nav_cny - Decimal("100000")


def test_max_drawdown_uses_historical_high_water_mark() -> None:
    navs = (
        DailyNav(date(2026, 7, 1), Decimal("100")),
        DailyNav(date(2026, 7, 2), Decimal("120")),
        DailyNav(date(2026, 7, 3), Decimal("90")),
        DailyNav(date(2026, 7, 4), Decimal("110")),
    )

    result = calculate_max_drawdown(navs)

    assert result.rate == Decimal("0.25")
    assert result.peak_date == date(2026, 7, 2)
    assert result.trough_date == date(2026, 7, 3)
