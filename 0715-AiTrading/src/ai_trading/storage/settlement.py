"""模拟成交的单事务持久化与幂等重放。"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ai_trading.domain import (
    Currency,
    OrderSide,
    OrderStatus,
    decimal_to_micros,
)
from ai_trading.storage.ledger_tables import FillRow
from ai_trading.storage.tables import (
    CashBalanceRow,
    InstrumentRow,
    OrderRow,
    PositionRow,
)


class SettlementError(ValueError):
    pass


class SettlementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    fill_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    trade_date: date
    side: OrderSide
    quantity: int = Field(gt=0)
    price: Decimal = Field(gt=Decimal(0))
    fx_to_cny: Decimal = Field(gt=Decimal(0))
    fee_cny: Decimal = Field(ge=Decimal(0))
    fee_schedule_id: str = Field(min_length=1)

    @field_validator("price", "fx_to_cny", "fee_cny")
    @classmethod
    def validate_precision(cls, value: Decimal) -> Decimal:
        decimal_to_micros(value)
        return value


class SettlementOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    applied: bool
    cash_cny_micros: int = Field(ge=0)
    position_quantity: int = Field(ge=0)


class SettlementRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self._session_factory() as session:
            yield session

    def apply(self, request: SettlementRequest) -> SettlementOutcome:
        with self.session() as session, session.begin():
            order = session.get(OrderRow, request.order_id)
            if order is None:
                raise SettlementError("订单不存在")
            self._validate_order(order, request)
            existing_fill = session.scalar(
                select(FillRow).where(FillRow.order_id == request.order_id)
            )
            if existing_fill is not None:
                return self._outcome(session, request, applied=False)
            if order.status is not OrderStatus.PENDING_OPEN:
                raise SettlementError("订单不处于待成交状态")

            instrument = session.get(InstrumentRow, request.instrument_id)
            if instrument is None:
                raise SettlementError("证券主数据不存在")
            if instrument.currency is not Currency.CNY or request.fx_to_cny != Decimal(1):
                raise SettlementError("当前成交事务尚未激活港股原子换汇")
            cash = session.get(CashBalanceRow, (request.account_id, Currency.CNY))
            if cash is None:
                raise SettlementError("人民币现金子账本不存在")
            position = session.get(PositionRow, (request.account_id, request.instrument_id))
            notional_micros = decimal_to_micros(
                request.price * request.quantity * request.fx_to_cny
            )
            fee_micros = decimal_to_micros(request.fee_cny)

            if request.side is OrderSide.BUY:
                required = notional_micros + fee_micros
                if order.reserved_cash_micros > 0:
                    reserved = order.reserved_cash_micros
                    if reserved < required or cash.reserved_micros < reserved:
                        raise SettlementError("预留现金不足")
                    cash.reserved_micros -= reserved
                    cash.available_micros += reserved - required
                    order.reserved_cash_micros = 0
                else:
                    if cash.available_micros < required:
                        raise SettlementError("现金不足")
                    cash.available_micros -= required
                position = self._apply_buy(session, position, request)
            else:
                if position is None or position.quantity < request.quantity:
                    raise SettlementError("持仓不足")
                cash.available_micros += notional_micros - fee_micros
                self._apply_sell(session, position, request.quantity)

            order.status = OrderStatus.FILLED
            session.add(
                FillRow(
                    id=request.fill_id,
                    order_id=request.order_id,
                    account_id=request.account_id,
                    instrument_id=request.instrument_id,
                    trade_date=request.trade_date,
                    side=request.side,
                    quantity=request.quantity,
                    price_micros=decimal_to_micros(request.price),
                    fx_to_cny_micros=decimal_to_micros(request.fx_to_cny),
                    fee_cny_micros=fee_micros,
                    fee_schedule_id=request.fee_schedule_id,
                )
            )
            session.flush()
            return SettlementOutcome(
                applied=True,
                cash_cny_micros=cash.available_micros,
                position_quantity=0 if position is None else position.quantity,
            )

    @staticmethod
    def _validate_order(order: OrderRow, request: SettlementRequest) -> None:
        identity_matches = (
            order.account_id == request.account_id
            and order.instrument_id == request.instrument_id
            and order.trade_date == request.trade_date
            and order.side is request.side
            and order.quantity == request.quantity
        )
        within_limit = (
            request.price <= Decimal(order.limit_price_micros) / 1_000_000
            if request.side is OrderSide.BUY
            else request.price >= Decimal(order.limit_price_micros) / 1_000_000
        )
        if not identity_matches or not within_limit:
            raise SettlementError("成交与冻结订单不一致")

    @staticmethod
    def _apply_buy(
        session: Session,
        position: PositionRow | None,
        request: SettlementRequest,
    ) -> PositionRow:
        price_micros = decimal_to_micros(request.price)
        if position is None:
            position = PositionRow(
                account_id=request.account_id,
                instrument_id=request.instrument_id,
                quantity=request.quantity,
                average_cost_micros=price_micros,
            )
            session.add(position)
            return position
        new_quantity = position.quantity + request.quantity
        total_cost = (
            position.average_cost_micros * position.quantity + price_micros * request.quantity
        )
        position.average_cost_micros = int(
            (Decimal(total_cost) / new_quantity).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        )
        position.quantity = new_quantity
        return position

    @staticmethod
    def _apply_sell(session: Session, position: PositionRow, quantity: int) -> None:
        position.quantity -= quantity
        if position.quantity == 0:
            session.delete(position)

    @staticmethod
    def _outcome(
        session: Session,
        request: SettlementRequest,
        applied: bool,
    ) -> SettlementOutcome:
        cash = session.get(CashBalanceRow, (request.account_id, Currency.CNY))
        position = session.get(PositionRow, (request.account_id, request.instrument_id))
        return SettlementOutcome(
            applied=applied,
            cash_cny_micros=0 if cash is None else cash.available_micros,
            position_quantity=0 if position is None else position.quantity,
        )
