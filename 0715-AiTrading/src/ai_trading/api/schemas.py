from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ai_trading.domain import (
    Currency,
    Market,
    OrderSide,
    OrderStatus,
    ProposalStatus,
    TradeAction,
    TradePlanStatus,
)

HealthStatus = Literal["healthy", "degraded", "unavailable"]
AddedBy = Literal["USER", "AI"]


class ApiResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class HealthResponse(ApiResponse):
    status: Literal["ok"] = "ok"
    paper_trading_only: Literal[True] = True
    broker_connection: Literal[False] = False


class AccountResponse(ApiResponse):
    initial_cash_micros: int = Field(ge=0)
    cash_micros: int = Field(ge=0)
    market_value_micros: int = Field(ge=0)
    nav_micros: int = Field(ge=0)
    pnl_micros: int
    return_bps: int
    max_drawdown_bps: int = Field(ge=0)
    updated_at: datetime


class CashBalanceView(ApiResponse):
    currency: Currency
    available_micros: int = Field(ge=0)
    reserved_micros: int = Field(ge=0)


class OrderStatusCount(ApiResponse):
    status: OrderStatus
    count: int = Field(ge=0)


class OverviewResponse(ApiResponse):
    database_initialized: bool
    account_initialized: bool
    account_id: str | None
    base_currency: Currency | None
    configured_initial_cash_cny_micros: int = Field(ge=0)
    cash_balances: tuple[CashBalanceView, ...]
    position_count: int = Field(ge=0)
    order_count: int = Field(ge=0)
    order_statuses: tuple[OrderStatusCount, ...]


class WatchlistItem(ApiResponse):
    symbol: str
    name: str
    market: Market
    last_price_micros: int | None = Field(default=None, gt=0)
    change_bps: int | None
    decision: TradeAction
    data_status: HealthStatus
    added_by: AddedBy


class WatchlistResponse(ApiResponse):
    items: tuple[WatchlistItem, ...]


class TradeProposalView(ApiResponse):
    proposal_id: str
    instrument_id: str
    action: TradeAction
    current_quantity: int = Field(ge=0)
    target_quantity: int = Field(ge=0)
    delta_quantity: int
    limit_price_micros: int | None = Field(default=None, gt=0)
    status: ProposalStatus
    confidence_micros: int = Field(ge=0, le=1_000_000)


class TradePlanView(ApiResponse):
    plan_id: str
    trade_date: date
    decision_asof: datetime
    status: TradePlanStatus
    proposals: tuple[TradeProposalView, ...]


class TradePlansResponse(ApiResponse):
    database_initialized: bool
    account_initialized: bool
    items: tuple[TradePlanView, ...]


class PlanItem(ApiResponse):
    symbol: str
    action: TradeAction
    confidence_bps: int = Field(ge=0, le=10_000)
    target_weight_bps: int = Field(ge=0, le=10_000)
    reason: str = Field(min_length=1)
    status: TradePlanStatus


class PlansResponse(ApiResponse):
    items: tuple[PlanItem, ...]


class OrderView(ApiResponse):
    id: str
    symbol: str
    trade_date: date
    side: OrderSide
    quantity: int = Field(gt=0)
    limit_price_micros: int = Field(gt=0)
    status: OrderStatus
    reason: str = Field(min_length=1)


class OrdersResponse(ApiResponse):
    items: tuple[OrderView, ...]


class PerformancePoint(ApiResponse):
    date: date
    nav_micros: int = Field(ge=0)
    return_bps: int
    drawdown_bps: int = Field(ge=0)


class PerformanceResponse(ApiResponse):
    points: tuple[PerformancePoint, ...]


class DataHealthItem(ApiResponse):
    provider: str = Field(min_length=1)
    status: HealthStatus
    latency_ms: int | None = Field(default=None, ge=0)
    last_success_at: datetime | None
    message: str = Field(min_length=1)


class DataHealthResponse(ApiResponse):
    items: tuple[DataHealthItem, ...]
