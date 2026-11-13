from datetime import date
from pathlib import Path

import pytest
from mcp import Client
from pytest import CaptureFixture, MonkeyPatch

from ai_trading.config import Settings
from ai_trading.integrations.market_data import MarketBar, MarketDataRangeRequest, MarketDataRequest
from ai_trading.market_mcp import probe
from ai_trading.market_mcp.server import create_server
from ai_trading.market_mcp.service import MarketService


@pytest.mark.asyncio
async def test_probe_reports_unavailable_without_raising_inside_client_context(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    class Unavailable:
        def fetch(self, request: MarketDataRequest) -> MarketBar:
            raise TimeoutError("private-token")

        def fetch_range(self, request: MarketDataRangeRequest) -> tuple[MarketBar, ...]:
            raise TimeoutError("private-token")

    server = create_server(MarketService((("akshare", Unavailable()),)))
    monkeypatch.setattr(probe, "Client", lambda _: Client(server))
    monkeypatch.setattr(probe, "Settings", lambda: Settings(_env_file=None, project_root=tmp_path))
    assert await probe.run_probe("600584.SH", date(2026, 10, 28), False, False) is False
    output = capsys.readouterr().out
    assert "单日日线调用失败" in output
    assert "private-token" not in output
    assert "Traceback" not in output
