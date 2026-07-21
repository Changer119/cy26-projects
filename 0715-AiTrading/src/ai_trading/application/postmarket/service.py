from collections.abc import Callable
from datetime import date, datetime, time
from decimal import Decimal
from typing import Protocol
from zoneinfo import ZoneInfo

from sqlalchemy import select

from ai_trading.application.models import (
    EvidenceBatch,
    QualifiedMarketEvidence,
    WorkflowReport,
    WorkflowStatus,
)
from ai_trading.application.postmarket.reporting import (
    postmarket_report,
    postmarket_timing_rejection,
)
from ai_trading.application.store import ApplicationStore
from ai_trading.domain import (
    Currency,
    Instrument,
    OrderStatus,
    decimal_to_micros,
)
from ai_trading.storage import (
    DEFAULT_ACCOUNT_ID,
    CashBalanceRow,
    DailyValuationRow,
    InstrumentRow,
    MarketBarRow,
    OrderRow,
    PositionRow,
)
from ai_trading.storage.settlement import (
    SettlementError,
    SettlementRepository,
    SettlementRequest,
)
from ai_trading.storage.valuation import (
    ValuationError,
    ValuationMark,
    ValuationRepository,
)
from ai_trading.trading.execution import (
    ExecutionStatus,
    MarketBar,
    OrderRequest,
    execute_opening_order,
)
from ai_trading.trading.fees import FeeSchedule, calculate_fees


class CurrentSessionEvidenceLoader(Protocol):
    def load_current_session(self, trade_date: date) -> EvidenceBatch: ...


class PostmarketService:
    def __init__(
        self,
        store: ApplicationStore,
        evidence_loader: CurrentSessionEvidenceLoader,
        fee_schedule: FeeSchedule,
        slippage_rate: Decimal,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._evidence_loader = evidence_loader
        self._fee_schedule = fee_schedule
        self._slippage_rate = slippage_rate
        self._clock = clock or (lambda: datetime.now(ZoneInfo("Asia/Shanghai")))
        self._settlements = SettlementRepository(store.session_factory)
        self._valuations = ValuationRepository(store.session_factory)

    def run(self, trade_date: date) -> WorkflowReport:
        if self._has_valuation(trade_date):
            return postmarket_report(
                WorkflowStatus.ALREADY_COMPLETED, trade_date, 0, "ALREADY_VALUED"
            )
        timing_reason = postmarket_timing_rejection(trade_date, self._clock())
        if timing_reason is not None:
            return postmarket_report(WorkflowStatus.HOLD, trade_date, 0, timing_reason)
        batch = self._evidence_loader.load_current_session(trade_date)
        evidence = tuple(item for item in batch.qualified if item.evidence_date == trade_date)
        pending = self._pending_orders(trade_date)
        if not evidence:
            self._mark_orders(pending, OrderStatus.DATA_UNAVAILABLE)
            if pending or self._missing_position_marks(evidence):
                return postmarket_report(WorkflowStatus.HOLD, trade_date, 0, batch.reason)
            valuation = self._valuations.record(DEFAULT_ACCOUNT_ID, trade_date, ())
            reason = f"PAPER_RECONCILED:NAV_CNY={valuation.nav_cny}"
            return postmarket_report(WorkflowStatus.COMPLETED, trade_date, 0, reason, valuation)
        if self._missing_position_marks(evidence):
            self._mark_orders(pending, OrderStatus.DATA_UNAVAILABLE)
            return postmarket_report(WorkflowStatus.HOLD, trade_date, 0, batch.reason)
        self._record_market_bars(trade_date, evidence)

        fills = 0
        for order in pending:
            market = next(
                (item for item in evidence if item.instrument_id == order.instrument_id),
                None,
            )
            if market is None:
                self._mark_order(order.id, OrderStatus.DATA_UNAVAILABLE)
                continue
            instrument = self._instrument(order.instrument_id)
            if instrument is None:
                self._mark_order(order.id, OrderStatus.EXECUTION_REJECTED)
                continue
            execution = execute_opening_order(
                OrderRequest(
                    order_id=order.id,
                    instrument=instrument,
                    side=order.side,
                    quantity=order.quantity,
                    limit_price=Decimal(order.limit_price_micros) / 1_000_000,
                ),
                self._execution_bar(trade_date, market),
                self._slippage_rate,
            )
            if execution.status is not ExecutionStatus.FILLED or execution.fill_price is None:
                self._mark_order(order.id, OrderStatus.UNFILLED)
                continue
            try:
                fee = calculate_fees(
                    instrument,
                    order.side,
                    execution.fill_price * execution.filled_quantity,
                    trade_date,
                    self._fee_schedule,
                )
                outcome = self._settlements.apply(
                    SettlementRequest(
                        fill_id=f"fill:{order.id}",
                        order_id=order.id,
                        account_id=order.account_id,
                        instrument_id=order.instrument_id,
                        trade_date=trade_date,
                        side=order.side,
                        quantity=execution.filled_quantity,
                        price=execution.fill_price,
                        fx_to_cny=market.fx_to_cny,
                        fee_cny=fee.total,
                        fee_schedule_id=fee.schedule_id,
                    )
                )
            except (SettlementError, ValueError):
                self._mark_order(order.id, OrderStatus.EXECUTION_REJECTED)
                continue
            fills += int(outcome.applied)

        try:
            valuation = self._valuations.record(
                DEFAULT_ACCOUNT_ID,
                trade_date,
                tuple(
                    ValuationMark(
                        instrument_id=item.instrument_id,
                        close=item.close,
                        fx_to_cny=item.fx_to_cny,
                    )
                    for item in evidence
                    if self._is_held(item.instrument_id)
                ),
            )
        except ValuationError:
            return postmarket_report(
                WorkflowStatus.HOLD, trade_date, fills, "VALUATION_DATA_MISSING"
            )
        reason = f"PAPER_RECONCILED:NAV_CNY={valuation.nav_cny}"
        return postmarket_report(WorkflowStatus.COMPLETED, trade_date, fills, reason, valuation)

    def _pending_orders(self, trade_date: date) -> tuple[OrderRow, ...]:
        with self._store.session() as session:
            return tuple(
                session.scalars(
                    select(OrderRow).where(
                        OrderRow.account_id == DEFAULT_ACCOUNT_ID,
                        OrderRow.trade_date == trade_date,
                        OrderRow.status == OrderStatus.PENDING_OPEN,
                    )
                ).all()
            )

    def _has_valuation(self, trade_date: date) -> bool:
        with self._store.session() as session:
            return session.get(DailyValuationRow, (DEFAULT_ACCOUNT_ID, trade_date)) is not None

    def _missing_position_marks(
        self,
        evidence: tuple[QualifiedMarketEvidence, ...],
    ) -> bool:
        evidence_ids = tuple(item.instrument_id for item in evidence)
        with self._store.session() as session:
            held_ids = tuple(
                session.scalars(
                    select(PositionRow.instrument_id).where(
                        PositionRow.account_id == DEFAULT_ACCOUNT_ID,
                        PositionRow.quantity > 0,
                    )
                ).all()
            )
        return any(item not in evidence_ids for item in held_ids)

    def _instrument(self, instrument_id: str) -> Instrument | None:
        with self._store.session() as session:
            row = session.get(InstrumentRow, instrument_id)
            if row is None:
                return None
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

    def _is_held(self, instrument_id: str) -> bool:
        with self._store.session() as session:
            row = session.get(PositionRow, (DEFAULT_ACCOUNT_ID, instrument_id))
            return row is not None and row.quantity > 0

    def _mark_order(self, order_id: str, status: OrderStatus) -> None:
        with self._store.session() as session, session.begin():
            row = session.get(OrderRow, order_id)
            if row is not None and row.status is OrderStatus.PENDING_OPEN:
                if row.reserved_cash_micros > 0:
                    cash = session.get(
                        CashBalanceRow,
                        (row.account_id, Currency.CNY),
                    )
                    if cash is not None:
                        cash.reserved_micros -= row.reserved_cash_micros
                        cash.available_micros += row.reserved_cash_micros
                    row.reserved_cash_micros = 0
                row.status = status

    def _mark_orders(self, orders: tuple[OrderRow, ...], status: OrderStatus) -> None:
        for order in orders:
            self._mark_order(order.id, status)

    def _record_market_bars(
        self,
        trade_date: date,
        evidence: tuple[QualifiedMarketEvidence, ...],
    ) -> None:
        available_at = datetime.combine(trade_date, time(18), ZoneInfo("Asia/Shanghai"))
        with self._store.session() as session, session.begin():
            for item in evidence:
                key = (item.instrument_id, trade_date, "dual_source_canonical")
                if session.get(MarketBarRow, key) is not None:
                    continue
                session.add(
                    MarketBarRow(
                        instrument_id=item.instrument_id,
                        trade_date=trade_date,
                        source="dual_source_canonical",
                        currency=Currency.CNY,
                        open_micros=decimal_to_micros(item.open),
                        high_micros=decimal_to_micros(item.high),
                        low_micros=decimal_to_micros(item.low),
                        close_micros=decimal_to_micros(item.close),
                        volume=item.volume,
                        available_at=available_at,
                        quality_status="VALID",
                    )
                )

    @staticmethod
    def _execution_bar(
        trade_date: date,
        market: QualifiedMarketEvidence,
    ) -> MarketBar:
        opening = market.open
        high = market.high
        low = market.low
        locked = opening == high == low
        return MarketBar(
            instrument_id=market.instrument_id,
            session_date=trade_date,
            open_price=opening,
            high_price=high,
            low_price=low,
            close_price=market.close,
            volume=market.volume,
            available_at=datetime.combine(
                trade_date,
                time(18),
                ZoneInfo("Asia/Shanghai"),
            ),
            locked_limit_up=locked,
            locked_limit_down=locked,
        )
