from pathlib import Path

from pytest import MonkeyPatch

from ai_trading.config import Settings


def test_settings_use_safe_local_defaults(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, project_root=tmp_path)

    assert settings.timezone == "Asia/Shanghai"
    assert settings.database_url == f"sqlite:///{tmp_path}/data/ai_trading.db"
    assert settings.initial_cash_cny_micros == 100_000_000_000
    assert settings.paper_trading_only is True


def test_settings_read_secrets_without_exposing_them(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-secret")
    monkeypatch.setenv("TIINGO_API_KEY", "tiingo-secret")

    settings = Settings(_env_file=None, project_root=tmp_path)

    assert settings.deepseek_api_key is not None
    assert settings.deepseek_api_key.get_secret_value() == "deepseek-secret"
    assert settings.tiingo_api_key is not None
    assert settings.tiingo_api_key.get_secret_value() == "tiingo-secret"
    assert "deepseek-secret" not in repr(settings)
    assert "tiingo-secret" not in repr(settings)


def test_settings_accept_feishu_runtime_environment(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("FEISHU_TARGET_TYPE", "chat")
    monkeypatch.setenv("FEISHU_TARGET_ID", "oc_test_target")

    settings = Settings(_env_file=None, project_root=tmp_path)

    assert settings.feishu_target_type == "chat"
    assert settings.feishu_target_id is not None
    assert settings.feishu_target_id.get_secret_value() == "oc_test_target"
    assert "oc_test_target" not in repr(settings)
