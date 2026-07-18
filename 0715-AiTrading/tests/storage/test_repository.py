from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ai_trading.domain import (
    Currency,
    NotificationEvent,
    Order,
    OrderSide,
    OrderStatus,
    ProposalStatus,
    TradeAction,
    TradePlan,
    TradePlanStatus,
    TradeProposal,
)
from ai_trading.storage import (
    DEFAULT_ACCOUNT_ID,
    AccountRow,
    CashBalanceRow,
    InstrumentRow,
    NotificationOutboxRow,
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


@pytest.fixture
def repository(tmp_path: Path) -> TradingRepository:
    database_path = tmp_path / "trading.db"
    engine = create_sqlite_engine(f"sqlite+pysqlite:///{database_path}")
    create_schema(engine)
    return TradingRepository(create_session_factory(engine))


def make_order(order_id: str, instrument_id: str) -> Order:
    return Order(
        order_id=order_id,
        account_id=DEFAULT_ACCOUNT_ID,
        instrument_id=instrument_id,
        trade_date=date(2026, 7, 15),
        side=OrderSide.BUY,
        quantity=100,
        limit_price=Decimal("20.123456"),
        status=OrderStatus.PENDING_OPEN,
    )


def test_default_portfolio_has_100000_cny_and_four_watchlist_entries(
    repository: TradingRepository,
) -> None:
    repository.initialize_default_portfolio()
    repository.initialize_default_portfolio()

    with repository.session() as session:
        account = session.get(AccountRow, DEFAULT_ACCOUNT_ID)
        cny_cash = session.get(CashBalanceRow, (DEFAULT_ACCOUNT_ID, Currency.CNY))
        symbols = set(
            session.scalars(
                select(WatchlistEntryRow.instrument_id).where(
                    WatchlistEntryRow.account_id == DEFAULT_ACCOUNT_ID
                )
            )
        )

        assert account is not None
        assert cny_cash is not None
        assert cny_cash.available_micros == 100_000_000_000
        assert cny_cash.reserved_micros == 0
        assert symbols == {"603005.SH", "600584.SH", "02513.HK", "01810.HK"}
        assert session.scalar(select(func.count()).select_from(InstrumentRow)) == 4
        semiconductor = session.get(InstrumentRow, "603005.SH")
        assert semiconductor is not None
        assert semiconductor.industry == "半导体"


def test_same_symbol_same_day_order_is_unique_but_other_symbol_is_allowed(
    repository: TradingRepository,
) -> None:
    repository.initialize_default_portfolio()
    repository.create_order(make_order("order-1", "603005.SH"))
    repository.create_order(make_order("order-2", "600584.SH"))

    with pytest.raises(IntegrityError):
        repository.create_order(make_order("order-3", "603005.SH"))

    with repository.session() as session:
        assert session.scalar(select(func.count()).select_from(OrderRow)) == 2
        first = session.get(OrderRow, "order-1")
        assert first is not None
        assert first.limit_price_micros == 20_123_456


def test_trade_plan_and_proposal_statuses_are_persisted(
    repository: TradingRepository,
) -> None:
    repository.initialize_default_portfolio()
    proposal = TradeProposal(
        proposal_id="proposal-1",
        instrument_id="603005.SH",
        action=TradeAction.BUY,
        current_quantity=0,
        target_quantity=100,
        delta_quantity=100,
        limit_price=Decimal("20.123456"),
        status=ProposalStatus.RISK_APPROVED,
        confidence=Decimal("0.80"),
        reason="趋势、波动和量能支持买入；本地规则完成仓位计算",
        strategy_version="AGGRESSIVE_V2",
        target_weight=Decimal("0.20"),
        reference_price=Decimal("20.00"),
        stop_price=Decimal("18.00"),
    )
    plan = TradePlan(
        plan_id="plan-1",
        account_id=DEFAULT_ACCOUNT_ID,
        trade_date=date(2026, 7, 15),
        decision_asof=datetime(2026, 7, 15, 8, 35, tzinfo=ZoneInfo("Asia/Shanghai")),
        status=TradePlanStatus.RISK_CHECKED,
        proposals=(proposal,),
    )

    repository.save_trade_plan(plan)

    with repository.session() as session:
        plan_row = session.get(TradePlanRow, plan.plan_id)
        proposal_row = session.get(TradeProposalRow, proposal.proposal_id)
        assert plan_row is not None
        assert plan_row.status is TradePlanStatus.RISK_CHECKED
        assert proposal_row is not None
        assert proposal_row.status is ProposalStatus.RISK_APPROVED
        assert proposal_row.limit_price_micros == 20_123_456
        assert proposal_row.confidence_micros == 800_000
        assert proposal_row.reason.startswith("趋势")
        assert proposal_row.strategy_version == "AGGRESSIVE_V2"
        assert proposal_row.target_weight_micros == 200_000
        assert proposal_row.reference_price_micros == 20_000_000
        assert proposal_row.stop_price_micros == 18_000_000


def test_database_rejects_negative_cash_and_position(
    repository: TradingRepository,
) -> None:
    repository.initialize_default_portfolio()

    with repository.session() as session:
        cny_cash = session.get(CashBalanceRow, (DEFAULT_ACCOUNT_ID, Currency.CNY))
        assert cny_cash is not None
        cny_cash.available_micros = -1
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(
            PositionRow(
                account_id=DEFAULT_ACCOUNT_ID,
                instrument_id="603005.SH",
                quantity=-1,
                average_cost_micros=0,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_notification_outbox_is_idempotent(repository: TradingRepository) -> None:
    event = NotificationEvent(
        event_type="DAILY_PLAN",
        aggregate_id="plan-2026-07-15",
        recipient_id="user-271862",
        markdown="今日模拟交易计划 - HOLD",
    )

    assert repository.enqueue_notification(event) is True
    assert repository.enqueue_notification(event) is False

    with repository.session() as session:
        row = session.scalar(select(NotificationOutboxRow))
        assert row is not None
        assert row.markdown == event.markdown
        assert session.scalar(select(func.count()).select_from(NotificationOutboxRow)) == 1
