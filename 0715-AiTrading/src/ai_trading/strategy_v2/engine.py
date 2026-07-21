from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal

from ai_trading.domain import Instrument, InstrumentType, TradeAction
from ai_trading.strategy_v2.models import (
    StrategyDecision,
    StrategyFeatures,
    StrategyPolicy,
    TradeSignal,
)
from ai_trading.trading.risk import PortfolioPosition, PortfolioSnapshot

DEFAULT_STRATEGY_POLICY = StrategyPolicy()


def build_decisions(
    signals: tuple[TradeSignal, ...],
    instruments: tuple[Instrument, ...],
    features: tuple[StrategyFeatures, ...],
    snapshot: PortfolioSnapshot,
    policy: StrategyPolicy = DEFAULT_STRATEGY_POLICY,
) -> tuple[StrategyDecision, ...]:
    """AI 只给方向；价格、止损与数量全部由本地可复算规则生成。"""

    ids = tuple(item.instrument_id for item in signals)
    if len(ids) != len(set(ids)):
        raise ValueError("AI 信号包含重复标的")
    missing_signals = tuple(
        TradeSignal(
            instrument_id=item.instrument_id,
            action=TradeAction.HOLD,
            confidence=Decimal(0),
            reason="AI 未提供方向，执行本地保护规则",
        )
        for item in features
        if item.instrument_id not in ids
    )
    decisions: tuple[StrategyDecision, ...] = ()
    remaining_cash = snapshot.cash_available_cny
    remaining_new_risk = snapshot.nav_cny * policy.daily_new_risk_limit
    ordered = sorted(
        (*signals, *missing_signals),
        key=lambda item: (
            0 if item.action is TradeAction.BUY else 1,
            -item.confidence,
            item.instrument_id,
        ),
    )
    for signal in ordered:
        instrument = next(
            (item for item in instruments if item.instrument_id == signal.instrument_id),
            None,
        )
        feature = next(
            (item for item in features if item.instrument_id == signal.instrument_id),
            None,
        )
        if instrument is None or feature is None:
            raise ValueError("AI 信号缺少证券主数据或 V2 历史特征")
        position = _position(snapshot, signal.instrument_id)
        current = 0 if position is None else position.quantity
        sellable = 0 if position is None else position.sellable_quantity
        if _local_stop_breached(position, feature, instrument, policy):
            decisions += (
                _sell(signal, instrument, feature, current, sellable, snapshot, policy, "本地止损"),
            )
        elif signal.confidence < policy.minimum_confidence:
            decisions += (_hold(signal, feature, current, snapshot, "置信度低于 60% 门槛"),)
        elif signal.action is TradeAction.BUY and not _buy_trend_confirmed(feature):
            decisions += (_hold(signal, feature, current, snapshot, "本地中期趋势确认失败"),)
        elif signal.action is TradeAction.BUY:
            decision = _buy(
                signal,
                instrument,
                feature,
                current,
                snapshot,
                remaining_cash,
                remaining_new_risk,
                policy,
            )
            decisions += (decision,)
            if decision.action is TradeAction.BUY and decision.limit_price is not None:
                notional = decision.delta_quantity * decision.limit_price
                remaining_new_risk -= notional
                remaining_cash -= notional * (Decimal(1) + policy.cash_fee_buffer)
        elif signal.action is TradeAction.SELL:
            decisions += (_sell(signal, instrument, feature, current, sellable, snapshot, policy),)
        else:
            decisions += (_hold(signal, feature, current, snapshot, "AI 建议继续持有"),)
    return tuple(sorted(decisions, key=lambda item: item.instrument_id))


def _buy(
    signal: TradeSignal,
    instrument: Instrument,
    feature: StrategyFeatures,
    current: int,
    snapshot: PortfolioSnapshot,
    cash_available: Decimal,
    new_risk_available: Decimal,
    policy: StrategyPolicy,
) -> StrategyDecision:
    lot = instrument.lot_size
    if not instrument.is_tradable or lot is None:
        return _hold(signal, feature, current, snapshot, "证券不可交易或整手未知")
    tick = _price_tick(instrument)
    raw_limit = min(
        feature.close + feature.atr_20 * policy.atr_entry_fraction,
        feature.close * (Decimal(1) + policy.maximum_entry_gap),
    )
    limit_price = _round_down(raw_limit, tick)
    stop_distance = max(
        feature.atr_20 * policy.atr_stop_multiple,
        feature.close * policy.minimum_stop_fraction,
    )
    stop_price = _round_down(feature.close - stop_distance, tick)
    if stop_price <= 0 or limit_price <= stop_price:
        return _hold(signal, feature, current, snapshot, "波动过大，无法形成正的止损价格")

    risk_budget = snapshot.nav_cny * policy.risk_per_trade * signal.confidence
    by_risk = _lots(risk_budget / (limit_price - stop_price), lot)
    position_limit = (
        Decimal("0.50")
        if instrument.instrument_type in (InstrumentType.ETF, InstrumentType.LOF)
        else Decimal("0.30")
    )
    by_exposure = _lots(snapshot.nav_cny * position_limit / limit_price, lot)
    desired_total = min(by_risk, by_exposure)
    desired_delta = max(0, desired_total - current)
    by_cash = _lots(
        cash_available / (limit_price * (Decimal(1) + policy.cash_fee_buffer)),
        lot,
    )
    by_liquidity = _lots(
        Decimal(feature.average_volume_20) * policy.liquidity_fraction,
        lot,
    )
    by_daily_budget = _lots(
        new_risk_available / limit_price,
        lot,
    )
    delta = min(desired_delta, by_cash, by_liquidity, by_daily_budget)
    if delta <= 0:
        return _hold(signal, feature, current, snapshot, "预算取整后不足一个整手")
    target = current + delta
    return StrategyDecision(
        instrument_id=signal.instrument_id,
        action=TradeAction.BUY,
        current_quantity=current,
        target_quantity=target,
        delta_quantity=delta,
        limit_price=limit_price,
        stop_price=stop_price,
        reference_price=feature.close,
        confidence=signal.confidence,
        target_weight=_weight(target, feature.close, snapshot),
        reason=f"{signal.reason}；本地规则：ATR 限价、1.5% 风险预算与整手仓位",
    )


def _sell(
    signal: TradeSignal,
    instrument: Instrument,
    feature: StrategyFeatures,
    current: int,
    sellable: int,
    snapshot: PortfolioSnapshot,
    policy: StrategyPolicy,
    local_reason: str = "按 ATR 保护限价退出全部可卖持仓",
) -> StrategyDecision:
    if current <= 0:
        return _hold(signal, feature, current, snapshot, "当前没有可卖持仓")
    if not instrument.is_tradable or instrument.lot_size is None:
        return _hold(signal, feature, current, snapshot, "证券不可交易或整手未知")
    quantity = min(current, sellable)
    if quantity <= 0:
        return _hold(signal, feature, current, snapshot, "当前持仓不可卖")
    raw_limit = max(
        feature.close - feature.atr_20 * policy.atr_entry_fraction,
        feature.close * (Decimal(1) - policy.maximum_entry_gap),
    )
    limit_price = _round_up(raw_limit, _price_tick(instrument))
    return StrategyDecision(
        instrument_id=signal.instrument_id,
        action=TradeAction.SELL,
        current_quantity=current,
        target_quantity=current - quantity,
        delta_quantity=-quantity,
        limit_price=limit_price,
        stop_price=None,
        reference_price=feature.close,
        confidence=signal.confidence,
        target_weight=Decimal(0),
        reason=f"{signal.reason}；本地规则：{local_reason}",
    )


def _hold(
    signal: TradeSignal,
    feature: StrategyFeatures,
    current: int,
    snapshot: PortfolioSnapshot,
    local_reason: str,
) -> StrategyDecision:
    return StrategyDecision(
        instrument_id=signal.instrument_id,
        action=TradeAction.HOLD,
        current_quantity=current,
        target_quantity=current,
        delta_quantity=0,
        limit_price=None,
        stop_price=None,
        reference_price=feature.close,
        confidence=signal.confidence,
        target_weight=_weight(current, feature.close, snapshot),
        reason=f"{signal.reason}；本地规则：{local_reason}",
    )


def _position(snapshot: PortfolioSnapshot, instrument_id: str) -> PortfolioPosition | None:
    return next(
        (item for item in snapshot.positions if item.instrument.instrument_id == instrument_id),
        None,
    )


def _buy_trend_confirmed(feature: StrategyFeatures) -> bool:
    return feature.close > feature.sma_20 >= feature.sma_60


def _local_stop_breached(
    position: PortfolioPosition | None,
    feature: StrategyFeatures,
    instrument: Instrument,
    policy: StrategyPolicy,
) -> bool:
    if position is None:
        return False
    if position.stop_price is not None:
        return feature.close <= position.stop_price
    if position.average_cost is None or position.average_cost <= 0:
        return False
    distance = max(
        feature.atr_20 * policy.atr_stop_multiple,
        position.average_cost * policy.minimum_stop_fraction,
    )
    stop = _round_down(position.average_cost - distance, _price_tick(instrument))
    return stop > 0 and feature.close <= stop


def _price_tick(instrument: Instrument) -> Decimal:
    if instrument.instrument_type in (InstrumentType.ETF, InstrumentType.LOF):
        return Decimal("0.001")
    return Decimal("0.01")


def _lots(quantity: Decimal, lot_size: int) -> int:
    whole = int(quantity.to_integral_value(rounding=ROUND_FLOOR))
    return whole // lot_size * lot_size


def _round_down(value: Decimal, tick: Decimal) -> Decimal:
    units = (value / tick).to_integral_value(rounding=ROUND_FLOOR)
    return units * tick


def _round_up(value: Decimal, tick: Decimal) -> Decimal:
    units = (value / tick).to_integral_value(rounding=ROUND_CEILING)
    return units * tick


def _weight(quantity: int, price: Decimal, snapshot: PortfolioSnapshot) -> Decimal:
    if snapshot.nav_cny <= 0:
        return Decimal(0)
    return Decimal(quantity) * price / snapshot.nav_cny
