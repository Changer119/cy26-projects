from datetime import UTC, date, datetime
from decimal import Decimal

from ai_trading.domain import (
    Currency,
    Instrument,
    InstrumentType,
    Market,
    ProposalStatus,
    TradeAction,
    TradePlan,
    TradePlanStatus,
    TradeProposal,
)
from ai_trading.trading.risk import (
    PortfolioPosition,
    PortfolioSnapshot,
    RiskCode,
    RiskInstrument,
    RiskPolicy,
    evaluate_trade_plan,
)


def stock(
    instrument_id: str,
    market: Market = Market.SSE,
    instrument_type: InstrumentType = InstrumentType.STOCK,
    industry: str | None = "芯片",
) -> Instrument:
    return Instrument(
        instrument_id=instrument_id,
        name=instrument_id,
        market=market,
        currency=Currency.CNY,
        instrument_type=instrument_type,
        industry=industry,
        lot_size=100,
        is_tradable=True,
    )


def profile(instrument: Instrument) -> RiskInstrument:
    return RiskInstrument(instrument=instrument, fx_to_cny=Decimal("1"))


def proposal(
    proposal_id: str,
    instrument_id: str,
    action: TradeAction,
    current: int,
    delta: int,
    price: str,
) -> TradeProposal:
    return TradeProposal(
        proposal_id=proposal_id,
        instrument_id=instrument_id,
        action=action,
        current_quantity=current,
        target_quantity=current + delta,
        delta_quantity=delta,
        limit_price=Decimal(price),
        status=ProposalStatus.GENERATED,
        confidence=Decimal("0.8"),
    )


def plan(*proposals: TradeProposal) -> TradePlan:
    return TradePlan(
        plan_id="plan-1",
        account_id="paper",
        trade_date=date(2026, 7, 15),
        decision_asof=datetime(2026, 7, 15, 0, 40, tzinfo=UTC),
        status=TradePlanStatus.DRAFT,
        proposals=proposals,
    )


def snapshot(
    cash: str = "100000",
    nav: str = "100000",
    peak: str = "100000",
    positions: tuple[PortfolioPosition, ...] = (),
) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        cash_available_cny=Decimal(cash),
        nav_cny=Decimal(nav),
        peak_nav_cny=Decimal(peak),
        positions=positions,
    )


def test_worst_case_buys_cannot_depend_on_same_day_sale_proceeds() -> None:
    held = stock("600584.SH")
    state = snapshot(
        cash="20000",
        positions=(
            PortfolioPosition(
                instrument=held,
                quantity=1000,
                sellable_quantity=1000,
                mark_price=Decimal("50"),
                fx_to_cny=Decimal("1"),
            ),
        ),
    )
    trade_plan = plan(
        proposal("sell", held.instrument_id, TradeAction.SELL, 1000, -1000, "50"),
        proposal("buy", "603005.SH", TradeAction.BUY, 0, 300, "100"),
    )

    bought = stock("603005.SH")
    result = evaluate_trade_plan(
        trade_plan,
        state,
        (profile(held), profile(bought)),
        RiskPolicy(),
    )

    assert result.approved is False
    assert RiskCode.INSUFFICIENT_CASH in result.codes
    assert result.required_buying_power_cny == Decimal("30000")


def test_combined_buys_use_worst_case_exposure_for_all_limits() -> None:
    first = stock("603005.SH")
    second = stock("600584.SH")
    trade_plan = plan(
        proposal("first", first.instrument_id, TradeAction.BUY, 0, 300, "100"),
        proposal("second", second.instrument_id, TradeAction.BUY, 0, 400, "100"),
    )

    result = evaluate_trade_plan(
        trade_plan,
        snapshot(),
        (profile(first), profile(second)),
        RiskPolicy(),
    )

    assert result.approved is False
    assert RiskCode.INDUSTRY_LIMIT in result.codes
    assert RiskCode.DAILY_NEW_RISK_LIMIT in result.codes


def test_stock_fund_market_and_turnover_limits_are_enforced() -> None:
    instrument = stock("603005.SH")
    policy = RiskPolicy(
        single_stock_limit=Decimal("0.20"),
        single_fund_limit=Decimal("0.50"),
        single_market_limit=Decimal("0.25"),
        industry_limit=Decimal("0.60"),
        daily_new_risk_limit=Decimal("0.50"),
        daily_turnover_limit=Decimal("0.25"),
    )
    trade_plan = plan(proposal("buy", instrument.instrument_id, TradeAction.BUY, 0, 300, "100"))

    result = evaluate_trade_plan(trade_plan, snapshot(), (profile(instrument),), policy)

    assert result.approved is False
    assert result.codes == (
        RiskCode.SINGLE_INSTRUMENT_LIMIT,
        RiskCode.MARKET_LIMIT,
        RiskCode.DAILY_TURNOVER_LIMIT,
    )


def test_lof_uses_fund_limit_instead_of_stock_limit() -> None:
    fund = stock("160706.SZ", Market.SZSE, InstrumentType.LOF, "基金")
    trade_plan = plan(proposal("fund", fund.instrument_id, TradeAction.BUY, 0, 400, "100"))

    result = evaluate_trade_plan(trade_plan, snapshot(), (profile(fund),), RiskPolicy())

    assert result.approved is True


def test_drawdown_at_twenty_five_percent_stops_new_risk() -> None:
    instrument = stock("603005.SH")
    trade_plan = plan(proposal("buy", instrument.instrument_id, TradeAction.BUY, 0, 100, "100"))

    result = evaluate_trade_plan(
        trade_plan,
        snapshot(cash="75000", nav="75000", peak="100000"),
        (profile(instrument),),
        RiskPolicy(),
    )

    assert result.approved is False
    assert result.codes == (RiskCode.NEW_RISK_STOPPED,)


def test_drawdown_at_thirty_percent_allows_only_sellable_reduction() -> None:
    instrument = stock("603005.SH")
    state = snapshot(
        cash="20000",
        nav="70000",
        peak="100000",
        positions=(
            PortfolioPosition(
                instrument=instrument,
                quantity=500,
                sellable_quantity=300,
                mark_price=Decimal("100"),
                fx_to_cny=Decimal("1"),
            ),
        ),
    )

    reduction = evaluate_trade_plan(
        plan(proposal("sell", instrument.instrument_id, TradeAction.SELL, 500, -300, "99")),
        state,
        (profile(instrument),),
        RiskPolicy(),
    )
    excessive = evaluate_trade_plan(
        plan(proposal("sell", instrument.instrument_id, TradeAction.SELL, 500, -400, "99")),
        state,
        (profile(instrument),),
        RiskPolicy(),
    )

    assert reduction.approved is True
    assert excessive.approved is False
    assert excessive.codes == (RiskCode.NOT_SELLABLE,)
