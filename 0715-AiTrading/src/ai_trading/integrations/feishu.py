"""飞书 lark-cli 命令构造与 outbox 投递边界。"""

from __future__ import annotations

import hashlib
import subprocess
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class FeishuTargetKind(StrEnum):
    USER = "USER"
    CHAT = "CHAT"


class FeishuTarget(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    kind: FeishuTargetKind
    identifier: str = Field(min_length=1)

    @classmethod
    def user(cls, user_id: str) -> FeishuTarget:
        return cls(kind=FeishuTargetKind.USER, identifier=user_id)

    @classmethod
    def chat(cls, chat_id: str) -> FeishuTarget:
        return cls(kind=FeishuTargetKind.CHAT, identifier=chat_id)


class NotificationKind(StrEnum):
    DAILY_PLAN = "DAILY_PLAN"
    WATCHLIST_ADDED = "WATCHLIST_ADDED"
    POSTMARKET_REPORT = "POSTMARKET_REPORT"


class NotificationEvent(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    event_id: str = Field(min_length=1)
    kind: NotificationKind
    markdown: str = Field(min_length=1)


class FeishuCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    argv: tuple[str, ...]
    idempotency_key: str


class CommandResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    exit_code: int
    stdout: str = ""
    stderr: str = ""


class CommandRunner(Protocol):
    def run(self, command: tuple[str, ...]) -> CommandResult: ...


class SubprocessCommandRunner:
    """使用 argv 而非 shell 字符串执行, 防止 Markdown 被解释。"""

    def __init__(self, timeout_seconds: float = 30) -> None:
        self._timeout_seconds = timeout_seconds

    def run(self, command: tuple[str, ...]) -> CommandResult:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=self._timeout_seconds,
        )
        return CommandResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


class FeishuCommandBuilder:
    """只生成 lark-cli 的机器人消息命令。"""

    def build(self, event: NotificationEvent, target: FeishuTarget) -> FeishuCommand:
        key = self._idempotency_key(event, target)
        target_flag = "--user-id" if target.kind is FeishuTargetKind.USER else "--chat-id"
        return FeishuCommand(
            argv=(
                "lark-cli",
                "im",
                "+messages-send",
                "--as",
                "bot",
                target_flag,
                target.identifier,
                "--markdown",
                event.markdown,
                "--idempotency-key",
                key,
            ),
            idempotency_key=key,
        )

    @staticmethod
    def _idempotency_key(event: NotificationEvent, target: FeishuTarget) -> str:
        canonical = "\x1f".join(
            (event.kind.value, event.event_id, target.kind.value, target.identifier)
        ).encode()
        return f"ait-{hashlib.sha256(canonical).hexdigest()[:32]}"


class DeliveryStatus(StrEnum):
    SENT = "SENT"
    FAILED = "FAILED"


class DeliveryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: DeliveryStatus
    idempotency_key: str
    detail: str | None = None


class FeishuOutboxDispatcher:
    def __init__(
        self,
        runner: CommandRunner | None = None,
        builder: FeishuCommandBuilder | None = None,
    ) -> None:
        self._runner = runner or SubprocessCommandRunner()
        self._builder = builder or FeishuCommandBuilder()

    def deliver(self, event: NotificationEvent, target: FeishuTarget) -> DeliveryResult:
        command = self._builder.build(event, target)
        try:
            result = self._runner.run(command.argv)
        except (OSError, subprocess.SubprocessError):
            return DeliveryResult(
                status=DeliveryStatus.FAILED,
                idempotency_key=command.idempotency_key,
                detail="lark-cli 执行失败",
            )
        if result.exit_code == 0:
            return DeliveryResult(
                status=DeliveryStatus.SENT,
                idempotency_key=command.idempotency_key,
            )
        return DeliveryResult(
            status=DeliveryStatus.FAILED,
            idempotency_key=command.idempotency_key,
            detail=f"lark-cli 退出码 {result.exit_code}",
        )
