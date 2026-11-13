import stat
from pathlib import Path

from ai_trading.market_mcp.auth import ClientConfiguration, local_token


def test_credentials_survive_restart_and_client_configuration_is_private(tmp_path: Path) -> None:
    first = local_token(tmp_path)
    assert first == local_token(tmp_path)
    directory = tmp_path / "data" / "market-mcp"
    for name in ("access.token", "client.json"):
        assert stat.S_IMODE((directory / name).stat().st_mode) == 0o600
    config = ClientConfiguration.model_validate_json((directory / "client.json").read_bytes())
    assert config.servers["local-market"].url == "http://127.0.0.1:8766/mcp"
    assert config.servers["local-market"].headers.authorization == (
        f"Bearer {first.get_secret_value()}"
    )
