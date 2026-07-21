from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from ai_trading.api.app import create_app
from ai_trading.api.schemas import HealthResponse
from ai_trading.config import Settings
from ai_trading.main import app


@pytest.mark.asyncio
async def test_health_confirms_paper_trading_mode(tmp_path: Path) -> None:
    app = create_app(Settings(_env_file=None, project_root=tmp_path))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
    health = HealthResponse.model_validate_json(response.content)

    assert response.status_code == 200
    assert health.status == "ok"
    assert health.paper_trading_only is True
    assert health.broker_connection is False


def test_main_exports_local_application() -> None:
    assert app.title == "AI 模拟交易系统"
