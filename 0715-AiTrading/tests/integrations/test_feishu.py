from ai_trading.integrations.feishu import (
    CommandResult,
    DeliveryStatus,
    FeishuCommandBuilder,
    FeishuOutboxDispatcher,
    FeishuTarget,
    NotificationEvent,
    NotificationKind,
)


class RecordingRunner:
    def __init__(self, result: CommandResult) -> None:
        self.result = result
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: tuple[str, ...]) -> CommandResult:
        self.commands.append(command)
        return self.result


class FailingRunner:
    def run(self, command: tuple[str, ...]) -> CommandResult:
        raise OSError("lark-cli not found")


def make_event(event_id: str = "plan-20260715") -> NotificationEvent:
    return NotificationEvent(
        event_id=event_id,
        kind=NotificationKind.DAILY_PLAN,
        markdown="**盘前计划**\n不构成投资建议",
    )


def test_user_command_uses_only_lark_cli_and_single_argv_markdown() -> None:
    event = NotificationEvent(
        event_id="plan-1",
        kind=NotificationKind.DAILY_PLAN,
        markdown="$(touch /tmp/must-not-run)",
    )

    command = FeishuCommandBuilder().build(event, FeishuTarget.user("ou_recipient"))

    assert command.argv[:5] == ("lark-cli", "im", "+messages-send", "--as", "bot")
    assert command.argv[5:9] == (
        "--user-id",
        "ou_recipient",
        "--markdown",
        "$(touch /tmp/must-not-run)",
    )
    assert "--idempotency-key" in command.argv


def test_chat_target_uses_chat_id_flag() -> None:
    command = FeishuCommandBuilder().build(make_event(), FeishuTarget.chat("oc_group"))

    assert "--chat-id" in command.argv
    assert "oc_group" in command.argv
    assert "--user-id" not in command.argv


def test_idempotency_key_is_deterministic_and_event_specific() -> None:
    builder = FeishuCommandBuilder()
    target = FeishuTarget.user("ou_recipient")

    first = builder.build(make_event(), target)
    repeated = builder.build(make_event(), target)
    different = builder.build(make_event("plan-20260716"), target)

    assert first.idempotency_key == repeated.idempotency_key
    assert first.idempotency_key != different.idempotency_key


def test_outbox_dispatch_records_success_without_real_send() -> None:
    runner = RecordingRunner(CommandResult(exit_code=0))
    dispatcher = FeishuOutboxDispatcher(runner=runner)

    result = dispatcher.deliver(make_event(), FeishuTarget.user("ou_recipient"))

    assert result.status is DeliveryStatus.SENT
    assert len(runner.commands) == 1
    assert result.idempotency_key in runner.commands[0]


def test_nonzero_lark_cli_exit_keeps_event_failed_for_retry() -> None:
    runner = RecordingRunner(CommandResult(exit_code=2))
    dispatcher = FeishuOutboxDispatcher(runner=runner)

    result = dispatcher.deliver(make_event(), FeishuTarget.user("ou_recipient"))

    assert result.status is DeliveryStatus.FAILED
    assert result.detail == "lark-cli 退出码 2"


def test_runner_start_failure_is_returned_as_failed_for_retry() -> None:
    dispatcher = FeishuOutboxDispatcher(runner=FailingRunner())

    result = dispatcher.deliver(make_event(), FeishuTarget.user("ou_recipient"))

    assert result.status is DeliveryStatus.FAILED
    assert result.detail == "lark-cli 执行失败"
