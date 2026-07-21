"""每日工作流与飞书通知的稳定调度入口。"""

import logging
from collections.abc import Callable
from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from ai_trading.application.models import PlanDecisionSummary, WorkflowReport
from ai_trading.application.store import ApplicationStore
from ai_trading.config import Settings
from ai_trading.domain import TradeAction
from ai_trading.integrations.feishu import (
    DeliveryResult,
    DeliveryStatus,
    FeishuOutboxDispatcher,
    FeishuTarget,
    NotificationEvent,
    NotificationKind,
)

logger = logging.getLogger(__name__)


class TradingWorkflow(Protocol):
    def premarket(self, trade_date: date, decision_asof: datetime) -> WorkflowReport: ...

    def postmarket(self, trade_date: date) -> WorkflowReport: ...


class NotificationDispatcher(Protocol):
    def deliver(
        self,
        event: NotificationEvent,
        target: FeishuTarget,
    ) -> DeliveryResult: ...


class PlanReader(Protocol):
    def plan_decisions(self, plan_id: str) -> tuple[PlanDecisionSummary, ...]: ...


class ScheduledJobs:
    def __init__(
        self,
        workflow: TradingWorkflow,
        settings: Settings,
        dispatcher: NotificationDispatcher | None = None,
        clock: Callable[[], datetime] | None = None,
        plan_reader: PlanReader | None = None,
    ) -> None:
        self._workflow = workflow
        self._settings = settings
        self._dispatcher = dispatcher or FeishuOutboxDispatcher()
        self._clock = clock or self._now
        self._plan_reader = plan_reader or ApplicationStore(settings.database_url)

    def premarket(self) -> WorkflowReport:
        now = self._clock()
        report = self._workflow.premarket(now.date(), now)
        self._notify(report, NotificationKind.DAILY_PLAN)
        return report

    def postmarket(self) -> WorkflowReport:
        now = self._clock()
        report = self._workflow.postmarket(now.date())
        self._notify(report, NotificationKind.POSTMARKET_REPORT)
        return report

    def _notify(self, report: WorkflowReport, kind: NotificationKind) -> None:
        target = self._target()
        if target is None:
            logger.warning("未配置飞书收件人，跳过 %s 通知", kind.value)
            return
        event = NotificationEvent(
            event_id=f"{kind.value}:{report.trade_date.isoformat()}",
            kind=kind,
            markdown=self._markdown(report, kind, self._decisions(report)),
        )
        result = self._dispatcher.deliver(event, target)
        if result.status is DeliveryStatus.FAILED:
            logger.error("飞书通知投递失败：%s", kind.value)

    def _decisions(self, report: WorkflowReport) -> tuple[PlanDecisionSummary, ...]:
        if report.plan_id is None:
            return ()
        return self._plan_reader.plan_decisions(report.plan_id)

    def _target(self) -> FeishuTarget | None:
        identifier = self._settings.feishu_target_id
        if identifier is None or not identifier.get_secret_value().strip():
            return None
        value = identifier.get_secret_value().strip()
        if self._settings.feishu_target_type == "chat":
            return FeishuTarget.chat(value)
        return FeishuTarget.user(value)

    @staticmethod
    def _markdown(
        report: WorkflowReport,
        kind: NotificationKind,
        decisions: tuple[PlanDecisionSummary, ...],
    ) -> str:
        title = "盘前交易计划" if kind is NotificationKind.DAILY_PLAN else "盘后收益复盘"
        lines: tuple[str, ...] = (
            f"## {title}",
            "**仅模拟交易 · 永不连接券商账户**",
            f"- 日期：{report.trade_date.isoformat()}",
            f"- 状态：{report.status.value}",
            f"- 提案：{report.proposals_count}",
            f"- 模拟订单：{report.orders_created}",
            f"- 模拟成交：{report.fills_recorded}",
            f"- 说明：{report.reason}",
        )
        if kind is NotificationKind.DAILY_PLAN and decisions:
            lines += (
                "### 逐标的计划",
                *(ScheduledJobs._decision_line(item) for item in decisions),
            )
        if kind is NotificationKind.POSTMARKET_REPORT and report.nav_cny is not None:
            lines += (
                f"- 账户净值：{report.nav_cny:.6f} 元",
                f"- 当日盈亏：{report.daily_pnl_cny or 0:+.6f} 元",
                f"- 累计盈亏：{report.total_pnl_cny or 0:+.6f} 元",
                f"- 当前回撤：{report.drawdown or 0:.2%}",
            )
        return "\n".join(lines)

    @staticmethod
    def _decision_line(item: PlanDecisionSummary) -> str:
        action = {
            TradeAction.BUY: "买入",
            TradeAction.SELL: "卖出",
            TradeAction.HOLD: "持有",
        }[item.action]
        limit = "无" if item.limit_price is None else f"{item.limit_price:.6f}"
        weight = "未知" if item.target_weight is None else f"{item.target_weight:.2%}"
        return (
            f"- {item.instrument_id}：{action}；当前 {item.current_quantity} 股 → "
            f"目标 {item.target_quantity} 股；目标权重 {weight}；限价 {limit}；"
            f"策略 {item.strategy_version}；状态 {item.status.value}；理由：{item.reason}"
        )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(ZoneInfo("Asia/Shanghai"))
