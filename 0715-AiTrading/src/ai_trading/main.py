from ai_trading.api.app import create_app
from ai_trading.config import Settings
from ai_trading.logging_config import configure_logging

settings = Settings()
configure_logging(settings.project_root / "logs", settings.log_level)
app = create_app(settings, enable_scheduler=True)
