"""统一日志：带文件输出，日志写入项目 logs/ 目录。"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parents[3] / "logs"


def get_logger(name: str) -> logging.Logger:
    """返回带文件 + 控制台输出的 logger（同名只初始化一次）。"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        _LOG_DIR / "weather.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    console_handler = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    for handler in (file_handler, console_handler):
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    return logger
