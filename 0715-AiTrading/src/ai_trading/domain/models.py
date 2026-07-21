from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ai_trading.domain.enums import (
    Currency,
    InstrumentType,
    Market,
    NotificationStatus,
    OrderSide,
    OrderStatus,
    ProposalStatus,
    TradeAction,
    TradePlanStatus,
)
from ai_trading.domain.money import decimal_to_micros

InstrumentId = Annotated[
    str,
    Field(pattern=r"^(?:\d{6}\.(?:SH|SZ)|\d{5}\.HK)$"),
]


class DomainModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
    )


class Instrument(DomainModel):
    instrument_id: InstrumentId
    name: str = Field(min_length=1)
    market: Market
    currency: Currency
    instrument_type: InstrumentType
    industry: str | None = Field(default=None, min_length=1)
    lot_size: int | None = Field(default=None, gt=0)
    is_tradable: bool

    @model_validator(mode="after")
    def validate_market_identity(self) -> Self:
        match self.market:
            case Market.SSE:
                suffix, currency = ".SH", Currency.CNY
            case Market.SZSE:
                suffix, currency = ".SZ", Currency.CNY
            case Market.HKEX:
                suffix, currency = ".HK", Currency.HKD
        if not self.instrument_id.endswith(suffix) or self.currency is not currency:
            raise ValueError("证券代码、市场与币种不一致")
        if self.is_tradable and self.lot_size is None:
            raise ValueError("可交易证券必须先核验整手数量")
        return self


class CashBalance(DomainModel):
    account_id: str = Field(min_length=1)
    currency: Currency
    available: Decimal = Field(ge=Decimal(0))
    reserved: Decimal = Field(ge=Decimal(0))

    @field_validator("available", "reserved")
    @classmethod
    def validate_precision(cls, value: Decimal) -> Decimal:
        decimal_to_micros(value)
        return value


class Position(DomainModel):
    account_id: str = Field(min_length=1)
    instrument_id: InstrumentId
    quantity: int = Field(ge=0)
    average_cost: Decimal = Field(ge=Decimal(0))

    @field_validator("average_cost")
    @classmethod
    def validate_precision(cls, value: Decimal) -> Decimal:
        decimal_to_micros(value)
        return value


class TradeProposal(DomainModel):
    proposal_id: str = Field(min_length=1)
    instrument_id: InstrumentId
    action: TradeAction
    current_quantity: int = Field(ge=0)
    target_quantity: int = Field(ge=0)
    delta_quantity: int
    limit_price: Decimal | None = Field(default=None, gt=Decimal(0))
    status: ProposalStatus
    confidence: Decimal = Field(ge=Decimal(0), le=Decimal(1))
    reason: str = Field(default="历史计划未记录理由", min_length=2, max_length=700)
    strategy_version: str = Field(default="LEGACY_V1", min_length=2, max_length=32)
    target_weight: Decimal | None = Field(default=None, ge=Decimal(0), le=Decimal(1))
    reference_price: Decimal | None = Field(default=None, gt=Decimal(0))
    stop_price: Decimal | None = Field(default=None, gt=Decimal(0))

    @field_validator("limit_price", "reference_price", "stop_price")
    @classmethod
    def validate_price_precision(cls, value: Decimal | None) -> Decimal | None:
        if value is not None:
            decimal_to_micros(value)
        return value

    @model_validator(mode="after")
    def validate_trade_intent(self) -> Self:
        if self.delta_quantity != self.target_quantity - self.current_quantity:
            raise ValueError("delta_quantity 必须等于目标数量减当前数量")
        if self.action is TradeAction.BUY and self.delta_quantity <= 0:
            raise ValueError("BUY 提案必须增加持仓")
        if self.action is TradeAction.SELL and self.delta_quantity >= 0:
            raise ValueError("SELL 提案必须减少持仓")
        if self.action is TradeAction.HOLD and self.delta_quantity != 0:
            raise ValueError("HOLD 提案不得改变持仓")
        if self.action is TradeAction.HOLD and self.limit_price is not None:
            raise ValueError("HOLD 提案不得携带限价")
        if self.action is not TradeAction.HOLD and self.limit_price is None:
            raise ValueError("交易提案必须携带正限价")
        if self.strategy_version == "AGGRESSIVE_V2" and self.reference_price is None:
            raise ValueError("V2 提案必须记录参考价格")
        return self


class TradePlan(DomainModel):
    plan_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    trade_date: date
    decision_asof: datetime
    status: TradePlanStatus
    proposals: tuple[TradeProposal, ...]

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        if self.decision_asof.utcoffset() is None:
            raise ValueError("decision_asof 必须包含时区")
        instrument_ids = tuple(item.instrument_id for item in self.proposals)
        if len(instrument_ids) != len(set(instrument_ids)):
            raise ValueError("同一标的在一个计划中只能出现一次")
        return self


class Order(DomainModel):
    order_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    instrument_id: InstrumentId
    trade_date: date
    side: OrderSide
    quantity: int = Field(gt=0)
    limit_price: Decimal = Field(gt=Decimal(0))
    status: OrderStatus

    @field_validator("limit_price")
    @classmethod
    def validate_price_precision(cls, value: Decimal) -> Decimal:
        decimal_to_micros(value)
        return value


class NotificationEvent(DomainModel):
    event_type: str = Field(min_length=1, max_length=64)
    aggregate_id: str = Field(min_length=1, max_length=128)
    recipient_id: str = Field(min_length=1, max_length=128)
    markdown: str = Field(min_length=1)
    status: NotificationStatus = NotificationStatus.PENDING
