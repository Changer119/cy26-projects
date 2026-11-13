from datetime import date
from decimal import Decimal

import pytest
from mcp import Client
from pydantic import BaseModel, SecretStr
from starlette.testclient import TestClient

from ai_trading.integrations.market_data import MarketBar, MarketDataRangeRequest, MarketDataRequest
from ai_trading.market_mcp.server import create_http_app, create_server
from ai_trading.market_mcp.service import MarketService


class RequestArguments(BaseModel):
    symbol: str = "600584.SH"
    trade_date: date = date(2026, 10, 28)


class Provider:
    def fetch(self, request: MarketDataRequest) -> MarketBar:
        return MarketBar(
            symbol=request.symbol,
            trade_date=request.trade_date,
            open=Decimal("10.12"),
            high=Decimal(11),
            low=Decimal(9),
            close=Decimal("10.15"),
            volume=10000,
            currency="CNY",
            source="akshare",
        )

    def fetch_range(self, request: MarketDataRangeRequest) -> tuple[MarketBar, ...]:
        return ()


def service() -> MarketService:
    return MarketService((("akshare", Provider()),))


@pytest.mark.asyncio
async def test_mcp_exposes_tools_and_structured_prices() -> None:
    async with Client(create_server(service()), raise_exceptions=True) as client:
        tools = await client.list_tools()
        assert {tool.name for tool in tools.tools} == {
            "get_daily_bar",
            "get_daily_history",
            "check_data_sources",
        }
        result = await client.call_tool("get_daily_bar", RequestArguments().model_dump(mode="json"))
        assert not result.is_error
        assert result.structured_content is not None
        assert result.structured_content["bar"]["close"] == "10.15"


@pytest.mark.asyncio
async def test_mcp_bad_input_is_tool_error() -> None:
    async with Client(create_server(service())) as client:
        result = await client.call_tool(
            "get_daily_bar", RequestArguments(symbol="01810.HK").model_dump(mode="json")
        )
        assert result.is_error
        assert "沪深" in str(result.content)


def test_http_requires_auth_and_rejects_bad_origin() -> None:
    app = create_http_app(service(), SecretStr("local-secret"))
    with TestClient(app, base_url="http://127.0.0.1:8766") as client:
        assert client.get("/health").status_code == 200
        assert client.post("/mcp").status_code == 401
        response = client.post(
            "/mcp",
            headers={
                "Authorization": "Bearer local-secret",
                "Origin": "https://evil.example",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            content='{"jsonrpc":"2.0","id":1,"method":"tools/list"}',
        )
        assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_real_http_client_fails_over_and_reuses_cache(mode: str) -> None:
    import asyncio
    import socket
    import threading

    import httpx2
    import uvicorn
    from mcp.client.streamable_http import streamable_http_client

    class FailingProvider(Provider):
        def fetch(self, request: MarketDataRequest) -> MarketBar:
            raise TimeoutError("never expose this")

    market = MarketService((("primary", FailingProvider()), ("secondary", Provider())))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        app = create_http_app(market, SecretStr("local-secret"), port)
        server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="on"))
        worker = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        worker.start()
        try:
            for _ in range(300):
                if server.started:
                    break
                await asyncio.sleep(0.01)
            assert server.started
            async with httpx2.AsyncClient(
                headers={"Authorization": "Bearer local-secret"}, trust_env=False, timeout=10
            ) as http:
                transport = streamable_http_client(f"http://127.0.0.1:{port}/mcp", http_client=http)
                async with Client(transport, mode=mode) as client:
                    assert len((await client.list_tools()).tools) == 3
                    arguments = RequestArguments().model_dump(mode="json")
                    first = await client.call_tool("get_daily_bar", arguments)
                    second = await client.call_tool("get_daily_bar", arguments)
                    assert not first.is_error
                    assert first.structured_content["cached"] is False
                    assert second.structured_content["cached"] is True
                    assert "never expose this" not in str(first)
        finally:
            server.should_exit = True
            worker.join(timeout=5)
            assert not worker.is_alive()
