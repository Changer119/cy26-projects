from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_trading.api.schemas import (
    AddedBy,
    HealthStatus,
    OrderView,
    TradePlanView,
    TradeProposalView,
    WatchlistItem,
)
from ai_trading.domain import TradeAction
from ai_trading.storage import INITIAL_INSTRUMENTS
from ai_trading.storage.ledger_tables import MarketBarRow
from ai_trading.storage.tables import (
    InstrumentRow,
    OrderRow,
    TradePlanRow,
    TradeProposalRow,
    WatchlistEntryRow,
)

INITIAL_INSTRUMENT_IDS: tuple[str, ...] = tuple(
    instrument.instrument_id for instrument in INITIAL_INSTRUMENTS
)


def watchlist_item(
    session: Session,
    entry: WatchlistEntryRow,
    account_id: str,
) -> WatchlistItem | None:
    instrument = session.get(InstrumentRow, entry.instrument_id)
    if instrument is None:
        return None
    latest_proposal = session.scalar(
        select(TradeProposalRow)
        .join(TradePlanRow, TradeProposalRow.trade_plan_id == TradePlanRow.id)
        .where(
            TradePlanRow.account_id == account_id,
            TradeProposalRow.instrument_id == instrument.id,
        )
        .order_by(TradePlanRow.trade_date.desc(), TradePlanRow.decision_asof.desc())
        .limit(1)
    )
    decision = TradeAction.HOLD if latest_proposal is None else latest_proposal.action
    added_by: AddedBy = "USER" if instrument.id in INITIAL_INSTRUMENT_IDS else "AI"
    latest_bar = session.scalar(
        select(MarketBarRow)
        .where(MarketBarRow.instrument_id == instrument.id)
        .order_by(MarketBarRow.trade_date.desc(), MarketBarRow.available_at.desc())
        .limit(1)
    )
    change_bps: int | None = None
    data_status: HealthStatus = "unavailable"
    if latest_bar is not None:
        previous_bar = session.scalar(
            select(MarketBarRow)
            .where(
                MarketBarRow.instrument_id == instrument.id,
                MarketBarRow.source == latest_bar.source,
                MarketBarRow.trade_date < latest_bar.trade_date,
            )
            .order_by(MarketBarRow.trade_date.desc())
            .limit(1)
        )
        if previous_bar is not None:
            change_bps = (
                (latest_bar.close_micros - previous_bar.close_micros)
                * 10_000
                // previous_bar.close_micros
            )
        data_status = _bar_status(latest_bar.quality_status)
    return WatchlistItem(
        symbol=instrument.id,
        name=instrument.name,
        market=instrument.market,
        last_price_micros=(None if latest_bar is None else latest_bar.close_micros),
        change_bps=change_bps,
        decision=decision,
        data_status=data_status,
        added_by=added_by,
    )


def trade_plan_view(session: Session, row: TradePlanRow) -> TradePlanView:
    proposals = tuple(
        session.scalars(
            select(TradeProposalRow)
            .where(TradeProposalRow.trade_plan_id == row.id)
            .order_by(TradeProposalRow.instrument_id)
        )
    )
    return TradePlanView(
        plan_id=row.id,
        trade_date=row.trade_date,
        decision_asof=row.decision_asof,
        status=row.status,
        proposals=tuple(
            TradeProposalView(
                proposal_id=proposal.id,
                instrument_id=proposal.instrument_id,
                action=proposal.action,
                current_quantity=proposal.current_quantity,
                target_quantity=proposal.target_quantity,
                delta_quantity=proposal.delta_quantity,
                limit_price_micros=proposal.limit_price_micros,
                status=proposal.status,
                confidence_micros=proposal.confidence_micros,
            )
            for proposal in proposals
        ),
    )


def order_view(row: OrderRow) -> OrderView:
    return OrderView(
        id=row.id,
        symbol=row.instrument_id,
        trade_date=row.trade_date,
        side=row.side,
        quantity=row.quantity,
        limit_price_micros=row.limit_price_micros,
        status=row.status,
        reason="订单理由未持久化",
    )


def _bar_status(value: str) -> HealthStatus:
    normalized = value.strip().lower()
    if normalized in ("healthy", "ok", "good", "valid"):
        return "healthy"
    if normalized in ("unavailable", "missing", "failed"):
        return "unavailable"
    return "degraded"
