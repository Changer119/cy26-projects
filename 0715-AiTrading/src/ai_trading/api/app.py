import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ai_trading.api.queries import DashboardQueries
from ai_trading.api.schemas import (
    AccountResponse,
    DataHealthResponse,
    HealthResponse,
    OrdersResponse,
    OverviewResponse,
    PerformanceResponse,
    PlansResponse,
    TradePlansResponse,
    WatchlistResponse,
)
from ai_trading.application import build_application
from ai_trading.config import Settings
from ai_trading.orchestration.jobs import ScheduledJobs
from ai_trading.orchestration.scheduler import build_scheduler
from ai_trading.storage import create_session_factory, create_sqlite_engine


def create_app(
    settings: Settings | None = None,
    *,
    enable_scheduler: bool = False,
) -> FastAPI:
    runtime_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if not enable_scheduler:
            yield
            return
        trading = build_application(runtime_settings)
        trading.initialize()
        jobs = ScheduledJobs(trading, runtime_settings)
        scheduler = build_scheduler(jobs.premarket, jobs.postmarket)
        app.state.scheduler = scheduler
        scheduler.start()
        try:
            yield
        finally:
            scheduler.shutdown(wait=False)
            await asyncio.sleep(0)

    app = FastAPI(
        title="AI 模拟交易系统",
        version="0.1.0",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = runtime_settings
    engine = create_sqlite_engine(runtime_settings.database_url)
    queries = DashboardQueries(
        engine,
        create_session_factory(engine),
        runtime_settings,
    )

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/api/account", response_model=AccountResponse)
    def account() -> AccountResponse:
        return queries.account()

    @app.get("/api/overview", response_model=OverviewResponse, include_in_schema=False)
    def overview() -> OverviewResponse:
        return queries.overview()

    @app.get("/api/watchlist", response_model=WatchlistResponse)
    def watchlist() -> WatchlistResponse:
        return queries.watchlist()

    @app.get("/api/plans", response_model=PlansResponse)
    def plans() -> PlansResponse:
        return queries.plans()

    @app.get("/api/trade-plans", response_model=TradePlansResponse, include_in_schema=False)
    def trade_plans() -> TradePlansResponse:
        return queries.trade_plans()

    @app.get("/api/orders", response_model=OrdersResponse)
    def orders() -> OrdersResponse:
        return queries.orders()

    @app.get("/api/performance", response_model=PerformanceResponse)
    def performance() -> PerformanceResponse:
        return queries.performance()

    @app.get("/api/data-health", response_model=DataHealthResponse)
    def data_health() -> DataHealthResponse:
        return queries.data_health()

    dashboard = runtime_settings.project_root / "web" / "dist"
    if (dashboard / "index.html").is_file():
        app.mount("/", StaticFiles(directory=dashboard, html=True), name="dashboard")

    return app
