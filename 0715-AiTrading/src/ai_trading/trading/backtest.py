"""简化事件驱动回测器, 决策证据严格按可用时间校验。"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ai_trading.domain import Instrument, OrderSide, ProposalStatus, TradeAction, TradePlan

from .execution import ExecutionStatus, MarketBar, OrderRequest, execute_opening_order
from .ledger import DailyNav, Fill, LedgerState, PriceMark, apply_fill, calculate_nav


class LookaheadError(ValueError):
    pass


class BacktestDataError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TimedEvidence:
    evidence_id: str
    available_at: datetime


@dataclass(frozen=True, slots=True)
class BacktestDay:
    decision_asof: datetime
    plan: TradePlan
    instruments: tuple[Instrument, ...]
    evidence: tuple[TimedEvidence, ...]
    opening_bars: tuple[MarketBar, ...]
    closing_marks: tuple[PriceMark, ...]


@dataclass(frozen=True, slots=True)
class BacktestResult:
    final_state: LedgerState
    fills: tuple[Fill, ...]
    daily_navs: tuple[DailyNav, ...]


def _instrument(day: BacktestDay, instrument_id: str) -> Instrument:
    result = next(
        (item for item in day.instruments if item.instrument_id == instrument_id),
        None,
    )
    if result is None:
        raise BacktestDataError(f"缺少证券元数据: {instrument_id}")
    return result


def _bar(day: BacktestDay, instrument_id: str) -> MarketBar:
    result = next(
        (item for item in day.opening_bars if item.instrument_id == instrument_id),
        None,
    )
    if result is None:
        raise BacktestDataError(f"缺少开盘行情: {instrument_id}")
    return result


def _mark(day: BacktestDay, instrument_id: str) -> PriceMark:
    result = next(
        (item for item in day.closing_marks if item.instrument_id == instrument_id),
        None,
    )
    if result is None:
        raise BacktestDataError(f"缺少收盘估值: {instrument_id}")
    return result


def run_event_backtest(
    initial_state: LedgerState,
    days: tuple[BacktestDay, ...],
    slippage_rate: Decimal,
) -> BacktestResult:
    state = initial_state
    fills: tuple[Fill, ...] = ()
    navs: tuple[DailyNav, ...] = ()
    previous_decision: datetime | None = None

    for day in days:
        if previous_decision is not None and day.decision_asof <= previous_decision:
            raise BacktestDataError("回测决策事件未严格递增")
        previous_decision = day.decision_asof
        for evidence in day.evidence:
            if evidence.available_at > day.decision_asof:
                raise LookaheadError(f"证据 {evidence.evidence_id} 在决策后才可用")

        for proposal in day.plan.proposals:
            if proposal.status is not ProposalStatus.RISK_APPROVED:
                continue
            if proposal.action is TradeAction.HOLD or proposal.limit_price is None:
                continue
            side = OrderSide.BUY if proposal.action is TradeAction.BUY else OrderSide.SELL
            instrument = _instrument(day, proposal.instrument_id)
            execution = execute_opening_order(
                OrderRequest(
                    order_id=proposal.proposal_id,
                    instrument=instrument,
                    side=side,
                    quantity=abs(proposal.delta_quantity),
                    limit_price=proposal.limit_price,
                ),
                _bar(day, proposal.instrument_id),
                slippage_rate,
            )
            if execution.status is not ExecutionStatus.FILLED or execution.fill_price is None:
                continue
            mark = _mark(day, proposal.instrument_id)
            fill = Fill(
                fill_id=f"fill:{proposal.proposal_id}",
                instrument=instrument,
                side=side,
                quantity=execution.filled_quantity,
                price=execution.fill_price,
                fx_to_cny=mark.fx_to_cny,
                fee_cny=Decimal("0"),
            )
            state = apply_fill(state, fill).state
            fills += (fill,)

        navs += (DailyNav(day.plan.trade_date, calculate_nav(state, day.closing_marks)),)
    return BacktestResult(state, fills, navs)
