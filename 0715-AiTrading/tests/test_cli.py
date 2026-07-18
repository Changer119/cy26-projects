import stat
from collections.abc import Mapping
from pathlib import Path

from typer.testing import CliRunner

from ai_trading.application.models import (
    EvidenceBatch,
    RuntimeStatus,
    WorkflowReport,
    WorkflowStatus,
)
from ai_trading.cli import app


def database_environment(tmp_path: Path) -> Mapping[str, str]:
    return {
        "AI_TRADING_DATABASE_URL": f"sqlite+pysqlite:///{tmp_path / 'cli.db'}",
        "DEEPSEEK_API_KEY": "",
        "TIINGO_API_KEY": "",
    }


def test_init_and_status_commands_return_validated_json(tmp_path: Path) -> None:
    runner = CliRunner()
    environment = database_environment(tmp_path)

    initialized = runner.invoke(app, ["init"], env=environment)
    status = runner.invoke(app, ["status"], env=environment)

    assert initialized.exit_code == 0
    assert status.exit_code == 0
    init_report = RuntimeStatus.model_validate_json(initialized.stdout)
    status_report = RuntimeStatus.model_validate_json(status.stdout)
    assert init_report.initialized is True
    assert status_report == init_report


def test_daily_commands_fail_closed_without_data_credentials(tmp_path: Path) -> None:
    runner = CliRunner()
    environment = database_environment(tmp_path)
    assert runner.invoke(app, ["init"], env=environment).exit_code == 0

    premarket = runner.invoke(app, ["premarket", "--date", "2026-07-15"], env=environment)
    postmarket = runner.invoke(app, ["postmarket", "--date", "2026-07-15"], env=environment)
    backtest = runner.invoke(
        app,
        ["backtest", "--start", "2026-07-01", "--end", "2026-07-15"],
        env=environment,
    )

    assert premarket.exit_code == 0
    assert postmarket.exit_code == 0
    assert backtest.exit_code == 0
    assert WorkflowReport.model_validate_json(premarket.stdout).status is WorkflowStatus.HOLD
    assert WorkflowReport.model_validate_json(postmarket.stdout).fills_recorded == 0
    assert WorkflowReport.model_validate_json(backtest.stdout).status is WorkflowStatus.NO_DATA


def test_data_smoke_is_read_only_and_reports_missing_sources(tmp_path: Path) -> None:
    runner = CliRunner()
    environment = database_environment(tmp_path)

    result = runner.invoke(
        app,
        ["data-smoke", "--date", "2026-07-15"],
        env=environment,
    )

    assert result.exit_code == 0
    report = EvidenceBatch.model_validate_json(result.stdout)
    assert report.qualified == ()
    assert set(report.unavailable_instrument_ids) == {
        "603005.SH",
        "600584.SH",
        "02513.HK",
        "01810.HK",
    }
    assert report.reason == "TIINGO_TOKEN_MISSING"


def test_strategy_smoke_validates_v2_history_without_creating_plan(tmp_path: Path) -> None:
    runner = CliRunner()
    environment = database_environment(tmp_path)

    result = runner.invoke(
        app,
        ["strategy-smoke", "--date", "2026-07-15"],
        env=environment,
    )

    assert result.exit_code == 0
    report = EvidenceBatch.model_validate_json(result.stdout)
    assert report.qualified == ()
    assert report.strategy_features == ()
    assert report.reason == "TIINGO_TOKEN_MISSING"


def test_cli_never_synthesizes_morning_time_to_backfill_old_order(tmp_path: Path) -> None:
    runner = CliRunner()
    environment = database_environment(tmp_path)
    assert runner.invoke(app, ["init"], env=environment).exit_code == 0

    result = runner.invoke(app, ["premarket", "--date", "2000-01-03"], env=environment)

    assert result.exit_code == 0
    report = WorkflowReport.model_validate_json(result.stdout)
    assert report.status is WorkflowStatus.HOLD
    assert report.reason == "DECISION_DATE_MISMATCH"
    assert report.orders_created == 0


def test_configure_from_env_writes_private_file_without_echoing_secrets(tmp_path: Path) -> None:
    destination = tmp_path / ".env"
    environment = {
        "DEEPSEEK_API_KEY": "deepseek-secret",
        "TIINGO_API_KEY": "",
        "FEISHU_TARGET_TYPE": "user",
        "FEISHU_TARGET_ID": "ou_target",
    }

    result = CliRunner().invoke(
        app,
        ["configure-from-env", "--destination", str(destination)],
        env=environment,
    )

    assert result.exit_code == 0
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert "deepseek-secret" not in result.stdout
    assert "DEEPSEEK_API_KEY=deepseek-secret" in destination.read_text(encoding="utf-8")
