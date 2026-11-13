"""通过真实 HTTP 连接验收 MCP，不读取或修改任何模拟订单。"""

import asyncio
from datetime import date

import httpx2
import typer
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel

from ai_trading.config import Settings
from ai_trading.logging_config import configure_logging
from ai_trading.market_mcp.auth import local_token
from ai_trading.market_mcp.models import DailyResult, HistoryResult, SourcesResult

app = typer.Typer()


class DailyArguments(BaseModel):
    symbol: str
    trade_date: date


class HistoryArguments(BaseModel):
    symbol: str
    start_date: date
    end_date: date


async def run_probe(symbol: str, selected: date, history: bool, sources: bool) -> bool:
    settings = Settings()
    key = local_token(settings.project_root, settings.mcp_port)
    url = f"http://127.0.0.1:{settings.mcp_port}/mcp"
    async with (
        httpx2.AsyncClient(
            headers={"Authorization": f"Bearer {key.get_secret_value()}"},
            timeout=120,
            trust_env=False,
        ) as http,
        Client(streamable_http_client(url, http_client=http)) as client,
    ):
        tools = await client.list_tools()
        typer.echo("已发现工具：" + ", ".join(tool.name for tool in tools.tools))
        arguments = DailyArguments(symbol=symbol, trade_date=selected).model_dump(mode="json")
        if sources:
            result = await client.call_tool("check_data_sources", arguments)
            typer.echo(SourcesResult.model_validate(result.structured_content).model_dump_json())
        result = await client.call_tool("get_daily_bar", arguments)
        if result.is_error:
            typer.echo("单日日线调用失败：" + str(result.content))
            return False
        typer.echo(DailyResult.model_validate(result.structured_content).model_dump_json())
        repeated = await client.call_tool("get_daily_bar", arguments)
        cached = DailyResult.model_validate(repeated.structured_content)
        if not cached.cached:
            typer.echo("重复请求未命中服务端缓存")
            return False
        typer.echo("重复请求命中服务端缓存")
        if history:
            history_result = await client.call_tool(
                "get_daily_history",
                HistoryArguments(
                    symbol=symbol,
                    start_date=selected,
                    end_date=selected,
                ).model_dump(mode="json"),
            )
            if history_result.is_error:
                typer.echo("历史日线调用失败：" + str(history_result.content))
                return False
            typer.echo(
                HistoryResult.model_validate(history_result.structured_content).model_dump_json()
            )
    return True


@app.command()
def probe(
    symbol: str = "600584.SH",
    trade_date: str = "2026-10-28",
    history: bool = False,
    sources: bool = False,
) -> None:
    settings = Settings()
    configure_logging(settings.project_root / "logs" / "market-mcp", settings.log_level)
    if not asyncio.run(run_probe(symbol, date.fromisoformat(trade_date), history, sources)):
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
