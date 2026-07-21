import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_HANDLER_NAME = "ai-trading-file"


def configure_logging(log_dir: Path, level: str) -> Path:
    """配置单一轮转文件处理器，并返回日志文件路径。"""

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "ai-trading.log"
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())

    for handler in tuple(root_logger.handlers):
        if handler.name == _HANDLER_NAME:
            root_logger.removeHandler(handler)
            handler.close()

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.name = _HANDLER_NAME
    file_handler.setLevel(level.upper())
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root_logger.addHandler(file_handler)
    return log_path
