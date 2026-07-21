from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import ROUND_UP, Decimal

from sqlalchemy import and_, func, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from ai_trading.application.models import (
    PlanDecisionSummary,
    QualifiedMarketEvidence,
    RuntimeStatus,
)
from ai_trading.domain import (
    Currency,
    Instrument,
    Order,
    OrderSide,
    OrderStatus,
    TradeAction,
    TradePlan,
    decimal_to_micros,
    micros_to_decimal,
)
from ai_trading.storage import (
    DEFAULT_ACCOUNT_ID,
    INITIAL_CASH_CNY_MICROS,
    AccountRow,
    CashBalanceRow,
    DailyValuationRow,
    InstrumentRow,
    OrderRow,
    PositionRow,
    TradePlanRow,
    TradeProposalRow,
    TradingRepository,
    WatchlistEntryRow,
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)
from ai_trading.storage.orderbook import FrozenOrder, OrderBatchRepository
from ai_trading.trading.risk import PortfolioPosition, PortfolioSnapshot


class ApplicationStore:
    def __init__(self, database_url: str) -> None:
        self._engine = create_sqlite_engine(database_url)
        self._session_factory = create_session_factory(self._engine)
        self._repository = TradingRepository(self._session_factory)
        self._orderbook = OrderBatchRepository(self._session_factory)

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self._session_factory() as session:
            yield session

    def initialize(self) -> RuntimeStatus:
        create_schema(self._engine)
        self._repository.initialize_default_portfolio()
        return self.status()

    @property
    def session_factory(self) -> sessionmaker[Session]:
        return self._session_factory

    def status(self) -> RuntimeStatus:
        if not inspect(self._engine).has_table(AccountRow.__tablename__):
            return RuntimeStatus(initialized=False)
        with self.session() as session:
            account = session.get(AccountRow, DEFAULT_ACCOUNT_ID)
            if account is None:
                return RuntimeStatus(initialized=False)
            cash = session.get(CashBalanceRow, (DEFAULT_ACCOUNT_ID, Currency.CNY))
            return RuntimeStatus(
                initialized=True,
                account_id=DEFAULT_ACCOUNT_ID,
                cash_cny_micros=0 if cash is None else cash.available_micros,
                watchlist_count=int(
                    session.scalar(select(func.count()).select_from(WatchlistEntryRow)) or 0
                ),
                position_count=int(
                    session.scalar(select(func.count()).select_from(PositionRow)) or 0
                ),
                order_count=int(session.scalar(select(func.count()).select_from(OrderRow)) or 0),
            )

    def watchlist(self) -> tuple[Instrument, ...]:
        with self.session() as session:
            rows = session.scalars(
                select(InstrumentRow)
                .join(
                    WatchlistEntryRow,
                    WatchlistEntryRow.instrument_id == InstrumentRow.id,
                )
                .where(WatchlistEntryRow.account_id == DEFAULT_ACCOUNT_ID)
                .order_by(InstrumentRow.id)
            ).all()
            return tuple(self._instrument(row) for row in rows)

    def quantity(self, instrument_id: str) -> int:
        with self.session() as session:
            row = session.get(PositionRow, (DEFAULT_ACCOUNT_ID, instrument_id))
            return 0 if row is None else row.quantity

    def has_plan(self, plan_id: str) -> bool:
        with self.session() as session:
            return session.get(TradePlanRow, plan_id) is not None

    def plan_decisions(self, plan_id: str) -> tuple[PlanDecisionSummary, ...]:
        with self.session() as session:
            rows = session.scalars(
                select(TradeProposalRow)
                .where(TradeProposalRow.trade_plan_id == plan_id)
                .order_by(TradeProposalRow.instrument_id)
            ).all()
            return tuple(
                PlanDecisionSummary(
                    instrument_id=row.instrument_id,
                    action=row.action,
                    current_quantity=row.current_quantity,
                    target_quantity=row.target_quantity,
                    delta_quantity=row.delta_quantity,
                    limit_price=(
                        None
                        if row.limit_price_micros is None
                        else micros_to_decimal(row.limit_price_micros)
                    ),
                    status=row.status,
                    confidence=micros_to_decimal(row.confidence_micros),
                    reason=row.reason or "历史计划未记录理由",
                    strategy_version=row.strategy_version or "LEGACY_V1",
                    target_weight=(
                        None
                        if row.target_weight_micros is None
                        else micros_to_decimal(row.target_weight_micros)
                    ),
                    reference_price=(
                        None
                        if row.reference_price_micros is None
                        else micros_to_decimal(row.reference_price_micros)
                    ),
                    stop_price=(
                        None
                        if row.stop_price_micros is None
                        else micros_to_decimal(row.stop_price_micros)
                    ),
                )
                for row in rows
            )

    def save_plan(self, plan: TradePlan) -> None:
        self._repository.save_trade_plan(plan)

    def create_order(self, order: Order) -> None:
        self._repository.create_order(order)

    def freeze_plan(self, plan: TradePlan, orders: tuple[Order, ...]) -> None:
        frozen = tuple(
            FrozenOrder(
                order=order,
                reserved_cash_micros=self._reservation(order),
            )
            for order in orders
        )
        self._orderbook.freeze(plan, frozen)

    def portfolio_snapshot(
        self,
        evidence: tuple[QualifiedMarketEvidence, ...],
    ) -> PortfolioSnapshot:
        with self.session() as session:
            cash = session.get(CashBalanceRow, (DEFAULT_ACCOUNT_ID, Currency.CNY))
            available = Decimal(0) if cash is None else Decimal(cash.available_micros) / 1_000_000
            rows = session.scalars(
                select(PositionRow).where(PositionRow.account_id == DEFAULT_ACCOUNT_ID)
            ).all()
            positions = tuple(self._portfolio_position(session, row, evidence) for row in rows)
            peak_micros = session.scalar(
                select(func.max(DailyValuationRow.nav_cny_micros)).where(
                    DailyValuationRow.account_id == DEFAULT_ACCOUNT_ID
                )
            )
        nav = available + sum((item.market_value_cny for item in positions), Decimal(0))
        initial_nav = Decimal(INITIAL_CASH_CNY_MICROS) / 1_000_000
        historical_peak = Decimal(peak_micros or 0) / 1_000_000
        return PortfolioSnapshot(
            cash_available_cny=available,
            nav_cny=nav,
            peak_nav_cny=max(initial_nav, historical_peak, nav),
            positions=positions,
        )

    def mark_pending_orders_data_unavailable(self, trade_date: date) -> None:
        with self.session() as session, session.begin():
            rows = tuple(
                session.scalars(
                    select(OrderRow).where(
                        OrderRow.account_id == DEFAULT_ACCOUNT_ID,
                        OrderRow.trade_date == trade_date,
                        OrderRow.status == OrderStatus.PENDING_OPEN,
                    )
                )
            )
            cash = session.get(CashBalanceRow, (DEFAULT_ACCOUNT_ID, Currency.CNY))
            for row in rows:
                if cash is not None and row.reserved_cash_micros > 0:
                    cash.reserved_micros -= row.reserved_cash_micros
                    cash.available_micros += row.reserved_cash_micros
                    row.reserved_cash_micros = 0
                row.status = OrderStatus.DATA_UNAVAILABLE

    @staticmethod
    def _reservation(order: Order) -> int:
        if order.side is OrderSide.SELL:
            return 0
        amount = order.limit_price * order.quantity * Decimal("1.005")
        rounded = amount.quantize(Decimal("0.000001"), rounding=ROUND_UP)
        return decimal_to_micros(rounded)

    @staticmethod
    def _instrument(row: InstrumentRow) -> Instrument:
        return Instrument(
            instrument_id=row.id,
            name=row.name,
            market=row.market,
            currency=row.currency,
            instrument_type=row.instrument_type,
            industry=row.industry,
            lot_size=row.lot_size,
            is_tradable=row.is_tradable,
        )

    def _portfolio_position(
        self,
        session: Session,
        row: PositionRow,
        evidence: tuple[QualifiedMarketEvidence, ...],
    ) -> PortfolioPosition:
        market = next((item for item in evidence if item.instrument_id == row.instrument_id), None)
        instrument_row = session.get(InstrumentRow, row.instrument_id)
        if market is None or instrument_row is None:
            raise ValueError(f"持仓缺少合格行情: {row.instrument_id}")
        return PortfolioPosition(
            instrument=self._instrument(instrument_row),
            quantity=row.quantity,
            sellable_quantity=row.quantity,
            mark_price=market.close,
            fx_to_cny=market.fx_to_cny,
            average_cost=micros_to_decimal(row.average_cost_micros),
            stop_price=self._active_stop_price(session, row),
        )

    @staticmethod
    def _active_stop_price(session: Session, row: PositionRow) -> Decimal | None:
        value = session.scalar(
            select(TradeProposalRow.stop_price_micros)
            .join(TradePlanRow, TradePlanRow.id == TradeProposalRow.trade_plan_id)
            .join(
                OrderRow,
                and_(
                    OrderRow.account_id == TradePlanRow.account_id,
                    OrderRow.trade_date == TradePlanRow.trade_date,
                    OrderRow.instrument_id == TradeProposalRow.instrument_id,
                ),
            )
            .where(
                TradeProposalRow.instrument_id == row.instrument_id,
                TradeProposalRow.action == TradeAction.BUY,
                TradeProposalRow.stop_price_micros.is_not(None),
                OrderRow.side == OrderSide.BUY,
                OrderRow.status == OrderStatus.FILLED,
            )
            .order_by(TradePlanRow.trade_date.desc())
            .limit(1)
        )
        return None if value is None else micros_to_decimal(value)
