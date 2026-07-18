from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from ai_trading.api.app import create_app
from ai_trading.config import Settings


@pytest.mark.asyncio
async def test_built_dashboard_is_served_from_backend_root(tmp_path: Path) -> None:
    distribution = tmp_path / "web" / "dist"
    distribution.mkdir(parents=True)
    (distribution / "index.html").write_text(
        "<html><body>AI Trading Dashboard</body></html>",
        encoding="utf-8",
    )
    settings = Settings(_env_file=None, project_root=tmp_path)
    app = create_app(settings)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "AI Trading Dashboard" in response.text
