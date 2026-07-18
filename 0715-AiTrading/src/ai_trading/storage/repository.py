from collections.abc import Iterator
from contextlib import contextmanager
from typing import cast
from uuid import uuid4

from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker

from ai_trading.domain import (
    Currency,
    Instrument,
    InstrumentType,
    Market,
    NotificationEvent,
    Order,
    TradePlan,
    decimal_to_micros,
)
from ai_trading.storage.tables import (
    AccountRow,
    CashBalanceRow,
    InstrumentRow,
    NotificationOutboxRow,
    OrderRow,
    TradePlanRow,
    TradeProposalRow,
    WatchlistEntryRow,
)

DEFAULT_ACCOUNT_ID = "paper-main"
INITIAL_CASH_CNY_MICROS = 100_000_000_000
INITIAL_INSTRUMENTS: tuple[Instrument, ...] = (
    Instrument(
        instrument_id="603005.SH",
        name="晶方科技",
        market=Market.SSE,
        currency=Currency.CNY,
        instrument_type=InstrumentType.STOCK,
        industry="半导体",
        lot_size=100,
        is_tradable=True,
    ),
    Instrument(
        instrument_id="600584.SH",
        name="长电科技",
        market=Market.SSE,
        currency=Currency.CNY,
        instrument_type=InstrumentType.STOCK,
        industry="半导体",
        lot_size=100,
        is_tradable=True,
    ),
    Instrument(
        instrument_id="02513.HK",
        name="智谱",
        market=Market.HKEX,
        currency=Currency.HKD,
        instrument_type=InstrumentType.STOCK,
        industry="人工智能",
        lot_size=None,
        is_tradable=False,
    ),
    Instrument(
        instrument_id="01810.HK",
        name="小米集团-W",
        market=Market.HKEX,
        currency=Currency.HKD,
        instrument_type=InstrumentType.STOCK,
        industry="消费电子",
        lot_size=None,
        is_tradable=False,
    ),
)


def add_trade_plan_rows(session: Session, plan: TradePlan) -> None:
    session.add(
        TradePlanRow(
            id=plan.plan_id,
            account_id=plan.account_id,
            trade_date=plan.trade_date,
            decision_asof=plan.decision_asof,
            status=plan.status,
        )
    )
    for proposal in plan.proposals:
        session.add(
            TradeProposalRow(
                id=proposal.proposal_id,
                trade_plan_id=plan.plan_id,
                instrument_id=proposal.instrument_id,
                action=proposal.action,
                current_quantity=proposal.current_quantity,
                target_quantity=proposal.target_quantity,
                delta_quantity=proposal.delta_quantity,
                limit_price_micros=(
                    decimal_to_micros(proposal.limit_price)
                    if proposal.limit_price is not None
                    else None
                ),
                status=proposal.status,
                confidence_micros=decimal_to_micros(proposal.confidence),
                reason=proposal.reason,
                strategy_version=proposal.strategy_version,
                target_weight_micros=(
                    None
                    if proposal.target_weight is None
                    else decimal_to_micros(proposal.target_weight)
                ),
                reference_price_micros=(
                    None
                    if proposal.reference_price is None
                    else decimal_to_micros(proposal.reference_price)
                ),
                stop_price_micros=(
                    None if proposal.stop_price is None else decimal_to_micros(proposal.stop_price)
                ),
            )
        )


def build_order_row(order: Order, reserved_cash_micros: int = 0) -> OrderRow:
    return OrderRow(
        id=order.order_id,
        account_id=order.account_id,
        instrument_id=order.instrument_id,
        trade_date=order.trade_date,
        side=order.side,
        quantity=order.quantity,
        limit_price_micros=decimal_to_micros(order.limit_price),
        reserved_cash_micros=reserved_cash_micros,
        status=order.status,
    )


class TradingRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self._session_factory() as session:
            yield session

    def initialize_default_portfolio(self) -> None:
        with self.session() as session, session.begin():
            if session.get(AccountRow, DEFAULT_ACCOUNT_ID) is None:
                session.add(AccountRow(id=DEFAULT_ACCOUNT_ID, base_currency=Currency.CNY))
            for currency, available in (
                (Currency.CNY, INITIAL_CASH_CNY_MICROS),
                (Currency.HKD, 0),
            ):
                if session.get(CashBalanceRow, (DEFAULT_ACCOUNT_ID, currency)) is None:
                    session.add(
                        CashBalanceRow(
                            account_id=DEFAULT_ACCOUNT_ID,
                            currency=currency,
                            available_micros=available,
                            reserved_micros=0,
                        )
                    )
            for instrument in INITIAL_INSTRUMENTS:
                if session.get(InstrumentRow, instrument.instrument_id) is None:
                    session.add(self._instrument_row(instrument))
                key = (DEFAULT_ACCOUNT_ID, instrument.instrument_id)
                if session.get(WatchlistEntryRow, key) is None:
                    session.add(
                        WatchlistEntryRow(
                            account_id=DEFAULT_ACCOUNT_ID,
                            instrument_id=instrument.instrument_id,
                        )
                    )

    def save_trade_plan(self, plan: TradePlan) -> None:
        with self.session() as session, session.begin():
            add_trade_plan_rows(session, plan)

    def create_order(self, order: Order) -> None:
        with self.session() as session, session.begin():
            session.add(build_order_row(order))

    def enqueue_notification(self, event: NotificationEvent) -> bool:
        statement = (
            sqlite_insert(NotificationOutboxRow)
            .values(
                id=str(uuid4()),
                event_type=event.event_type,
                aggregate_id=event.aggregate_id,
                recipient_id=event.recipient_id,
                markdown=event.markdown,
                status=event.status,
                attempts=0,
            )
            .on_conflict_do_nothing(index_elements=["event_type", "aggregate_id", "recipient_id"])
        )
        with self.session() as session, session.begin():
            inserted_id = cast(
                str | None,
                session.scalar(statement.returning(NotificationOutboxRow.id)),
            )
            return inserted_id is not None

    @staticmethod
    def _instrument_row(instrument: Instrument) -> InstrumentRow:
        return InstrumentRow(
            id=instrument.instrument_id,
            name=instrument.name,
            market=instrument.market,
            currency=instrument.currency,
            instrument_type=instrument.instrument_type,
            industry=instrument.industry,
            lot_size=instrument.lot_size,
            is_tradable=instrument.is_tradable,
        )
