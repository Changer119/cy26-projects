from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_trading.domain import InstrumentId, TradeAction


class StrategyModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class HistoricalBar(StrategyModel):
    trade_date: date
    open: Decimal = Field(gt=Decimal(0))
    high: Decimal = Field(gt=Decimal(0))
    low: Decimal = Field(gt=Decimal(0))
    close: Decimal = Field(gt=Decimal(0))
    volume: int = Field(ge=0)
    available_at: datetime

    @model_validator(mode="after")
    def validate_bar(self) -> Self:
        if self.available_at.utcoffset() is None:
            raise ValueError("历史行情可用时间必须包含时区")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("历史行情最高价无效")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("历史行情最低价无效")
        return self


class StrategyFeatures(StrategyModel):
    instrument_id: InstrumentId
    as_of: date
    history_sessions: int = Field(ge=60)
    close: Decimal = Field(gt=Decimal(0))
    sma_20: Decimal = Field(gt=Decimal(0))
    sma_60: Decimal = Field(gt=Decimal(0))
    atr_20: Decimal = Field(gt=Decimal(0))
    average_volume_20: int = Field(ge=0)
    support_20: Decimal = Field(gt=Decimal(0))
    resistance_20: Decimal = Field(gt=Decimal(0))


class TradeSignal(StrategyModel):
    instrument_id: InstrumentId
    action: TradeAction
    confidence: Decimal = Field(ge=Decimal(0), le=Decimal(1))
    reason: str = Field(min_length=2, max_length=500)


class StrategyDecision(StrategyModel):
    instrument_id: InstrumentId
    action: TradeAction
    current_quantity: int = Field(ge=0)
    target_quantity: int = Field(ge=0)
    delta_quantity: int
    limit_price: Decimal | None = Field(default=None, gt=Decimal(0))
    stop_price: Decimal | None = Field(default=None, gt=Decimal(0))
    reference_price: Decimal = Field(gt=Decimal(0))
    confidence: Decimal = Field(ge=Decimal(0), le=Decimal(1))
    target_weight: Decimal = Field(ge=Decimal(0), le=Decimal(1))
    reason: str = Field(min_length=2, max_length=700)
    strategy_version: Literal["AGGRESSIVE_V2"] = "AGGRESSIVE_V2"

    @model_validator(mode="after")
    def validate_decision(self) -> Self:
        if self.delta_quantity != self.target_quantity - self.current_quantity:
            raise ValueError("决策数量差额无效")
        if self.action is TradeAction.HOLD and self.limit_price is not None:
            raise ValueError("HOLD 不得携带限价")
        if self.action is not TradeAction.HOLD and self.limit_price is None:
            raise ValueError("交易决策必须携带限价")
        return self


@dataclass(frozen=True, slots=True)
class StrategyPolicy:
    minimum_confidence: Decimal = Decimal("0.60")
    risk_per_trade: Decimal = Decimal("0.015")
    atr_entry_fraction: Decimal = Decimal("0.25")
    atr_stop_multiple: Decimal = Decimal("2")
    minimum_stop_fraction: Decimal = Decimal("0.08")
    maximum_entry_gap: Decimal = Decimal("0.02")
    cash_fee_buffer: Decimal = Decimal("0.005")
    liquidity_fraction: Decimal = Decimal("0.05")
    daily_new_risk_limit: Decimal = Decimal("0.50")
