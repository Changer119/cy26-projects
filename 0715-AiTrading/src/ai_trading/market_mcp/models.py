"""MCP 工具的稳定输入输出类型。"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ai_trading.integrations.market_data import MarketBar


class ResultModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class HealthResult(ResultModel):
    status: Literal["ok"] = "ok"
    service: Literal["local-market"] = "local-market"


class ErrorResult(ResultModel):
    error: str


class DailyResult(ResultModel):
    bar: MarketBar
    cached: bool
    fetched_at: datetime
    adjustment: Literal["none"] = "none"
    volume_unit: Literal["share"] = "share"


class HistoryResult(ResultModel):
    symbol: str
    start_date: date
    end_date: date
    bars: tuple[MarketBar, ...]
    cached: bool
    fetched_at: datetime
    adjustment: Literal["qfq_at_end"] = "qfq_at_end"
    volume_unit: Literal["share"] = "share"


class SourceState(ResultModel):
    source: str
    available: bool
    error_kind: str | None = None
    message: str


class SourcesResult(ResultModel):
    symbol: str
    trade_date: date
    checked_at: datetime
    sources: tuple[SourceState, ...]
