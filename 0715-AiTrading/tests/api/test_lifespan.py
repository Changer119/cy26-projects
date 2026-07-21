from pathlib import Path

import pytest

from ai_trading.api.app import create_app
from ai_trading.application.store import ApplicationStore
from ai_trading.config import Settings


@pytest.mark.asyncio
async def test_production_lifespan_initializes_portfolio_and_scheduler(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, project_root=tmp_path)
    settings.database_url_override = f"sqlite+pysqlite:///{tmp_path / 'lifespan.db'}"
    app = create_app(settings, enable_scheduler=True)

    async with app.router.lifespan_context(app):
        status = ApplicationStore(settings.database_url).status()
        scheduler = app.state.scheduler
        assert status.initialized is True
        assert scheduler.running is True

    assert scheduler.running is False
