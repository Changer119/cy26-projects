"""应用配置。

所有敏感/环境相关配置一律从环境变量读取，禁止硬编码。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """从 .env / 环境变量加载的运行时配置。"""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    app_host: str = "0.0.0.0"
    app_port: int = 8000

    rag_top_k: int = 3
    session_max_turns: int = 20  # 单个会话保留的最大消息轮数，防止内存无限增长

    data_dir: Path = BACKEND_ROOT / "data"
    log_dir: Path = BACKEND_ROOT / "logs"

    @property
    def deepseek_configured(self) -> bool:
        """是否已配置真实可用的 DeepSeek key（用于给出清晰报错而不是崩溃）。"""
        return bool(self.deepseek_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
