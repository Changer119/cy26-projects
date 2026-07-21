from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """只包含运行所需的强类型配置，秘密字段始终保持遮蔽。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AI_TRADING_",
        extra="forbid",
        validate_assignment=True,
    )

    project_root: Path = Field(default_factory=Path.cwd, exclude=True)
    database_url_override: str | None = Field(
        default=None,
        validation_alias="AI_TRADING_DATABASE_URL",
    )
    timezone: str = "Asia/Shanghai"
    log_level: str = "INFO"
    initial_cash_cny_micros: int = 100_000_000_000
    paper_trading_only: Literal[True] = True
    deepseek_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="DEEPSEEK_API_KEY",
    )
    tiingo_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="TIINGO_API_KEY",
    )
    feishu_target_type: Literal["user", "chat"] = Field(
        default="user",
        validation_alias="FEISHU_TARGET_TYPE",
    )
    feishu_target_id: SecretStr | None = Field(
        default=None,
        validation_alias="FEISHU_TARGET_ID",
    )

    @property
    def database_url(self) -> str:
        if self.database_url_override is not None:
            return self.database_url_override
        database_path = self.project_root / "data" / "ai_trading.db"
        return f"sqlite:///{database_path}"
