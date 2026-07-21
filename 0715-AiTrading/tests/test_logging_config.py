import logging
from pathlib import Path

from ai_trading.logging_config import configure_logging


def test_configure_logging_writes_application_log(tmp_path: Path) -> None:
    log_path = configure_logging(tmp_path, "INFO")

    logging.getLogger("ai_trading.test").info("ledger-ready")
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert log_path == tmp_path / "ai-trading.log"
    assert "ledger-ready" in log_path.read_text(encoding="utf-8")


def test_configure_logging_is_idempotent(tmp_path: Path) -> None:
    configure_logging(tmp_path, "INFO")
    configure_logging(tmp_path, "INFO")

    managed_handlers = [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, "name", None) == "ai-trading-file"
    ]
    assert len(managed_handlers) == 1
