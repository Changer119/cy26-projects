from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, SecretStr


class LocalSecrets(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    deepseek_api_key: SecretStr
    tiingo_api_key: SecretStr
    tushare_token: SecretStr = SecretStr("")
    market_data_mode: Literal["akshare_tushare", "yahoo_tiingo"] = "akshare_tushare"
    feishu_target_type: Literal["user", "chat"]
    feishu_target_id: SecretStr


def write_local_secrets(destination: Path, secrets: LocalSecrets) -> None:
    """原子写入仅限本机读取的环境文件。"""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f"{destination.name}.tmp")
    content = (
        f"DEEPSEEK_API_KEY={secrets.deepseek_api_key.get_secret_value()}\n"
        f"TIINGO_API_KEY={secrets.tiingo_api_key.get_secret_value()}\n"
        f"TUSHARE_TOKEN={secrets.tushare_token.get_secret_value()}\n"
        f"AI_TRADING_MARKET_DATA_MODE={secrets.market_data_mode}\n"
        f"FEISHU_TARGET_TYPE={secrets.feishu_target_type}\n"
        f"FEISHU_TARGET_ID={secrets.feishu_target_id.get_secret_value()}\n"
    )
    temporary.write_text(content, encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(destination)
    destination.chmod(0o600)
