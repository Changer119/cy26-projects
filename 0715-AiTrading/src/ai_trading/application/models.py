from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_trading.domain import InstrumentId, ProposalStatus, TradeAction
from ai_trading.strategy_v2.models import StrategyFeatures


class ApplicationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class RuntimeStatus(ApplicationModel):
    initialized: bool
    account_id: str | None = None
    paper_trading_only: Literal[True] = True
    broker_connected: Literal[False] = False
    cash_cny_micros: int = Field(default=0, ge=0)
    watchlist_count: int = Field(default=0, ge=0)
    position_count: int = Field(default=0, ge=0)
    order_count: int = Field(default=0, ge=0)


class WorkflowStatus(StrEnum):
    COMPLETED = "COMPLETED"
    ALREADY_COMPLETED = "ALREADY_COMPLETED"
    HOLD = "HOLD"
    NO_DATA = "NO_DATA"


class WorkflowReport(ApplicationModel):
    command: Literal["premarket", "postmarket", "backtest"]
    status: WorkflowStatus
    trade_date: date
    end_date: date | None = None
    plan_id: str | None = None
    proposals_count: int = Field(default=0, ge=0)
    orders_created: int = Field(default=0, ge=0)
    fills_recorded: int = Field(default=0, ge=0)
    nav_cny: Decimal | None = Field(default=None, ge=Decimal(0))
    daily_pnl_cny: Decimal | None = None
    total_pnl_cny: Decimal | None = None
    drawdown: Decimal | None = Field(default=None, ge=Decimal(0), le=Decimal(1))
    reason: str = Field(min_length=1)
    paper_trading_only: Literal[True] = True
    broker_connected: Literal[False] = False


class PlanDecisionSummary(ApplicationModel):
    instrument_id: InstrumentId
    action: TradeAction
    current_quantity: int = Field(ge=0)
    target_quantity: int = Field(ge=0)
    delta_quantity: int
    limit_price: Decimal | None = Field(default=None, gt=Decimal(0))
    status: ProposalStatus
    confidence: Decimal = Field(ge=Decimal(0), le=Decimal(1))
    reason: str = Field(default="历史计划未记录理由", min_length=2)
    strategy_version: str = Field(default="LEGACY_V1", min_length=2)
    target_weight: Decimal | None = Field(default=None, ge=Decimal(0), le=Decimal(1))
    reference_price: Decimal | None = Field(default=None, gt=Decimal(0))
    stop_price: Decimal | None = Field(default=None, gt=Decimal(0))


class QualifiedMarketEvidence(ApplicationModel):
    instrument_id: InstrumentId
    open: Decimal = Field(gt=Decimal(0))
    high: Decimal = Field(gt=Decimal(0))
    low: Decimal = Field(gt=Decimal(0))
    close: Decimal = Field(gt=Decimal(0))
    volume: int = Field(ge=0)
    fx_to_cny: Decimal = Field(gt=Decimal(0))
    current_quantity: int = Field(default=0, ge=0)
    evidence_date: date | None = None

    @model_validator(mode="after")
    def validate_ohlc(self) -> Self:
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("最高价低于其他 OHLC 价格")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("最低价高于其他 OHLC 价格")
        return self


class StrategyDecisionContext(ApplicationModel):
    market: QualifiedMarketEvidence
    features: StrategyFeatures

    @model_validator(mode="after")
    def validate_consistency(self) -> Self:
        if self.market.instrument_id != self.features.instrument_id:
            raise ValueError("实时行情与 V2 历史特征标的不一致")
        if self.market.evidence_date is None:
            raise ValueError("行情证据日期不能为空")
        if self.features.as_of != self.market.evidence_date:
            raise ValueError("历史特征日期与行情证据日期不一致")
        return self


class EvidenceBatch(ApplicationModel):
    trade_date: date
    qualified: tuple[QualifiedMarketEvidence, ...]
    strategy_features: tuple[StrategyFeatures, ...] = ()
    unavailable_instrument_ids: tuple[InstrumentId, ...]
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_symbols(self) -> Self:
        qualified_ids = tuple(item.instrument_id for item in self.qualified)
        feature_ids = tuple(item.instrument_id for item in self.strategy_features)
        if len(qualified_ids) != len(set(qualified_ids)):
            raise ValueError("合格行情存在重复标的")
        if len(self.unavailable_instrument_ids) != len(set(self.unavailable_instrument_ids)):
            raise ValueError("不可用行情存在重复标的")
        if len(feature_ids) != len(set(feature_ids)):
            raise ValueError("V2 历史特征存在重复标的")
        if any(item not in qualified_ids for item in feature_ids):
            raise ValueError("V2 历史特征必须对应合格行情")
        if set(qualified_ids) & set(self.unavailable_instrument_ids):
            raise ValueError("同一标的不能同时合格和不可用")
        for feature in self.strategy_features:
            market = next(
                item for item in self.qualified if item.instrument_id == feature.instrument_id
            )
            StrategyDecisionContext(market=market, features=feature)
            if feature.as_of >= self.trade_date:
                raise ValueError("策略证据日期必须早于交易日")
        return self
