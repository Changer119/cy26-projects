"""成交、估值、行情与任务审计表。"""

from datetime import date, datetime

from sqlalchemy import (
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
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from ai_trading.domain import Currency, OrderSide
from ai_trading.storage.tables import Base


class FillRow(Base):
    __tablename__ = "fills"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_fill_order"),
        CheckConstraint("quantity > 0", name="ck_fill_quantity_positive"),
        CheckConstraint("price_micros > 0", name="ck_fill_price_positive"),
        CheckConstraint("fx_to_cny_micros > 0", name="ck_fill_fx_positive"),
        CheckConstraint("fee_cny_micros >= 0", name="ck_fill_fee_nonnegative"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"))
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"))
    trade_date: Mapped[date] = mapped_column(Date)
    side: Mapped[OrderSide] = mapped_column(SqlEnum(OrderSide, native_enum=False))
    quantity: Mapped[int] = mapped_column(Integer)
    price_micros: Mapped[int] = mapped_column(Integer)
    fx_to_cny_micros: Mapped[int] = mapped_column(Integer)
    fee_cny_micros: Mapped[int] = mapped_column(Integer)
    fee_schedule_id: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )


class DailyValuationRow(Base):
    __tablename__ = "daily_valuations"
    __table_args__ = (
        CheckConstraint("nav_cny_micros >= 0", name="ck_valuation_nav_nonnegative"),
        CheckConstraint("cash_cny_micros >= 0", name="ck_valuation_cash_nonnegative"),
        CheckConstraint("fees_cny_micros >= 0", name="ck_valuation_fees_nonnegative"),
        CheckConstraint(
            "drawdown_micros BETWEEN 0 AND 1000000",
            name="ck_valuation_drawdown_range",
        ),
    )

    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    nav_cny_micros: Mapped[int] = mapped_column(Integer)
    cash_cny_micros: Mapped[int] = mapped_column(Integer)
    realized_pnl_cny_micros: Mapped[int] = mapped_column(Integer)
    unrealized_pnl_cny_micros: Mapped[int] = mapped_column(Integer)
    fees_cny_micros: Mapped[int] = mapped_column(Integer)
    drawdown_micros: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )


class MarketBarRow(Base):
    __tablename__ = "market_bars"
    __table_args__ = (
        CheckConstraint("open_micros > 0", name="ck_market_bar_open_positive"),
        CheckConstraint("high_micros > 0", name="ck_market_bar_high_positive"),
        CheckConstraint("low_micros > 0", name="ck_market_bar_low_positive"),
        CheckConstraint("close_micros > 0", name="ck_market_bar_close_positive"),
        CheckConstraint("volume >= 0", name="ck_market_bar_volume_nonnegative"),
    )

    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), primary_key=True)
    currency: Mapped[Currency] = mapped_column(SqlEnum(Currency, native_enum=False))
    open_micros: Mapped[int] = mapped_column(Integer)
    high_micros: Mapped[int] = mapped_column(Integer)
    low_micros: Mapped[int] = mapped_column(Integer)
    close_micros: Mapped[int] = mapped_column(Integer)
    volume: Mapped[int] = mapped_column(Integer)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    quality_status: Mapped[str] = mapped_column(String(64))


class WorkflowRunRow(Base):
    __tablename__ = "workflow_runs"

    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    workflow: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


LEDGER_TABLES: tuple[type[Base], ...] = (
    FillRow,
    DailyValuationRow,
    MarketBarRow,
    WorkflowRunRow,
)
