from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from ai_trading.domain import (
    Currency,
    Instrument,
    InstrumentType,
    Market,
    Order,
    OrderSide,
    OrderStatus,
    Position,
    ProposalStatus,
    TradeAction,
    TradePlan,
    TradePlanStatus,
    TradeProposal,
)


def make_proposal(
    proposal_id: str = "proposal-1",
    instrument_id: str = "603005.SH",
) -> TradeProposal:
    return TradeProposal(
        proposal_id=proposal_id,
        instrument_id=instrument_id,
        action=TradeAction.BUY,
        current_quantity=0,
        target_quantity=100,
        delta_quantity=100,
        limit_price=Decimal("25.123456"),
        status=ProposalStatus.GENERATED,
        confidence=Decimal("0.75"),
    )


def test_instrument_requires_verified_lot_before_becoming_tradable() -> None:
    pending = Instrument(
        instrument_id="02513.HK",
        name="智谱",
        market=Market.HKEX,
        currency=Currency.HKD,
        instrument_type=InstrumentType.STOCK,
        lot_size=None,
        is_tradable=False,
    )

    assert pending.lot_size is None
    with pytest.raises(ValidationError, match="整手"):
        Instrument(
            instrument_id="02513.HK",
            name="智谱",
            market=Market.HKEX,
            currency=Currency.HKD,
            instrument_type=InstrumentType.STOCK,
            lot_size=None,
            is_tradable=True,
        )


def test_instrument_accepts_optional_typed_industry() -> None:
    instrument = Instrument(
        instrument_id="603005.SH",
        name="晶方科技",
        market=Market.SSE,
        currency=Currency.CNY,
        instrument_type=InstrumentType.STOCK,
        industry="半导体",
        lot_size=100,
        is_tradable=True,
    )

    assert instrument.industry == "半导体"


def test_instrument_rejects_market_suffix_or_currency_mismatch() -> None:
    with pytest.raises(ValidationError, match="市场"):
        Instrument(
            instrument_id="02513.HK",
            name="错误标的",
            market=Market.SSE,
            currency=Currency.CNY,
            instrument_type=InstrumentType.STOCK,
            lot_size=100,
            is_tradable=True,
        )


def test_trade_proposal_rejects_delta_inconsistent_with_action() -> None:
    with pytest.raises(ValidationError, match="BUY"):
        TradeProposal(
            proposal_id="proposal-invalid",
            instrument_id="603005.SH",
            action=TradeAction.BUY,
            current_quantity=100,
            target_quantity=0,
            delta_quantity=-100,
            limit_price=Decimal("25"),
            status=ProposalStatus.GENERATED,
            confidence=Decimal("0.50"),
        )


def test_trade_plan_rejects_duplicate_instrument_proposals() -> None:
    proposal = make_proposal()
    with pytest.raises(ValidationError, match="同一标的"):
        TradePlan(
            plan_id="plan-1",
            account_id="paper-main",
            trade_date=date(2026, 7, 15),
            decision_asof=datetime(2026, 7, 15, 8, 35, tzinfo=ZoneInfo("Asia/Shanghai")),
            status=TradePlanStatus.DRAFT,
            proposals=(proposal, proposal.model_copy(update={"proposal_id": "proposal-2"})),
        )


def test_negative_position_is_rejected_at_domain_boundary() -> None:
    with pytest.raises(ValidationError):
        Position(
            account_id="paper-main",
            instrument_id="603005.SH",
            quantity=-1,
            average_cost=Decimal("10"),
        )


def test_order_and_state_enums_cover_the_paper_trading_lifecycle() -> None:
    order = Order(
        order_id="order-1",
        account_id="paper-main",
        instrument_id="603005.SH",
        trade_date=date(2026, 7, 15),
        side=OrderSide.BUY,
        quantity=100,
        limit_price=Decimal("25.12"),
        status=OrderStatus.PENDING_OPEN,
    )

    assert order.status is OrderStatus.PENDING_OPEN
    assert set(OrderStatus) == {
        OrderStatus.PENDING_OPEN,
        OrderStatus.FILLED,
        OrderStatus.UNFILLED,
        OrderStatus.EXECUTION_REJECTED,
        OrderStatus.DATA_UNAVAILABLE,
    }
    assert set(ProposalStatus) == {
        ProposalStatus.GENERATED,
        ProposalStatus.RISK_APPROVED,
        ProposalStatus.RISK_REJECTED,
        ProposalStatus.HOLD,
    }
    assert set(TradePlanStatus) == {
        TradePlanStatus.DRAFT,
        TradePlanStatus.RISK_CHECKED,
        TradePlanStatus.FROZEN,
        TradePlanStatus.RECONCILED,
        TradePlanStatus.ABORTED,
    }
