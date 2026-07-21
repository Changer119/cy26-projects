from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ai_trading.domain import (
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


class Base(DeclarativeBase):
    pass


class AccountRow(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    base_currency: Mapped[Currency] = mapped_column(SqlEnum(Currency, native_enum=False))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )


class CashBalanceRow(Base):
    __tablename__ = "cash_balances"
    __table_args__ = (
        CheckConstraint("available_micros >= 0", name="ck_cash_available_nonnegative"),
        CheckConstraint("reserved_micros >= 0", name="ck_cash_reserved_nonnegative"),
    )

    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    currency: Mapped[Currency] = mapped_column(
        SqlEnum(Currency, native_enum=False), primary_key=True
    )
    available_micros: Mapped[int] = mapped_column(Integer)
    reserved_micros: Mapped[int] = mapped_column(Integer)


class InstrumentRow(Base):
    __tablename__ = "instruments"
    __table_args__ = (
        CheckConstraint("lot_size IS NULL OR lot_size > 0", name="ck_instrument_lot_positive"),
        CheckConstraint(
            "is_tradable = 0 OR lot_size IS NOT NULL",
            name="ck_tradable_instrument_has_lot",
        ),
    )

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    market: Mapped[Market] = mapped_column(SqlEnum(Market, native_enum=False))
    currency: Mapped[Currency] = mapped_column(SqlEnum(Currency, native_enum=False))
    instrument_type: Mapped[InstrumentType] = mapped_column(
        SqlEnum(InstrumentType, native_enum=False)
    )
    industry: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lot_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_tradable: Mapped[bool] = mapped_column(Boolean)


class WatchlistEntryRow(Base):
    __tablename__ = "watchlist_entries"

    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    instrument_id: Mapped[str] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )


class PositionRow(Base):
    __tablename__ = "positions"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_position_quantity_nonnegative"),
        CheckConstraint("average_cost_micros >= 0", name="ck_position_cost_nonnegative"),
    )

    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    instrument_id: Mapped[str] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), primary_key=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    average_cost_micros: Mapped[int] = mapped_column(Integer)


class TradePlanRow(Base):
    __tablename__ = "trade_plans"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    trade_date: Mapped[date] = mapped_column(Date)
    decision_asof: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[TradePlanStatus] = mapped_column(SqlEnum(TradePlanStatus, native_enum=False))


class TradeProposalRow(Base):
    __tablename__ = "trade_proposals"
    __table_args__ = (
        UniqueConstraint("trade_plan_id", "instrument_id", name="uq_proposal_plan_instrument"),
        CheckConstraint("current_quantity >= 0", name="ck_proposal_current_nonnegative"),
        CheckConstraint("target_quantity >= 0", name="ck_proposal_target_nonnegative"),
        CheckConstraint(
            "limit_price_micros IS NULL OR limit_price_micros > 0",
            name="ck_proposal_limit_positive",
        ),
        CheckConstraint(
            "confidence_micros BETWEEN 0 AND 1000000",
            name="ck_proposal_confidence_range",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    trade_plan_id: Mapped[str] = mapped_column(ForeignKey("trade_plans.id", ondelete="CASCADE"))
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"))
    action: Mapped[TradeAction] = mapped_column(SqlEnum(TradeAction, native_enum=False))
    current_quantity: Mapped[int] = mapped_column(Integer)
    target_quantity: Mapped[int] = mapped_column(Integer)
    delta_quantity: Mapped[int] = mapped_column(Integer)
    limit_price_micros: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[ProposalStatus] = mapped_column(SqlEnum(ProposalStatus, native_enum=False))
    confidence_micros: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategy_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_weight_micros: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference_price_micros: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stop_price_micros: Mapped[int | None] = mapped_column(Integer, nullable=True)


class OrderRow(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "trade_date",
            "instrument_id",
            name="uq_order_account_date_instrument",
        ),
        CheckConstraint("quantity > 0", name="ck_order_quantity_positive"),
        CheckConstraint("limit_price_micros > 0", name="ck_order_limit_positive"),
        CheckConstraint("reserved_cash_micros >= 0", name="ck_order_reserve_nonnegative"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"))
    trade_date: Mapped[date] = mapped_column(Date)
    side: Mapped[OrderSide] = mapped_column(SqlEnum(OrderSide, native_enum=False))
    quantity: Mapped[int] = mapped_column(Integer)
    limit_price_micros: Mapped[int] = mapped_column(Integer)
    reserved_cash_micros: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[OrderStatus] = mapped_column(SqlEnum(OrderStatus, native_enum=False))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )


class NotificationOutboxRow(Base):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        UniqueConstraint(
            "event_type",
            "aggregate_id",
            "recipient_id",
            name="uq_notification_idempotency",
        ),
        CheckConstraint("attempts >= 0", name="ck_notification_attempts_nonnegative"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64))
    aggregate_id: Mapped[str] = mapped_column(String(128))
    recipient_id: Mapped[str] = mapped_column(String(128))
    markdown: Mapped[str] = mapped_column(Text)
    status: Mapped[NotificationStatus] = mapped_column(
        SqlEnum(NotificationStatus, native_enum=False)
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )
