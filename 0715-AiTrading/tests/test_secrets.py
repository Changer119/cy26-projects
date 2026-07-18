import stat
from pathlib import Path

from pydantic import SecretStr

from ai_trading.secrets import LocalSecrets, write_local_secrets


def test_local_secret_file_is_private_and_ignored_by_runtime_logs(tmp_path: Path) -> None:
    destination = tmp_path / ".env"
    secrets = LocalSecrets(
        deepseek_api_key=SecretStr("deepseek-value"),
        tiingo_api_key=SecretStr("tiingo-value"),
        feishu_target_type="user",
        feishu_target_id=SecretStr("ou_target"),
    )

    write_local_secrets(destination, secrets)

    mode = stat.S_IMODE(destination.stat().st_mode)
    content = destination.read_text(encoding="utf-8")
    assert mode == 0o600
    assert "DEEPSEEK_API_KEY=deepseek-value" in content
    assert "TIINGO_API_KEY=tiingo-value" in content
    assert "FEISHU_TARGET_TYPE=user" in content
    assert "FEISHU_TARGET_ID=ou_target" in content
    assert "deepseek-value" not in repr(secrets)
    assert "tiingo-value" not in repr(secrets)
