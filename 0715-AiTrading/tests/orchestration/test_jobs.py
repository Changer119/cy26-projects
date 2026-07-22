from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import SecretStr

from ai_trading.application.models import PlanDecisionSummary, WorkflowReport, WorkflowStatus
from ai_trading.config import Settings
from ai_trading.domain import ProposalStatus, TradeAction
from ai_trading.integrations.feishu import (
    DeliveryResult,
    DeliveryStatus,
    FeishuTarget,
    NotificationEvent,
    NotificationKind,
)
from ai_trading.orchestration.jobs import ScheduledJobs

NOW = datetime(2026, 7, 15, 7, 50, tzinfo=ZoneInfo("Asia/Shanghai"))


class WorkflowStub:
    def __init__(self) -> None:
        self.premarket_dates: tuple[date, ...] = ()
        self.postmarket_dates: tuple[date, ...] = ()

    def premarket(self, trade_date: date, decision_asof: datetime) -> WorkflowReport:
        assert decision_asof == NOW
        self.premarket_dates += (trade_date,)
        return WorkflowReport(
            command="premarket",
            status=WorkflowStatus.HOLD,
            trade_date=trade_date,
            plan_id=f"premarket:{trade_date.isoformat()}",
            reason="TIINGO_TOKEN_MISSING",
        )

    def postmarket(self, trade_date: date) -> WorkflowReport:
        self.postmarket_dates += (trade_date,)
        return WorkflowReport(
            command="postmarket",
            status=WorkflowStatus.COMPLETED,
            trade_date=trade_date,
            fills_recorded=1,
            nav_cny=Decimal("100001"),
            daily_pnl_cny=Decimal("1"),
            total_pnl_cny=Decimal("1"),
            drawdown=Decimal("0"),
            reason="PAPER_RECONCILED:NAV_CNY=100001",
        )


class PlanReaderStub:
    def plan_decisions(self, plan_id: str) -> tuple[PlanDecisionSummary, ...]:
        assert plan_id == "premarket:2026-07-15"
        return (
            PlanDecisionSummary(
                instrument_id="603005.SH",
                instrument_name="晶方科技",
                action=TradeAction.BUY,
                current_quantity=0,
                target_quantity=100,
                delta_quantity=100,
                limit_price=Decimal("20.20"),
                status=ProposalStatus.RISK_APPROVED,
                confidence=Decimal("0.8"),
            ),
        )


class DispatcherSpy:
    def __init__(self) -> None:
        self.events: tuple[NotificationEvent, ...] = ()
        self.targets: tuple[FeishuTarget, ...] = ()

    def deliver(self, event: NotificationEvent, target: FeishuTarget) -> DeliveryResult:
        self.events += (event,)
        self.targets += (target,)
        return DeliveryResult(
            status=DeliveryStatus.SENT,
            idempotency_key=f"test:{event.event_id}",
        )


def settings(tmp_path: Path, with_target: bool) -> Settings:
    result = Settings(_env_file=None, project_root=tmp_path)
    if with_target:
        result.feishu_target_id = SecretStr("ou_test_user")
    return result


def test_scheduled_jobs_send_daily_plan_and_postmarket_report(tmp_path: Path) -> None:
    workflow = WorkflowStub()
    dispatcher = DispatcherSpy()
    jobs = ScheduledJobs(
        workflow,
        settings(tmp_path, True),
        dispatcher,
        lambda: NOW,
        PlanReaderStub(),
    )

    premarket = jobs.premarket()
    postmarket = jobs.postmarket()

    assert premarket.paper_trading_only is True
    assert postmarket.fills_recorded == 1
    assert workflow.premarket_dates == (NOW.date(),)
    assert workflow.postmarket_dates == (NOW.date(),)
    assert tuple(event.kind for event in dispatcher.events) == (
        NotificationKind.DAILY_PLAN,
        NotificationKind.POSTMARKET_REPORT,
    )
    assert all("仅模拟交易" in event.markdown for event in dispatcher.events)
    assert "603005.SH（晶方科技）：买入" in dispatcher.events[0].markdown
    assert "目标 100 股" in dispatcher.events[0].markdown
    assert "当日盈亏：+1.000000 元" in dispatcher.events[1].markdown


def test_missing_feishu_target_skips_external_delivery(tmp_path: Path) -> None:
    dispatcher = DispatcherSpy()
    jobs = ScheduledJobs(WorkflowStub(), settings(tmp_path, False), dispatcher, lambda: NOW)

    jobs.premarket()

    assert dispatcher.events == ()
