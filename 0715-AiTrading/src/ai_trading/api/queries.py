from sqlalchemy import Engine, inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ai_trading.api.account import account_snapshot
from ai_trading.api.metrics import data_health_response, performance_response
from ai_trading.api.schemas import (
    AccountResponse,
    CashBalanceView,
    DataHealthResponse,
    OrdersResponse,
    OrderStatusCount,
    OverviewResponse,
    PerformanceResponse,
    PlanItem,
    PlansResponse,
    TradePlansResponse,
    WatchlistResponse,
)
from ai_trading.api.views import order_view, trade_plan_view, watchlist_item
from ai_trading.config import Settings
from ai_trading.domain import OrderStatus
from ai_trading.storage import DEFAULT_ACCOUNT_ID
from ai_trading.storage.ledger_tables import (
    DailyValuationRow,
    MarketBarRow,
    WorkflowRunRow,
)
from ai_trading.storage.tables import (
    AccountRow,
    CashBalanceRow,
    InstrumentRow,
    OrderRow,
    PositionRow,
    TradePlanRow,
    TradeProposalRow,
    WatchlistEntryRow,
)

CORE_TABLES: tuple[str, ...] = (
    AccountRow.__tablename__,
    CashBalanceRow.__tablename__,
    DailyValuationRow.__tablename__,
    InstrumentRow.__tablename__,
    MarketBarRow.__tablename__,
    OrderRow.__tablename__,
    PositionRow.__tablename__,
    TradePlanRow.__tablename__,
    TradeProposalRow.__tablename__,
    WatchlistEntryRow.__tablename__,
    WorkflowRunRow.__tablename__,
)


class DashboardQueries:
    """仅执行查询且不会建表、建账户或写入任何交易数据。"""

    def __init__(
        self,
        engine: Engine,
        session_factory: sessionmaker[Session],
        settings: Settings,
    ) -> None:
        self._engine = engine
        self._session_factory = session_factory
        self._settings = settings

    def database_initialized(self) -> bool:
        try:
            table_names = set(inspect(self._engine).get_table_names())
        except SQLAlchemyError:
            return False
        return all(name in table_names for name in CORE_TABLES)

    def overview(self) -> OverviewResponse:
        if not self.database_initialized():
            return self._empty_overview()
        with self._session_factory() as session:
            account = session.get(AccountRow, DEFAULT_ACCOUNT_ID)
            if account is None:
                return self._empty_overview(database_initialized=True)
            balances = tuple(
                CashBalanceView(
                    currency=row.currency,
                    available_micros=row.available_micros,
                    reserved_micros=row.reserved_micros,
                )
                for row in session.scalars(
                    select(CashBalanceRow)
                    .where(CashBalanceRow.account_id == account.id)
                    .order_by(CashBalanceRow.currency)
                )
            )
            positions = tuple(
                session.scalars(
                    select(PositionRow).where(
                        PositionRow.account_id == account.id,
                        PositionRow.quantity > 0,
                    )
                )
            )
            orders = tuple(
                session.scalars(select(OrderRow).where(OrderRow.account_id == account.id))
            )
            status_counts = tuple(
                OrderStatusCount(
                    status=status,
                    count=sum(1 for order in orders if order.status is status),
                )
                for status in OrderStatus
            )
            return OverviewResponse(
                database_initialized=True,
                account_initialized=True,
                account_id=account.id,
                base_currency=account.base_currency,
                configured_initial_cash_cny_micros=self._settings.initial_cash_cny_micros,
                cash_balances=balances,
                position_count=len(positions),
                order_count=len(orders),
                order_statuses=status_counts,
            )

    def account(self) -> AccountResponse:
        return account_snapshot(
            self._session_factory,
            self._settings,
            self.database_initialized(),
        )

    def watchlist(self) -> WatchlistResponse:
        if not self.database_initialized():
            return WatchlistResponse(
                items=(),
            )
        with self._session_factory() as session:
            account = session.get(AccountRow, DEFAULT_ACCOUNT_ID)
            if account is None:
                return WatchlistResponse(
                    items=(),
                )
            entries = tuple(
                session.scalars(
                    select(WatchlistEntryRow)
                    .where(WatchlistEntryRow.account_id == account.id)
                    .order_by(WatchlistEntryRow.instrument_id)
                )
            )
            items = tuple(
                item
                for entry in entries
                if (item := watchlist_item(session, entry, account.id)) is not None
            )
            return WatchlistResponse(items=items)

    def trade_plans(self) -> TradePlansResponse:
        if not self.database_initialized():
            return TradePlansResponse(
                database_initialized=False,
                account_initialized=False,
                items=(),
            )
        with self._session_factory() as session:
            account = session.get(AccountRow, DEFAULT_ACCOUNT_ID)
            if account is None:
                return TradePlansResponse(
                    database_initialized=True,
                    account_initialized=False,
                    items=(),
                )
            rows = tuple(
                session.scalars(
                    select(TradePlanRow)
                    .where(TradePlanRow.account_id == account.id)
                    .order_by(TradePlanRow.trade_date.desc(), TradePlanRow.id.desc())
                )
            )
            return TradePlansResponse(
                database_initialized=True,
                account_initialized=True,
                items=tuple(trade_plan_view(session, row) for row in rows),
            )

    def plans(self) -> PlansResponse:
        if not self.database_initialized():
            return PlansResponse(items=())
        with self._session_factory() as session:
            account = session.get(AccountRow, DEFAULT_ACCOUNT_ID)
            if account is None:
                return PlansResponse(items=())
            latest = session.scalar(
                select(TradePlanRow)
                .where(TradePlanRow.account_id == account.id)
                .order_by(TradePlanRow.trade_date.desc(), TradePlanRow.id.desc())
                .limit(1)
            )
            if latest is None:
                return PlansResponse(items=())
            proposals = tuple(
                session.scalars(
                    select(TradeProposalRow)
                    .where(TradeProposalRow.trade_plan_id == latest.id)
                    .order_by(TradeProposalRow.instrument_id)
                )
            )
            return PlansResponse(
                items=tuple(
                    PlanItem(
                        symbol=proposal.instrument_id,
                        action=proposal.action,
                        confidence_bps=proposal.confidence_micros // 100,
                        target_weight_bps=(
                            0
                            if proposal.target_weight_micros is None
                            else proposal.target_weight_micros // 100
                        ),
                        reason=proposal.reason or "历史计划未记录理由",
                        status=latest.status,
                    )
                    for proposal in proposals
                )
            )

    def orders(self) -> OrdersResponse:
        if not self.database_initialized():
            return OrdersResponse(items=())
        with self._session_factory() as session:
            account = session.get(AccountRow, DEFAULT_ACCOUNT_ID)
            if account is None:
                return OrdersResponse(items=())
            rows = tuple(
                session.scalars(
                    select(OrderRow)
                    .where(OrderRow.account_id == account.id)
                    .order_by(OrderRow.trade_date.desc(), OrderRow.created_at.desc())
                )
            )
            return OrdersResponse(
                items=tuple(order_view(row) for row in rows),
            )

    def performance(self) -> PerformanceResponse:
        return performance_response(
            self._session_factory,
            self._settings,
            self.database_initialized(),
        )

    def data_health(self) -> DataHealthResponse:
        database_initialized = self.database_initialized()
        account_initialized = self._account_initialized(database_initialized)
        return data_health_response(
            self._session_factory,
            self._settings,
            database_initialized,
            account_initialized,
        )

    def _account_initialized(self, database_initialized: bool) -> bool:
        if not database_initialized:
            return False
        with self._session_factory() as session:
            return session.get(AccountRow, DEFAULT_ACCOUNT_ID) is not None

    def _empty_overview(self, database_initialized: bool = False) -> OverviewResponse:
        return OverviewResponse(
            database_initialized=database_initialized,
            account_initialized=False,
            account_id=None,
            base_currency=None,
            configured_initial_cash_cny_micros=self._settings.initial_cash_cny_micros,
            cash_balances=(),
            position_count=0,
            order_count=0,
            order_statuses=tuple(
                OrderStatusCount(status=status, count=0) for status in OrderStatus
            ),
        )
