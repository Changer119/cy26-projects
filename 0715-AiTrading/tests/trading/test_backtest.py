from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

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
from ai_trading.trading.backtest import (
    BacktestDay,
    LookaheadError,
    TimedEvidence,
    run_event_backtest,
)
from ai_trading.trading.execution import MarketBar
from ai_trading.trading.ledger import LedgerState, PriceMark


def instrument() -> Instrument:
    return Instrument(
        instrument_id="603005.SH",
        name="晶方科技",
        market=Market.SSE,
        currency=Currency.CNY,
        instrument_type=InstrumentType.STOCK,
        lot_size=100,
        is_tradable=True,
    )


def trade_plan(decision_asof: datetime) -> TradePlan:
    return TradePlan(
        plan_id="plan",
        account_id="paper",
        trade_date=date(2026, 7, 15),
        decision_asof=decision_asof,
        status=TradePlanStatus.RISK_CHECKED,
        proposals=(
            TradeProposal(
                proposal_id="proposal",
                instrument_id="603005.SH",
                action=TradeAction.BUY,
                current_quantity=0,
                target_quantity=100,
                delta_quantity=100,
                limit_price=Decimal("101"),
                status=ProposalStatus.RISK_APPROVED,
                confidence=Decimal("0.8"),
            ),
        ),
    )


def market_bar() -> MarketBar:
    return MarketBar(
        instrument_id="603005.SH",
        session_date=date(2026, 7, 15),
        open_price=Decimal("100"),
        high_price=Decimal("106"),
        low_price=Decimal("99"),
        close_price=Decimal("105"),
        volume=100_000,
        available_at=datetime(2026, 7, 15, 8, 30, tzinfo=UTC),
    )


def test_event_backtest_executes_open_then_values_close() -> None:
    decision_time = datetime(2026, 7, 15, 0, 40, tzinfo=UTC)
    day = BacktestDay(
        decision_asof=decision_time,
        plan=trade_plan(decision_time),
        instruments=(instrument(),),
        evidence=(TimedEvidence("prior-close", decision_time),),
        opening_bars=(market_bar(),),
        closing_marks=(PriceMark("603005.SH", Decimal("105"), Decimal("1")),),
    )

    result = run_event_backtest(
        LedgerState.initial(Decimal("100000")),
        (day,),
        slippage_rate=Decimal("0.002"),
    )

    assert len(result.fills) == 1
    assert result.fills[0].price == Decimal("100.200")
    assert result.daily_navs[0].nav_cny == Decimal("100480.000")


def test_event_backtest_rejects_future_evidence() -> None:
    decision_time = datetime(2026, 7, 15, 0, 40, tzinfo=UTC)
    future = datetime(2026, 7, 15, 0, 41, tzinfo=UTC)
    day = BacktestDay(
        decision_asof=decision_time,
        plan=trade_plan(decision_time),
        instruments=(instrument(),),
        evidence=(TimedEvidence("future", future),),
        opening_bars=(market_bar(),),
        closing_marks=(PriceMark("603005.SH", Decimal("105"), Decimal("1")),),
    )

    with pytest.raises(LookaheadError, match="future"):
        run_event_backtest(LedgerState.initial(Decimal("100000")), (day,), Decimal("0.002"))
