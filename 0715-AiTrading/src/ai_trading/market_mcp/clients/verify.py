"""核验配置、原生客户端连接及真实取数；输出前遮蔽本地令牌。"""

import asyncio
import re
from datetime import date
from pathlib import Path

import httpx2
import typer
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from pydantic import BaseModel

from ai_trading.config import Settings
from ai_trading.logging_config import configure_logging
from ai_trading.market_mcp.auth import local_token
from ai_trading.market_mcp.clients.codex_probe import probe_codex
from ai_trading.market_mcp.clients.configure import read_configuration, targets
from ai_trading.market_mcp.models import DailyResult
from ai_trading.market_mcp.probe import DailyArguments


class NativeCheck(BaseModel):
    agent: str
    returncode: int
    summary: str


async def _native(name: str, command: tuple[str, ...], token: str) -> NativeCheck:
    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout=60)
    except TimeoutError:
        process.kill()
        await process.wait()
        return NativeCheck(agent=name, returncode=1, summary="原生命令超时")
    text = output.decode(errors="replace").replace(token, "[已隐藏]")
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    if name == "Codex":
        summary = "原生配置读取成功" if process.returncode == 0 else "原生配置读取失败"
    else:
        selected = tuple(
            line.strip()
            for line in text.splitlines()
            if any(
                word in line.lower()
                for word in ("local-market", "connect", "tool", "failed", "error")
            )
        )
        summary = " | ".join(selected)[-1800:]
    return NativeCheck(agent=name, returncode=process.returncode or 0, summary=summary)


async def main_async() -> None:
    settings = Settings()
    key = local_token(settings.project_root, settings.mcp_port)
    token = key.get_secret_value()
    for target in targets(settings.project_root, Path.home()):
        read_configuration(Path(target.path).read_text(encoding="utf-8"), target.format)
    commands = (
        ("Codex", ("codex", "mcp", "get", "local-market", "--json")),
        ("Claude Code", ("claude", "mcp", "get", "local-market")),
        ("Hermes", ("hermes", "mcp", "test", "local-market")),
        ("OpenCode", ("opencode", "mcp", "list")),
    )
    results = await asyncio.gather(*(_native(name, command, token) for name, command in commands))
    for result in results:
        typer.echo(result.model_dump_json())
    try:
        tools = await asyncio.to_thread(probe_codex)
        typer.echo("Codex app-server 发现工具：" + ", ".join(tools))
    except Exception as exc:
        typer.echo(f"Codex app-server 状态未确认：{type(exc).__name__}")
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=120, trust_env=False
    ) as http:
        endpoint = f"http://127.0.0.1:{settings.mcp_port}/mcp"
        transport = streamable_http_client(endpoint, http_client=http)
        async with Client(transport, mode="legacy") as client:
            names = tuple(tool.name for tool in (await client.list_tools()).tools)
            typer.echo("HTTP legacy 协议工具发现：" + ", ".join(names))
            arguments = DailyArguments(symbol="600584.SH", trade_date=date(2026, 10, 28))
            response = await client.call_tool("get_daily_bar", arguments.model_dump(mode="json"))
            if response.is_error:
                typer.echo("实际日线暂不可用；MCP 连接与工具发现已通过")
            else:
                typer.echo(
                    DailyResult.model_validate(response.structured_content).model_dump_json()
                )


def main() -> None:
    settings = Settings()
    configure_logging(settings.project_root / "logs" / "market-mcp", settings.log_level)
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
