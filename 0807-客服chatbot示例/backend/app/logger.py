"""统一日志配置：输出到 backend/logs/ 目录下的文件，同时保留控制台输出。"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from app.config import get_settings

_CONFIGURED = False


def setup_logging() -> None:
    """初始化根 logger。幂等，重复调用不会重复挂 handler。"""
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    log_file = settings.log_dir / "backend.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # jieba 自身的 DEBUG 日志会绕过 root 的级别过滤直接输出，单独降噪
    logging.getLogger("jieba").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
