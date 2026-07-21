from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ai_trading.api.schemas import (
    DataHealthItem,
    DataHealthResponse,
    HealthStatus,
    PerformancePoint,
    PerformanceResponse,
)
from ai_trading.config import Settings
from ai_trading.storage import DEFAULT_ACCOUNT_ID
from ai_trading.storage.ledger_tables import (
    DailyValuationRow,
    MarketBarRow,
    WorkflowRunRow,
)


def performance_response(
    session_factory: sessionmaker[Session],
    settings: Settings,
    database_initialized: bool,
) -> PerformanceResponse:
    if not database_initialized:
        return PerformanceResponse(points=())
    with session_factory() as session:
        rows = tuple(
            session.scalars(
                select(DailyValuationRow)
                .where(DailyValuationRow.account_id == DEFAULT_ACCOUNT_ID)
                .order_by(DailyValuationRow.trade_date)
            )
        )
    initial_cash = settings.initial_cash_cny_micros
    return PerformanceResponse(
        points=tuple(
            PerformancePoint(
                date=row.trade_date,
                nav_micros=row.nav_cny_micros,
                return_bps=(
                    (row.nav_cny_micros - initial_cash) * 10_000 // initial_cash
                    if initial_cash
                    else 0
                ),
                drawdown_bps=row.drawdown_micros // 100,
            )
            for row in rows
        )
    )


def data_health_response(
    session_factory: sessionmaker[Session],
    settings: Settings,
    database_initialized: bool,
    account_initialized: bool,
) -> DataHealthResponse:
    database_item = _database_health(database_initialized, account_initialized)
    if not database_initialized:
        return DataHealthResponse(
            items=(database_item, _unavailable_yahoo(), _tiingo_health(settings))
        )
    with session_factory() as session:
        bars = tuple(session.scalars(select(MarketBarRow)))
        runs = tuple(session.scalars(select(WorkflowRunRow)))
    market_items = _market_health(bars)
    if not market_items:
        market_items = (_unavailable_yahoo(),)
    if settings.tiingo_api_key is not None and not _has_tiingo(market_items):
        market_items += (_tiingo_health(settings),)
    return DataHealthResponse(items=(database_item, *market_items, *_workflow_health(runs)))


def _database_health(initialized: bool, account_initialized: bool) -> DataHealthItem:
    status: HealthStatus
    message: str
    if initialized and account_initialized:
        status = "healthy"
        message = "组合数据库与模拟账户可读"
    elif initialized:
        status = "degraded"
        message = "数据库结构已建立但模拟账户尚未初始化"
    else:
        status = "unavailable"
        message = "组合数据库尚未初始化"
    return DataHealthItem(
        provider="portfolio-database",
        status=status,
        latency_ms=None,
        last_success_at=None,
        message=message,
    )


def _market_health(rows: tuple[MarketBarRow, ...]) -> tuple[DataHealthItem, ...]:
    sources = tuple(sorted(set(row.source for row in rows)))
    return tuple(_market_source_health(source, rows) for source in sources)


def _market_source_health(
    source: str,
    rows: tuple[MarketBarRow, ...],
) -> DataHealthItem:
    source_rows = tuple(row for row in rows if row.source == source)
    latest = max(source_rows, key=lambda row: (row.trade_date, row.available_at))
    status = _quality_status(latest.quality_status)
    latest_trade_date = latest.trade_date.isoformat()
    quality = latest.quality_status or "unknown"
    return DataHealthItem(
        provider=_provider_name(source),
        status=status,
        latency_ms=None,
        last_success_at=latest.available_at,
        message=f"最近交易日 {latest_trade_date}; 质量 {quality}",
    )


def _workflow_health(rows: tuple[WorkflowRunRow, ...]) -> tuple[DataHealthItem, ...]:
    workflows = tuple(sorted(set(row.workflow for row in rows)))
    return tuple(_workflow_item(workflow, rows) for workflow in workflows)


def _workflow_item(
    workflow: str,
    rows: tuple[WorkflowRunRow, ...],
) -> DataHealthItem:
    workflow_rows = tuple(row for row in rows if row.workflow == workflow)
    latest = max(workflow_rows, key=lambda row: (row.trade_date, row.started_at))
    status = _workflow_status(latest.status)
    return DataHealthItem(
        provider=f"workflow:{workflow or 'unknown'}",
        status=status,
        latency_ms=None,
        last_success_at=latest.finished_at if status == "healthy" else None,
        message=latest.reason or f"工作流状态 {latest.status or 'unknown'}",
    )


def _quality_status(value: str) -> HealthStatus:
    normalized = value.strip().lower()
    if normalized in ("healthy", "ok", "good", "valid"):
        return "healthy"
    if normalized in ("unavailable", "missing", "failed"):
        return "unavailable"
    return "degraded"


def _workflow_status(value: str) -> HealthStatus:
    normalized = value.strip().upper()
    if normalized in ("COMPLETED", "SUCCESS", "SUCCEEDED"):
        return "healthy"
    if normalized in ("FAILED", "ABORTED", "ERROR"):
        return "unavailable"
    return "degraded"


def _provider_name(source: str) -> str:
    normalized = source.strip().lower()
    if "yahoo" in normalized:
        return "Yahoo Finance"
    if "tiingo" in normalized:
        return "Tiingo"
    return source.strip() or "unknown-market-data"


def _unavailable_yahoo() -> DataHealthItem:
    return DataHealthItem(
        provider="Yahoo Finance",
        status="unavailable",
        latency_ms=None,
        last_success_at=None,
        message="尚无持久化行情观测",
    )


def _tiingo_health(settings: Settings) -> DataHealthItem:
    token = settings.tiingo_api_key
    configured = token is not None and bool(token.get_secret_value().strip())
    message = "已配置但尚无持久化行情观测" if configured else "未配置 Tiingo，双源交易已停用"
    return DataHealthItem(
        provider="Tiingo",
        status="unavailable",
        latency_ms=None,
        last_success_at=None,
        message=message,
    )


def _has_tiingo(items: tuple[DataHealthItem, ...]) -> bool:
    return any(item.provider == "Tiingo" for item in items)
