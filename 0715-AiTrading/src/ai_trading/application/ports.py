from datetime import date
from typing import Protocol

from ai_trading.application.models import (
    EvidenceBatch,
    StrategyDecisionContext,
    WorkflowReport,
)
from ai_trading.strategy_v2.models import TradeSignal


class EvidenceLoader(Protocol):
    def load(self, trade_date: date) -> EvidenceBatch: ...


class ProposalSource(Protocol):
    def propose(
        self,
        context: tuple[StrategyDecisionContext, ...],
    ) -> tuple[TradeSignal, ...]: ...


class PostmarketProcessor(Protocol):
    def run(self, trade_date: date) -> WorkflowReport: ...


class ProposalUnavailable(RuntimeError):
    """AI 提案不可用；应用层必须转为 HOLD。"""
