from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import inspect, select

from ai_trading.api.app import create_app
from ai_trading.api.schemas import (
    AccountResponse,
    DataHealthResponse,
    OrdersResponse,
    OverviewResponse,
    PerformanceResponse,
    PlansResponse,
    TradePlansResponse,
    WatchlistResponse,
)
from ai_trading.config import Settings
from ai_trading.domain import (
    OrderStatus,
    TradeAction,
    TradePlanStatus,
)
from ai_trading.storage import (
    DEFAULT_ACCOUNT_ID,
    MarketBarRow,
    create_session_factory,
    create_sqlite_engine,
)


@pytest.mark.asyncio
async def test_uninitialized_database_returns_explicit_empty_state(
    uninitialized_settings: Settings,
) -> None:
    app = create_app(uninitialized_settings)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        account_response = await client.get("/api/account")
        overview_response = await client.get("/api/overview")
        watchlist_response = await client.get("/api/watchlist")
        frontend_plans_response = await client.get("/api/plans")
        plans_response = await client.get("/api/trade-plans")
        orders_response = await client.get("/api/orders")
        performance_response = await client.get("/api/performance")
        data_health_response = await client.get("/api/data-health")

    account = AccountResponse.model_validate_json(account_response.content)
    overview = OverviewResponse.model_validate_json(overview_response.content)
    watchlist = WatchlistResponse.model_validate_json(watchlist_response.content)
    frontend_plans = PlansResponse.model_validate_json(frontend_plans_response.content)
    plans = TradePlansResponse.model_validate_json(plans_response.content)
    orders = OrdersResponse.model_validate_json(orders_response.content)
    performance = PerformanceResponse.model_validate_json(performance_response.content)
    data_health = DataHealthResponse.model_validate_json(data_health_response.content)

    assert overview.database_initialized is False
    assert overview.account_initialized is False
    assert overview.cash_balances == ()
    assert overview.position_count == 0
    assert overview.order_count == 0
    assert account.cash_micros == 0
    assert account.market_value_micros == 0
    assert account.nav_micros == 0
    assert account.pnl_micros == 0
    assert account.return_bps == 0
    assert watchlist.items == ()
    assert frontend_plans.items == ()
    assert plans.items == ()
    assert orders.items == ()
    assert performance.points == ()
    database_health = next(
        item for item in data_health.items if item.provider == "portfolio-database"
    )
    assert database_health.status == "unavailable"
    assert database_health.latency_ms is None
    assert database_health.last_success_at is None

    engine = create_sqlite_engine(uninitialized_settings.database_url)
    assert inspect(engine).get_table_names() == []


@pytest.mark.asyncio
async def test_overview_reports_real_account_counts(populated_settings: Settings) -> None:
    app = create_app(populated_settings)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/overview")
    overview = OverviewResponse.model_validate_json(response.content)

    assert response.status_code == 200
    assert overview.database_initialized is True
    assert overview.account_initialized is True
    assert overview.account_id == DEFAULT_ACCOUNT_ID
    assert overview.configured_initial_cash_cny_micros == 100_000_000_000
    assert tuple(item.available_micros for item in overview.cash_balances) == (
        100_000_000_000,
        0,
    )
    assert overview.position_count == 1
    assert overview.order_count == 1
    pending = next(
        item for item in overview.order_statuses if item.status is OrderStatus.PENDING_OPEN
    )
    assert pending.count == 1


@pytest.mark.asyncio
async def test_frontend_account_and_plans_contract_aliases(
    populated_settings: Settings,
) -> None:
    app = create_app(populated_settings)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        account_raw = await client.get("/api/account")
        plans_raw = await client.get("/api/plans")

    account = AccountResponse.model_validate_json(account_raw.content)
    plans = PlansResponse.model_validate_json(plans_raw.content)

    assert account_raw.status_code == 200
    assert account.initial_cash_micros == 100_000_000_000
    assert account.cash_micros == 72_000_000_000
    assert account.market_value_micros == 31_500_000_000
    assert account.nav_micros == 103_500_000_000
    assert account.pnl_micros == 3_500_000_000
    assert account.return_bps == 350
    assert account.max_drawdown_bps == 620
    assert plans_raw.status_code == 200
    assert plans.items[0].symbol == "603005.SH"
    assert plans.items[0].action is TradeAction.BUY
    assert plans.items[0].confidence_bps == 8200
    assert plans.items[0].target_weight_bps == 1500
    assert plans.items[0].reason == "中期趋势向上；本地按 ATR 与风险预算计算仓位"
    assert plans.items[0].status is TradePlanStatus.RISK_CHECKED


@pytest.mark.asyncio
async def test_watchlist_plans_and_orders_are_read_from_database(
    populated_settings: Settings,
) -> None:
    app = create_app(populated_settings)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        watchlist_raw = await client.get("/api/watchlist")
        plans_raw = await client.get("/api/trade-plans")
        orders_raw = await client.get("/api/orders")

    watchlist = WatchlistResponse.model_validate_json(watchlist_raw.content)
    plans = TradePlansResponse.model_validate_json(plans_raw.content)
    orders = OrdersResponse.model_validate_json(orders_raw.content)

    assert tuple(item.symbol for item in watchlist.items) == (
        "01810.HK",
        "02513.HK",
        "600584.SH",
        "603005.SH",
    )
    sh = next(item for item in watchlist.items if item.symbol == "603005.SH")
    assert sh.last_price_micros == 29_100_000
    assert sh.change_bps is None
    assert sh.decision is TradeAction.BUY
    assert sh.data_status == "healthy"
    assert sh.added_by == "USER"
    assert len(plans.items) == 1
    assert plans.items[0].proposals[0].confidence_micros == 820_000
    assert len(orders.items) == 1
    assert orders.items[0].limit_price_micros == 29_100_000
    assert orders.items[0].id == "order-603005"
    assert orders.items[0].symbol == "603005.SH"
    assert orders.items[0].reason == "订单理由未持久化"


@pytest.mark.asyncio
async def test_performance_and_data_health_do_not_invent_observations(
    populated_settings: Settings,
) -> None:
    populated_settings.tiingo_api_key = SecretStr("")
    app = create_app(populated_settings)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        performance_raw = await client.get("/api/performance")
        data_health_raw = await client.get("/api/data-health")

    performance = PerformanceResponse.model_validate_json(performance_raw.content)
    data_health = DataHealthResponse.model_validate_json(data_health_raw.content)

    assert len(performance.points) == 2
    assert performance.points[1].date == date(2026, 7, 15)
    assert performance.points[1].nav_micros == 103_500_000_000
    assert performance.points[1].return_bps == 350
    assert performance.points[1].drawdown_bps == 620
    database_health = next(
        item for item in data_health.items if item.provider == "portfolio-database"
    )
    yahoo_health = next(item for item in data_health.items if item.provider == "Yahoo Finance")
    assert database_health.status == "healthy"
    assert yahoo_health.status == "healthy"
    assert yahoo_health.latency_ms is None
    assert yahoo_health.last_success_at is not None
    tiingo_health = next(item for item in data_health.items if item.provider == "Tiingo")
    assert tiingo_health.message == "未配置 Tiingo，双源交易已停用"
    workflow_health = next(
        item for item in data_health.items if item.provider == "workflow:postmarket"
    )
    assert workflow_health.status == "healthy"
    assert workflow_health.message == "收盘结算完成"


@pytest.mark.asyncio
async def test_dual_source_valid_status_is_reported_as_healthy(
    populated_settings: Settings,
) -> None:
    engine = create_sqlite_engine(populated_settings.database_url)
    sessions = create_session_factory(engine)
    with sessions() as session, session.begin():
        bar = session.scalar(select(MarketBarRow))
        assert bar is not None
        bar.source = "dual_source_canonical"
        bar.quality_status = "VALID"
    app = create_app(populated_settings)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health_raw = await client.get("/api/data-health")
        watchlist_raw = await client.get("/api/watchlist")

    health = DataHealthResponse.model_validate_json(health_raw.content)
    watchlist = WatchlistResponse.model_validate_json(watchlist_raw.content)
    canonical = next(item for item in health.items if item.provider == "dual_source_canonical")
    security = next(item for item in watchlist.items if item.symbol == "603005.SH")
    assert canonical.status == "healthy"
    assert security.data_status == "healthy"
