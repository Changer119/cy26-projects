from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from ai_trading.config import Settings
from ai_trading.domain import (
    Currency,
    Order,
    OrderSide,
    OrderStatus,
    ProposalStatus,
    TradeAction,
    TradePlan,
    TradePlanStatus,
    TradeProposal,
    decimal_to_micros,
)
from ai_trading.storage import (
    DEFAULT_ACCOUNT_ID,
    DailyValuationRow,
    MarketBarRow,
    PositionRow,
    TradingRepository,
    WorkflowRunRow,
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)


def settings_for(database_path: Path) -> Settings:
    settings = Settings(_env_file=None, project_root=database_path.parent)
    settings.database_url_override = f"sqlite+pysqlite:///{database_path}"
    return settings


@pytest.fixture
def uninitialized_settings(tmp_path: Path) -> Settings:
    return settings_for(tmp_path / "missing.db")


@pytest.fixture
def populated_settings(tmp_path: Path) -> Settings:
    database_path = tmp_path / "populated.db"
    settings = settings_for(database_path)
    engine = create_sqlite_engine(settings.database_url)
    create_schema(engine)
    repository = TradingRepository(create_session_factory(engine))
    repository.initialize_default_portfolio()

    with repository.session() as session, session.begin():
        session.add(
            PositionRow(
                account_id=DEFAULT_ACCOUNT_ID,
                instrument_id="603005.SH",
                quantity=200,
                average_cost_micros=decimal_to_micros(Decimal("28.50")),
            )
        )
        session.add_all(
            (
                DailyValuationRow(
                    account_id=DEFAULT_ACCOUNT_ID,
                    trade_date=date(2026, 7, 14),
                    nav_cny_micros=100_000_000_000,
                    cash_cny_micros=100_000_000_000,
                    realized_pnl_cny_micros=0,
                    unrealized_pnl_cny_micros=0,
                    fees_cny_micros=0,
                    drawdown_micros=0,
                ),
                DailyValuationRow(
                    account_id=DEFAULT_ACCOUNT_ID,
                    trade_date=date(2026, 7, 15),
                    nav_cny_micros=103_500_000_000,
                    cash_cny_micros=72_000_000_000,
                    realized_pnl_cny_micros=500_000_000,
                    unrealized_pnl_cny_micros=3_010_000_000,
                    fees_cny_micros=10_000_000,
                    drawdown_micros=62_000,
                ),
                MarketBarRow(
                    instrument_id="603005.SH",
                    trade_date=date(2026, 7, 15),
                    source="Yahoo Finance",
                    currency=Currency.CNY,
                    open_micros=28_000_000,
                    high_micros=30_000_000,
                    low_micros=27_500_000,
                    close_micros=29_100_000,
                    volume=1_000_000,
                    available_at=datetime(
                        2026,
                        7,
                        15,
                        18,
                        15,
                        tzinfo=ZoneInfo("Asia/Shanghai"),
                    ),
                    quality_status="healthy",
                ),
                WorkflowRunRow(
                    account_id=DEFAULT_ACCOUNT_ID,
                    trade_date=date(2026, 7, 15),
                    workflow="postmarket",
                    status="COMPLETED",
                    reason="收盘结算完成",
                    started_at=datetime(
                        2026,
                        7,
                        15,
                        18,
                        15,
                        tzinfo=ZoneInfo("Asia/Shanghai"),
                    ),
                    finished_at=datetime(
                        2026,
                        7,
                        15,
                        18,
                        16,
                        tzinfo=ZoneInfo("Asia/Shanghai"),
                    ),
                ),
            )
        )

    repository.save_trade_plan(
        TradePlan(
            plan_id="plan-20260715",
            account_id=DEFAULT_ACCOUNT_ID,
            trade_date=date(2026, 7, 15),
            decision_asof=datetime(
                2026,
                7,
                15,
                8,
                35,
                tzinfo=ZoneInfo("Asia/Shanghai"),
            ),
            status=TradePlanStatus.RISK_CHECKED,
            proposals=(
                TradeProposal(
                    proposal_id="proposal-603005",
                    instrument_id="603005.SH",
                    action=TradeAction.BUY,
                    current_quantity=200,
                    target_quantity=300,
                    delta_quantity=100,
                    limit_price=Decimal("29.10"),
                    status=ProposalStatus.RISK_APPROVED,
                    confidence=Decimal("0.82"),
                    reason="中期趋势向上；本地按 ATR 与风险预算计算仓位",
                    strategy_version="AGGRESSIVE_V2",
                    target_weight=Decimal("0.15"),
                    reference_price=Decimal("28.80"),
                    stop_price=Decimal("25.50"),
                ),
            ),
        )
    )
    repository.create_order(
        Order(
            order_id="order-603005",
            account_id=DEFAULT_ACCOUNT_ID,
            instrument_id="603005.SH",
            trade_date=date(2026, 7, 15),
            side=OrderSide.BUY,
            quantity=100,
            limit_price=Decimal("29.10"),
            status=OrderStatus.PENDING_OPEN,
        )
    )
    return settings
