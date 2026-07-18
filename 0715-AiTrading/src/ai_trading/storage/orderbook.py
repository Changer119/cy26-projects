"""交易计划、订单与现金预留的单事务冻结。"""

from collections.abc import Iterator
from contextlib import contextmanager

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session, sessionmaker

from ai_trading.domain import Currency, Order, OrderSide, TradePlan, TradePlanStatus
from ai_trading.storage.repository import add_trade_plan_rows, build_order_row
from ai_trading.storage.tables import CashBalanceRow


class FrozenOrder(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    order: Order
    reserved_cash_micros: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_reservation(self) -> "FrozenOrder":
        if self.order.side is OrderSide.BUY and self.reserved_cash_micros <= 0:
            raise ValueError("买单必须预留现金")
        if self.order.side is OrderSide.SELL and self.reserved_cash_micros != 0:
            raise ValueError("卖单不得预留买入现金")
        return self


class OrderBatchRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self._session_factory() as session:
            yield session

    def freeze(self, plan: TradePlan, orders: tuple[FrozenOrder, ...]) -> None:
        if plan.status is not TradePlanStatus.FROZEN:
            raise ValueError("只有已冻结计划可以创建订单")
        proposal_ids = tuple(item.instrument_id for item in plan.proposals)
        for item in orders:
            order = item.order
            if (
                order.account_id != plan.account_id
                or order.trade_date != plan.trade_date
                or order.instrument_id not in proposal_ids
            ):
                raise ValueError("订单与交易计划不一致")
        required = sum(item.reserved_cash_micros for item in orders)
        with self.session() as session, session.begin():
            cash = session.get(CashBalanceRow, (plan.account_id, Currency.CNY))
            if cash is None or cash.available_micros < required:
                raise ValueError("冻结订单时人民币现金不足")
            cash.available_micros -= required
            cash.reserved_micros += required
            add_trade_plan_rows(session, plan)
            session.add_all(
                tuple(build_order_row(item.order, item.reserved_cash_micros) for item in orders)
            )
