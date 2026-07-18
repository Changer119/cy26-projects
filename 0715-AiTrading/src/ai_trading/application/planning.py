from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from ai_trading.application.models import (
    QualifiedMarketEvidence,
    StrategyDecisionContext,
    WorkflowReport,
    WorkflowStatus,
)
from ai_trading.application.ports import ProposalUnavailable
from ai_trading.domain import (
    Instrument,
    InstrumentId,
    Market,
    Order,
    OrderSide,
    OrderStatus,
    ProposalStatus,
    TradeAction,
    TradePlan,
    TradeProposal,
)
from ai_trading.integrations.deepseek import DeepSeekClient, DeepSeekClientError
from ai_trading.strategy_v2.history import completed_session_dates
from ai_trading.strategy_v2.models import StrategyDecision, StrategyFeatures, TradeSignal
from ai_trading.trading.risk import RiskInstrument


class _AiCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    instrument_id: InstrumentId
    action: TradeAction
    confidence: Decimal = Field(ge=Decimal(0), le=Decimal(1))
    reason: str = Field(min_length=2, max_length=500)


class _AiProposalBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposals: tuple[_AiCandidate, ...]


_EVIDENCE_ADAPTER = TypeAdapter(tuple[StrategyDecisionContext, ...])


def premarket_timing_rejection(trade_date: date, decision_asof: datetime) -> str | None:
    if decision_asof.utcoffset() is None:
        return "DECISION_TIMEZONE_MISSING"
    local = decision_asof.astimezone(ZoneInfo("Asia/Shanghai"))
    if local.date() != trade_date:
        return "DECISION_DATE_MISMATCH"
    try:
        completed_session_dates(Market.SSE, trade_date, 1)
    except ValueError:
        return "NON_TRADING_DAY"
    if (local.hour, local.minute) > (8, 45):
        return "PREMARKET_CUTOFF_EXCEEDED"
    return None


def basic_workflow_report(
    command: str,
    trade_date: date,
    status: WorkflowStatus,
    reason: str,
) -> WorkflowReport:
    if command == "premarket":
        return WorkflowReport(
            command="premarket", status=status, trade_date=trade_date, reason=reason
        )
    return WorkflowReport(command="postmarket", status=status, trade_date=trade_date, reason=reason)


class DeepSeekProposalSource:
    """DeepSeek 只能产生候选意图，不能写订单或绕过本地风控。"""

    def __init__(self, client: DeepSeekClient) -> None:
        self._client = client

    def propose(
        self,
        context: tuple[StrategyDecisionContext, ...],
    ) -> tuple[TradeSignal, ...]:
        if not context:
            return ()
        prompt = _EVIDENCE_ADAPTER.dump_json(context).decode()
        try:
            batch = self._client.complete_json(
                system_prompt=(
                    "你是 AGGRESSIVE_V2 模拟交易方向分析器。仅输出 JSON。"
                    "你只能给 BUY、SELL、HOLD、置信度和简短理由，"
                    "不得给价格、数量，不得调用券商。每个标的最多一条信号。"
                ),
                user_prompt=(
                    "根据以下已通过双源质量门的行情与 V2 历史特征给出 proposals。"
                    "本地规则将独立计算限价、止损和仓位，禁止在理由中伪造这些数值。"
                    f"行情：{prompt}"
                ),
                response_model=_AiProposalBatch,
            )
            return self._to_domain(batch, context)
        except DeepSeekClientError as exc:
            raise ProposalUnavailable("DeepSeek 提案不可用") from exc

    @staticmethod
    def _to_domain(
        batch: _AiProposalBatch,
        context: tuple[StrategyDecisionContext, ...],
    ) -> tuple[TradeSignal, ...]:
        ids = tuple(item.instrument_id for item in batch.proposals)
        if len(ids) != len(set(ids)):
            raise ProposalUnavailable("DeepSeek 返回重复标的")
        result: tuple[TradeSignal, ...] = ()
        for candidate in batch.proposals:
            evidence = next(
                (item for item in context if item.market.instrument_id == candidate.instrument_id),
                None,
            )
            if evidence is None:
                raise ProposalUnavailable("DeepSeek 返回数据门之外的标的")
            result += (
                TradeSignal(
                    instrument_id=candidate.instrument_id,
                    action=candidate.action,
                    confidence=candidate.confidence,
                    reason=candidate.reason,
                ),
            )
        return result


def build_decision_context(
    evidence: tuple[QualifiedMarketEvidence, ...],
    features: tuple[StrategyFeatures, ...],
) -> tuple[StrategyDecisionContext, ...]:
    context: tuple[StrategyDecisionContext, ...] = ()
    for market in evidence:
        feature = next(
            (item for item in features if item.instrument_id == market.instrument_id),
            None,
        )
        if feature is None:
            raise ValueError(f"合格行情缺少 V2 历史特征: {market.instrument_id}")
        context += (StrategyDecisionContext(market=market, features=feature),)
    return context


def decision_to_proposal(proposal_id: str, decision: StrategyDecision) -> TradeProposal:
    return TradeProposal(
        proposal_id=proposal_id,
        instrument_id=decision.instrument_id,
        action=decision.action,
        current_quantity=decision.current_quantity,
        target_quantity=decision.target_quantity,
        delta_quantity=decision.delta_quantity,
        limit_price=decision.limit_price,
        status=ProposalStatus.GENERATED,
        confidence=decision.confidence,
        reason=decision.reason,
        strategy_version=decision.strategy_version,
        target_weight=decision.target_weight,
        reference_price=decision.reference_price,
        stop_price=decision.stop_price,
    )


def build_risk_profiles(
    instruments: tuple[Instrument, ...],
    evidence: tuple[QualifiedMarketEvidence, ...],
) -> tuple[RiskInstrument, ...]:
    profiles: tuple[RiskInstrument, ...] = ()
    for market in evidence:
        instrument = next(
            (item for item in instruments if item.instrument_id == market.instrument_id),
            None,
        )
        if instrument is None:
            raise ValueError("合格行情标的不在自选股")
        profiles += (
            RiskInstrument(
                instrument=instrument,
                fx_to_cny=market.fx_to_cny,
                estimated_fee_rate=Decimal("0.005"),
            ),
        )
    return profiles


def apply_risk_status(proposal: TradeProposal, approved: bool) -> TradeProposal:
    if proposal.action is TradeAction.HOLD:
        return rebuild_proposal(proposal, proposal.proposal_id, ProposalStatus.HOLD)
    status = ProposalStatus.RISK_APPROVED if approved else ProposalStatus.RISK_REJECTED
    return rebuild_proposal(proposal, proposal.proposal_id, status)


def rebuild_proposal(
    proposal: TradeProposal,
    proposal_id: str,
    status: ProposalStatus,
) -> TradeProposal:
    return TradeProposal(
        proposal_id=proposal_id,
        instrument_id=proposal.instrument_id,
        action=proposal.action,
        current_quantity=proposal.current_quantity,
        target_quantity=proposal.target_quantity,
        delta_quantity=proposal.delta_quantity,
        limit_price=proposal.limit_price,
        status=status,
        confidence=proposal.confidence,
        reason=proposal.reason,
        strategy_version=proposal.strategy_version,
        target_weight=proposal.target_weight,
        reference_price=proposal.reference_price,
        stop_price=proposal.stop_price,
    )


def proposal_to_order(plan: TradePlan, proposal: TradeProposal) -> Order:
    if proposal.limit_price is None:
        raise ValueError("交易提案缺少限价")
    side = OrderSide.BUY if proposal.action is TradeAction.BUY else OrderSide.SELL
    return Order(
        order_id=f"order:{plan.trade_date.isoformat()}:{proposal.instrument_id}",
        account_id=plan.account_id,
        instrument_id=proposal.instrument_id,
        trade_date=plan.trade_date,
        side=side,
        quantity=abs(proposal.delta_quantity),
        limit_price=proposal.limit_price,
        status=OrderStatus.PENDING_OPEN,
    )
