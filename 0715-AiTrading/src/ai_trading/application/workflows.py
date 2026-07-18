from datetime import date, datetime
from decimal import Decimal

from ai_trading.application.models import (
    QualifiedMarketEvidence,
    RuntimeStatus,
    WorkflowReport,
    WorkflowStatus,
)
from ai_trading.application.planning import (
    apply_risk_status,
    basic_workflow_report,
    build_decision_context,
    build_risk_profiles,
    decision_to_proposal,
    premarket_timing_rejection,
    proposal_to_order,
)
from ai_trading.application.ports import (
    EvidenceLoader,
    PostmarketProcessor,
    ProposalSource,
    ProposalUnavailable,
)
from ai_trading.application.store import ApplicationStore
from ai_trading.domain import (
    Instrument,
    ProposalStatus,
    TradeAction,
    TradePlan,
    TradePlanStatus,
    TradeProposal,
)
from ai_trading.storage import DEFAULT_ACCOUNT_ID
from ai_trading.strategy_v2.engine import build_decisions
from ai_trading.strategy_v2.models import StrategyDecision
from ai_trading.trading.risk import RiskPolicy, evaluate_trade_plan


class TradingApplication:
    """所有外部提案都必须经过本地 schema、数据门和组合风控。"""

    def __init__(
        self,
        store: ApplicationStore,
        evidence_loader: EvidenceLoader,
        proposal_source: ProposalSource,
        postmarket_processor: PostmarketProcessor | None = None,
    ) -> None:
        self._store = store
        self._evidence_loader = evidence_loader
        self._proposal_source = proposal_source
        self._postmarket_processor = postmarket_processor

    def initialize(self) -> RuntimeStatus:
        return self._store.initialize()

    def status(self) -> RuntimeStatus:
        return self._store.status()

    def premarket(self, trade_date: date, decision_asof: datetime) -> WorkflowReport:
        plan_id = f"premarket:{trade_date.isoformat()}"
        if not self._store.status().initialized:
            return basic_workflow_report(
                "premarket", trade_date, WorkflowStatus.HOLD, "NOT_INITIALIZED"
            )
        if self._store.has_plan(plan_id):
            return WorkflowReport(
                command="premarket",
                status=WorkflowStatus.ALREADY_COMPLETED,
                trade_date=trade_date,
                plan_id=plan_id,
                reason="PLAN_ALREADY_FROZEN",
            )

        instruments = self._store.watchlist()
        timing_reason = premarket_timing_rejection(trade_date, decision_asof)
        if timing_reason == "DECISION_TIMEZONE_MISSING":
            return basic_workflow_report(
                "premarket", trade_date, WorkflowStatus.HOLD, timing_reason
            )
        if timing_reason is not None:
            return self._save_hold_plan(
                plan_id,
                trade_date,
                decision_asof,
                instruments,
                timing_reason,
            )
        batch = self._evidence_loader.load(trade_date)
        if batch.trade_date != trade_date:
            return self._save_hold_plan(
                plan_id,
                trade_date,
                decision_asof,
                instruments,
                "EVIDENCE_DATE_MISMATCH",
            )
        if not batch.qualified:
            return self._save_hold_plan(
                plan_id,
                trade_date,
                decision_asof,
                instruments,
                batch.reason,
            )

        try:
            context = build_decision_context(batch.qualified, batch.strategy_features)
            try:
                signals = self._proposal_source.propose(context)
            except ProposalUnavailable:
                signals = ()
            snapshot = self._store.portfolio_snapshot(batch.qualified)
            decisions = build_decisions(
                signals,
                instruments,
                batch.strategy_features,
                snapshot,
            )
            normalized = self._normalize_proposals(
                plan_id,
                instruments,
                batch.qualified,
                decisions,
            )
        except ValueError:
            return self._save_hold_plan(
                plan_id,
                trade_date,
                decision_asof,
                instruments,
                "PROPOSAL_OR_PORTFOLIO_DATA_INVALID",
            )

        draft = TradePlan(
            plan_id=plan_id,
            account_id=DEFAULT_ACCOUNT_ID,
            trade_date=trade_date,
            decision_asof=decision_asof,
            status=TradePlanStatus.DRAFT,
            proposals=normalized,
        )
        profiles = build_risk_profiles(instruments, batch.qualified)
        assessment = evaluate_trade_plan(draft, snapshot, profiles, RiskPolicy())
        if not assessment.approved:
            rejected = tuple(apply_risk_status(item, False) for item in normalized)
            plan = TradePlan(
                plan_id=draft.plan_id,
                account_id=draft.account_id,
                trade_date=draft.trade_date,
                decision_asof=draft.decision_asof,
                status=TradePlanStatus.RISK_CHECKED,
                proposals=rejected,
            )
            self._store.save_plan(plan)
            codes = ",".join(code.value for code in assessment.codes)
            return WorkflowReport(
                command="premarket",
                status=WorkflowStatus.HOLD,
                trade_date=trade_date,
                plan_id=plan_id,
                proposals_count=len(rejected),
                reason=f"RISK_REJECTED:{codes}",
            )

        approved = tuple(apply_risk_status(item, True) for item in normalized)
        plan = TradePlan(
            plan_id=draft.plan_id,
            account_id=draft.account_id,
            trade_date=draft.trade_date,
            decision_asof=draft.decision_asof,
            status=TradePlanStatus.FROZEN,
            proposals=approved,
        )
        orders = tuple(
            proposal_to_order(plan, item)
            for item in approved
            if item.action is not TradeAction.HOLD
        )
        self._store.freeze_plan(plan, orders)
        if not orders:
            return WorkflowReport(
                command="premarket",
                status=WorkflowStatus.HOLD,
                trade_date=trade_date,
                plan_id=plan_id,
                proposals_count=len(approved),
                reason=batch.reason,
            )
        return WorkflowReport(
            command="premarket",
            status=WorkflowStatus.COMPLETED,
            trade_date=trade_date,
            plan_id=plan_id,
            proposals_count=len(approved),
            orders_created=len(orders),
            reason="PAPER_ORDERS_FROZEN",
        )

    def postmarket(self, trade_date: date) -> WorkflowReport:
        if not self._store.status().initialized:
            return basic_workflow_report(
                "postmarket", trade_date, WorkflowStatus.HOLD, "NOT_INITIALIZED"
            )
        if self._postmarket_processor is not None:
            return self._postmarket_processor.run(trade_date)
        self._store.mark_pending_orders_data_unavailable(trade_date)
        return basic_workflow_report(
            "postmarket",
            trade_date,
            WorkflowStatus.HOLD,
            "QUALIFIED_EXECUTION_EVIDENCE_UNAVAILABLE",
        )

    def backtest(self, start: date, end: date) -> WorkflowReport:
        if start > end:
            raise ValueError("回测开始日期不得晚于结束日期")
        return WorkflowReport(
            command="backtest",
            status=WorkflowStatus.NO_DATA,
            trade_date=start,
            end_date=end,
            reason="HISTORICAL_EVIDENCE_UNAVAILABLE",
        )

    def _save_hold_plan(
        self,
        plan_id: str,
        trade_date: date,
        decision_asof: datetime,
        instruments: tuple[Instrument, ...],
        reason: str,
    ) -> WorkflowReport:
        proposals = tuple(self._hold(plan_id, item) for item in instruments)
        self._store.save_plan(
            TradePlan(
                plan_id=plan_id,
                account_id=DEFAULT_ACCOUNT_ID,
                trade_date=trade_date,
                decision_asof=decision_asof,
                status=TradePlanStatus.FROZEN,
                proposals=proposals,
            )
        )
        return WorkflowReport(
            command="premarket",
            status=WorkflowStatus.HOLD,
            trade_date=trade_date,
            plan_id=plan_id,
            proposals_count=len(proposals),
            reason=reason,
        )

    def _normalize_proposals(
        self,
        plan_id: str,
        instruments: tuple[Instrument, ...],
        evidence: tuple[QualifiedMarketEvidence, ...],
        proposed: tuple[StrategyDecision, ...],
    ) -> tuple[TradeProposal, ...]:
        proposed_ids = tuple(item.instrument_id for item in proposed)
        if len(proposed_ids) != len(set(proposed_ids)):
            raise ValueError("AI 返回重复标的")
        if any(item not in tuple(x.instrument_id for x in evidence) for item in proposed_ids):
            raise ValueError("AI 返回数据门之外的标的")
        result: tuple[TradeProposal, ...] = ()
        for instrument in instruments:
            candidate = next(
                (item for item in proposed if item.instrument_id == instrument.instrument_id),
                None,
            )
            if candidate is None:
                result += (self._hold(plan_id, instrument),)
                continue
            current = self._store.quantity(instrument.instrument_id)
            if candidate.current_quantity != current:
                raise ValueError("AI 使用了过期持仓")
            normalized_id = f"{plan_id}:{instrument.instrument_id}"
            result += (decision_to_proposal(normalized_id, candidate),)
        return result

    def _hold(self, plan_id: str, instrument: Instrument) -> TradeProposal:
        current = self._store.quantity(instrument.instrument_id)
        return TradeProposal(
            proposal_id=f"{plan_id}:{instrument.instrument_id}",
            instrument_id=instrument.instrument_id,
            action=TradeAction.HOLD,
            current_quantity=current,
            target_quantity=current,
            delta_quantity=0,
            limit_price=None,
            status=ProposalStatus.HOLD,
            confidence=Decimal(0),
        )
