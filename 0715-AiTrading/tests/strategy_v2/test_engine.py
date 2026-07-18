from datetime import date
from decimal import Decimal

from pydantic import ValidationError

from ai_trading.domain import (
    Currency,
    Instrument,
    InstrumentType,
    Market,
    TradeAction,
)
from ai_trading.strategy_v2.engine import build_decisions
from ai_trading.strategy_v2.models import StrategyFeatures, TradeSignal
from ai_trading.trading.risk import PortfolioPosition, PortfolioSnapshot


def stock(instrument_id: str = "603005.SH") -> Instrument:
    return Instrument(
        instrument_id=instrument_id,
        name="晶方科技",
        market=Market.SSE,
        currency=Currency.CNY,
        instrument_type=InstrumentType.STOCK,
        industry="半导体",
        lot_size=100,
        is_tradable=True,
    )


def features(instrument_id: str = "603005.SH") -> StrategyFeatures:
    return StrategyFeatures(
        instrument_id=instrument_id,
        as_of=date(2026, 2, 28),
        history_sessions=60,
        close=Decimal("100"),
        sma_20=Decimal("95"),
        sma_60=Decimal("90"),
        atr_20=Decimal("4"),
        average_volume_20=1_000_000,
        support_20=Decimal("88"),
        resistance_20=Decimal("104"),
    )


def snapshot(
    quantity: int = 0,
    cash: str = "100000",
    *,
    sellable_quantity: int | None = None,
    average_cost: str = "100",
    stop_price: str | None = None,
) -> PortfolioSnapshot:
    instrument = stock()
    positions: tuple[PortfolioPosition, ...] = ()
    if quantity:
        positions = (
            PortfolioPosition(
                instrument=instrument,
                quantity=quantity,
                sellable_quantity=(quantity if sellable_quantity is None else sellable_quantity),
                mark_price=Decimal("100"),
                fx_to_cny=Decimal(1),
                average_cost=Decimal(average_cost),
                stop_price=None if stop_price is None else Decimal(stop_price),
            ),
        )
    return PortfolioSnapshot(
        cash_available_cny=Decimal(cash),
        nav_cny=Decimal("100000"),
        peak_nav_cny=Decimal("100000"),
        positions=positions,
    )


def signal(
    action: TradeAction,
    confidence: str = "0.8",
    instrument_id: str = "603005.SH",
) -> TradeSignal:
    return TradeSignal(
        instrument_id=instrument_id,
        action=action,
        confidence=Decimal(confidence),
        reason="趋势与量价结构支持该方向",
    )


def test_ai_signal_cannot_supply_price_or_quantity() -> None:
    try:
        TradeSignal.model_validate(
            {
                "instrument_id": "603005.SH",
                "action": "BUY",
                "confidence": Decimal("0.8"),
                "reason": "模型理由",
                "limit_price": Decimal("120"),
                "target_quantity": 10_000,
            }
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("V2 禁止 AI 指定价格或数量")


def test_buy_price_and_quantity_are_calculated_locally() -> None:
    decision = build_decisions(
        (signal(TradeAction.BUY),),
        (stock(),),
        (features(),),
        snapshot(),
    )[0]

    assert decision.action is TradeAction.BUY
    assert decision.limit_price == Decimal("101.00")
    assert decision.stop_price == Decimal("92.00")
    assert decision.current_quantity == 0
    assert decision.target_quantity == 100
    assert decision.delta_quantity == 100
    assert decision.target_weight == Decimal("0.1")
    assert decision.strategy_version == "AGGRESSIVE_V2"
    assert "趋势与量价结构" in decision.reason


def test_sell_signal_liquidates_only_the_existing_position() -> None:
    decision = build_decisions(
        (signal(TradeAction.SELL),),
        (stock(),),
        (features(),),
        snapshot(quantity=300),
    )[0]

    assert decision.action is TradeAction.SELL
    assert decision.limit_price == Decimal("99.00")
    assert decision.target_quantity == 0
    assert decision.delta_quantity == -300
    assert decision.stop_price is None


def test_sell_signal_never_exceeds_sellable_quantity() -> None:
    decision = build_decisions(
        (signal(TradeAction.SELL),),
        (stock(),),
        (features(),),
        snapshot(quantity=300, sellable_quantity=100),
    )[0]

    assert decision.action is TradeAction.SELL
    assert decision.current_quantity == 300
    assert decision.target_quantity == 200
    assert decision.delta_quantity == -100


def test_local_stop_overrides_ai_hold_for_existing_position() -> None:
    breached = features().model_copy(update={"close": Decimal("90")})

    decision = build_decisions(
        (signal(TradeAction.HOLD, "0"),),
        (stock(),),
        (breached,),
        snapshot(quantity=300, average_cost="100"),
    )[0]

    assert decision.action is TradeAction.SELL
    assert decision.delta_quantity == -300
    assert "本地止损" in decision.reason


def test_local_stop_still_runs_when_ai_omits_the_instrument() -> None:
    breached = features().model_copy(update={"close": Decimal("90")})

    decision = build_decisions(
        (),
        (stock(),),
        (breached,),
        snapshot(quantity=300, average_cost="100"),
    )[0]

    assert decision.action is TradeAction.SELL
    assert decision.delta_quantity == -300
    assert "AI 未提供方向" in decision.reason


def test_filled_entry_stop_is_used_before_dynamic_fallback() -> None:
    not_dynamically_breached = features().model_copy(update={"close": Decimal("95")})

    decision = build_decisions(
        (signal(TradeAction.HOLD, "0"),),
        (stock(),),
        (not_dynamically_breached,),
        snapshot(quantity=300, average_cost="100", stop_price="96"),
    )[0]

    assert decision.action is TradeAction.SELL
    assert "本地止损" in decision.reason


def test_low_confidence_or_unaffordable_buy_becomes_hold() -> None:
    low_confidence = build_decisions(
        (signal(TradeAction.BUY, "0.59"),),
        (stock(),),
        (features(),),
        snapshot(),
    )[0]
    no_cash = build_decisions(
        (signal(TradeAction.BUY),),
        (stock(),),
        (features(),),
        snapshot(cash="1000"),
    )[0]

    assert low_confidence.action is TradeAction.HOLD
    assert "置信度" in low_confidence.reason
    assert no_cash.action is TradeAction.HOLD
    assert "整手" in no_cash.reason


def test_ai_buy_is_blocked_when_local_trend_confirmation_fails() -> None:
    bearish = features().model_copy(update={"sma_20": Decimal("105"), "sma_60": Decimal("110")})

    decision = build_decisions(
        (signal(TradeAction.BUY, "1"),),
        (stock(),),
        (bearish,),
        snapshot(),
    )[0]

    assert decision.action is TradeAction.HOLD
    assert "趋势确认" in decision.reason


def test_multiple_buys_share_one_deterministic_daily_budget() -> None:
    ids = tuple(f"60000{index}.SH" for index in range(1, 7))
    signals = tuple(signal(TradeAction.BUY, "1", item) for item in reversed(ids))
    instruments = tuple(stock(item) for item in ids)
    all_features = tuple(features(item) for item in ids)

    forward = build_decisions(signals, instruments, all_features, snapshot())
    reverse = build_decisions(tuple(reversed(signals)), instruments, all_features, snapshot())

    forward_by_id = {item.instrument_id: item for item in forward}
    reverse_by_id = {item.instrument_id: item for item in reverse}
    assert forward_by_id == reverse_by_id
    new_risk = sum(
        (
            item.delta_quantity * item.limit_price
            for item in forward
            if item.action is TradeAction.BUY and item.limit_price is not None
        ),
        Decimal(0),
    )
    assert new_risk <= Decimal("50000")
    assert sum(item.action is TradeAction.BUY for item in forward) == 4
