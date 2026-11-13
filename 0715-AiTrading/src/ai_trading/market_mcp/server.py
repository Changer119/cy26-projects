"""独立的只读 Streamable HTTP MCP 服务。"""

from collections.abc import Callable
from datetime import date
from functools import partial

import anyio
import httpx
import uvicorn
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import SecretStr
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.types import ASGIApp

from ai_trading.config import Settings
from ai_trading.integrations.china.akshare import AkshareEodProvider
from ai_trading.integrations.china.tushare import TushareEodProvider
from ai_trading.integrations.market_data import MarketDataProviderError
from ai_trading.logging_config import configure_logging
from ai_trading.market_mcp.auth import LocalAuthentication, local_token
from ai_trading.market_mcp.models import DailyResult, HealthResult, HistoryResult, SourcesResult
from ai_trading.market_mcp.service import MarketService


async def _execute[T](operation: Callable[[], T]) -> T:
    try:
        return await anyio.to_thread.run_sync(operation)
    except (MarketDataProviderError, ValueError) as exc:
        raise ToolError(str(exc)) from None
    except Exception:
        raise ToolError("行情服务暂不可用，请查看本地 logs/market-mcp 日志") from None


def create_server(service: MarketService) -> MCPServer[None]:
    mcp: MCPServer[None] = MCPServer(
        "local-market",
        version="1.0.0",
        instructions="只读沪深 A 股日线。价格单位为元，成交量为股；不能用于实时盘口查询。",
    )
    annotations = ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=True
    )

    @mcp.tool(annotations=annotations)
    async def get_daily_bar(symbol: str, trade_date: date) -> DailyResult:
        """查询沪深 A 股指定交易日的不复权日线；代码示例 600584.SH。失败自动切换备用源。"""
        return await _execute(partial(service.daily, symbol, trade_date))

    @mcp.tool(annotations=annotations)
    async def get_daily_history(symbol: str, start_date: date, end_date: date) -> HistoryResult:
        """查询最多366天的连续日线，起止日期均包含；价格前复权至区间末日，成交量为实际股数。

        Tushare 备用需要 adj_factor 权限；缺少会话或复权因子时返回错误，不混用价格口径。
        """
        return await _execute(partial(service.history, symbol, start_date, end_date))

    @mcp.tool(annotations=annotations)
    async def check_data_sources(symbol: str, trade_date: date) -> SourcesResult:
        """分别真实探测两源指定日线，不使用缓存；配置成功不等于已取得行情。"""
        return await _execute(partial(service.check_sources, symbol, trade_date))

    return mcp


async def _health(request: Request) -> JSONResponse:
    return JSONResponse(HealthResult().model_dump())


def create_http_app(service: MarketService, key: SecretStr, port: int = 8766) -> ASGIApp:
    app = create_server(service).streamable_http_app(
        stateless_http=True,
        json_response=True,
        max_request_body_size=64 * 1024,
        transport_security=TransportSecuritySettings(
            allowed_hosts=[f"127.0.0.1:{port}", f"localhost:{port}"],
            allowed_origins=[f"http://127.0.0.1:{port}", f"http://localhost:{port}"],
        ),
    )
    app.routes.append(Route("/health", endpoint=_health, methods=["GET"]))
    return LocalAuthentication(app, key)


def main() -> None:
    settings = Settings()
    configure_logging(settings.project_root / "logs" / "market-mcp", settings.log_level)
    key = local_token(settings.project_root, settings.mcp_port)
    with httpx.Client(timeout=20) as client:
        service = MarketService(
            (
                ("akshare", AkshareEodProvider()),
                ("tushare", TushareEodProvider(settings.tushare_token, client)),
            )
        )
        uvicorn.run(
            create_http_app(service, key, settings.mcp_port),
            host="127.0.0.1",
            port=settings.mcp_port,
            access_log=False,
        )


if __name__ == "__main__":
    main()
