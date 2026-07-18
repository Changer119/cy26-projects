from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from ai_trading.application.models import QualifiedMarketEvidence
from ai_trading.application.store import ApplicationStore
from ai_trading.domain import (
    OrderSide,
    OrderStatus,
    ProposalStatus,
    TradeAction,
    TradePlanStatus,
)
from ai_trading.storage import (
    DEFAULT_ACCOUNT_ID,
    DailyValuationRow,
    OrderRow,
    PositionRow,
    TradePlanRow,
    TradeProposalRow,
)


def test_portfolio_snapshot_uses_persisted_high_water_mark(tmp_path: Path) -> None:
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'high-water.db'}")
    store.initialize()
    with store.session() as session, session.begin():
        session.add(
            DailyValuationRow(
                account_id=DEFAULT_ACCOUNT_ID,
                trade_date=date(2026, 7, 14),
                nav_cny_micros=150_000_000_000,
                cash_cny_micros=150_000_000_000,
                realized_pnl_cny_micros=50_000_000_000,
                unrealized_pnl_cny_micros=0,
                fees_cny_micros=0,
                drawdown_micros=0,
            )
        )

    snapshot = store.portfolio_snapshot(())

    assert snapshot.nav_cny == Decimal("100000")
    assert snapshot.peak_nav_cny == Decimal("150000")
    assert snapshot.drawdown == Decimal("0.3333333333333333333333333333")


def test_portfolio_snapshot_loads_stop_from_latest_filled_buy(tmp_path: Path) -> None:
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'active-stop.db'}")
    store.initialize()
    trade_date = date(2026, 7, 14)
    with store.session() as session, session.begin():
        session.add(
            PositionRow(
                account_id=DEFAULT_ACCOUNT_ID,
                instrument_id="603005.SH",
                quantity=300,
                average_cost_micros=20_000_000,
            )
        )
        session.add(
            TradePlanRow(
                id="premarket:2026-07-14",
                account_id=DEFAULT_ACCOUNT_ID,
                trade_date=trade_date,
                decision_asof=datetime(2026, 7, 14, 8, 35, tzinfo=ZoneInfo("Asia/Shanghai")),
                status=TradePlanStatus.FROZEN,
            )
        )
        session.add(
            TradeProposalRow(
                id="proposal:stop",
                trade_plan_id="premarket:2026-07-14",
                instrument_id="603005.SH",
                action=TradeAction.BUY,
                current_quantity=0,
                target_quantity=300,
                delta_quantity=300,
                limit_price_micros=20_100_000,
                status=ProposalStatus.RISK_APPROVED,
                confidence_micros=800_000,
                reason="测试止损",
                strategy_version="AGGRESSIVE_V2",
                target_weight_micros=60_000,
                reference_price_micros=20_000_000,
                stop_price_micros=18_400_000,
            )
        )
        session.add(
            OrderRow(
                id="order:2026-07-14:603005.SH",
                account_id=DEFAULT_ACCOUNT_ID,
                instrument_id="603005.SH",
                trade_date=trade_date,
                side=OrderSide.BUY,
                quantity=300,
                limit_price_micros=20_100_000,
                reserved_cash_micros=0,
                status=OrderStatus.FILLED,
            )
        )

    snapshot = store.portfolio_snapshot(
        (
            QualifiedMarketEvidence(
                instrument_id="603005.SH",
                open=Decimal("20"),
                high=Decimal("21"),
                low=Decimal("19"),
                close=Decimal("20"),
                volume=1_000_000,
                fx_to_cny=Decimal(1),
                evidence_date=date(2026, 7, 15),
            ),
        )
    )

    assert snapshot.positions[0].stop_price == Decimal("18.4")
