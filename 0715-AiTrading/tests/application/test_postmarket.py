from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import select

from ai_trading.application.models import (
    EvidenceBatch,
    QualifiedMarketEvidence,
    StrategyDecisionContext,
    WorkflowStatus,
)
from ai_trading.application.postmarket import PostmarketService
from ai_trading.application.store import ApplicationStore
from ai_trading.application.workflows import TradingApplication
from ai_trading.domain import Currency, OrderStatus, TradeAction
from ai_trading.storage import (
    DEFAULT_ACCOUNT_ID,
    CashBalanceRow,
    DailyValuationRow,
    FillRow,
    OrderRow,
)
from ai_trading.strategy_v2.models import StrategyFeatures, TradeSignal
from ai_trading.trading.fees import FeeSchedule

TRADE_DATE = date(2026, 7, 15)
PREVIOUS_DATE = date(2026, 7, 14)
SHANGHAI = ZoneInfo("Asia/Shanghai")


class StaticSessionEvidence:
    def load(self, trade_date: date) -> EvidenceBatch:
        assert trade_date == TRADE_DATE
        return self._premarket_batch()

    def load_current_session(self, trade_date: date) -> EvidenceBatch:
        assert trade_date == TRADE_DATE
        return self._current_batch()

    @staticmethod
    def _premarket_batch() -> EvidenceBatch:
        return EvidenceBatch(
            trade_date=TRADE_DATE,
            qualified=(
                QualifiedMarketEvidence(
                    instrument_id="603005.SH",
                    open=Decimal("20.00"),
                    high=Decimal("20.50"),
                    low=Decimal("19.80"),
                    close=Decimal("20.10"),
                    volume=1_000_000,
                    fx_to_cny=Decimal("1"),
                    current_quantity=0,
                    evidence_date=PREVIOUS_DATE,
                ),
            ),
            strategy_features=(
                StrategyFeatures(
                    instrument_id="603005.SH",
                    as_of=PREVIOUS_DATE,
                    history_sessions=60,
                    close=Decimal("20.10"),
                    sma_20=Decimal("19.50"),
                    sma_60=Decimal("18.00"),
                    atr_20=Decimal("4.00"),
                    average_volume_20=1_000_000,
                    support_20=Decimal("15.00"),
                    resistance_20=Decimal("22.00"),
                ),
            ),
            unavailable_instrument_ids=("600584.SH", "02513.HK", "01810.HK"),
            reason="PARTIAL_DATA",
        )

    @staticmethod
    def _current_batch() -> EvidenceBatch:
        previous = StaticSessionEvidence._premarket_batch()
        market = previous.qualified[0]
        return EvidenceBatch(
            trade_date=TRADE_DATE,
            qualified=(market.model_copy(update={"evidence_date": TRADE_DATE}),),
            unavailable_instrument_ids=previous.unavailable_instrument_ids,
            reason=previous.reason,
        )


class StaticBuyProposal:
    def propose(
        self,
        context: tuple[StrategyDecisionContext, ...],
    ) -> tuple[TradeSignal, ...]:
        assert context[0].market.instrument_id == "603005.SH"
        return (
            TradeSignal(
                instrument_id="603005.SH",
                action=TradeAction.BUY,
                confidence=Decimal("0.8"),
                reason="趋势与量价结构支持买入",
            ),
        )


class OutsideLimitEvidence(StaticSessionEvidence):
    @staticmethod
    def _current_batch() -> EvidenceBatch:
        original = StaticSessionEvidence._current_batch()
        market = original.qualified[0]
        return EvidenceBatch(
            trade_date=original.trade_date,
            qualified=(
                QualifiedMarketEvidence(
                    instrument_id=market.instrument_id,
                    open=Decimal("21.00"),
                    high=Decimal("21.20"),
                    low=Decimal("20.80"),
                    close=Decimal("21.10"),
                    volume=market.volume,
                    fx_to_cny=market.fx_to_cny,
                    current_quantity=0,
                    evidence_date=TRADE_DATE,
                ),
            ),
            strategy_features=original.strategy_features,
            unavailable_instrument_ids=original.unavailable_instrument_ids,
            reason=original.reason,
        )


class EmptyEvidence(StaticSessionEvidence):
    @staticmethod
    def _current_batch() -> EvidenceBatch:
        return EvidenceBatch(
            trade_date=TRADE_DATE,
            qualified=(),
            unavailable_instrument_ids=(
                "603005.SH",
                "600584.SH",
                "02513.HK",
                "01810.HK",
            ),
            reason="DUAL_SOURCE_DATA_UNAVAILABLE",
        )


def fee_schedule() -> FeeSchedule:
    return FeeSchedule(
        schedule_id="a-share-simulation-v1",
        effective_from=date(2026, 1, 1),
        currency=Currency.CNY,
        commission_rate=Decimal("0.0003"),
        minimum_commission=Decimal("5"),
        transfer_rate=Decimal("0.00001"),
        stock_buy_tax_rate=Decimal("0"),
        stock_sell_tax_rate=Decimal("0.0005"),
    )


def test_postmarket_executes_paper_fill_and_records_daily_profit(tmp_path: Path) -> None:
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'postmarket.db'}")
    store.initialize()
    evidence = StaticSessionEvidence()
    postmarket = PostmarketService(
        store=store,
        evidence_loader=evidence,
        fee_schedule=fee_schedule(),
        slippage_rate=Decimal("0.001"),
    )
    application = TradingApplication(store, evidence, StaticBuyProposal(), postmarket)
    premarket = application.premarket(
        TRADE_DATE,
        datetime(2026, 7, 15, 8, 35, tzinfo=SHANGHAI),
    )

    assert premarket.orders_created == 1
    with store.session() as session:
        reserved_cash = session.get(CashBalanceRow, (DEFAULT_ACCOUNT_ID, Currency.CNY))
        assert reserved_cash is not None and reserved_cash.reserved_micros == 2_060_250_000
    report = application.postmarket(TRADE_DATE)

    assert report.status is WorkflowStatus.COMPLETED
    assert report.fills_recorded == 1
    assert report.nav_cny == Decimal("100002.97998")
    assert report.daily_pnl_cny == Decimal("2.97998")
    assert report.total_pnl_cny == Decimal("2.97998")
    assert report.drawdown == Decimal("0")
    with store.session() as session:
        order = session.scalar(select(OrderRow))
        fill = session.scalar(select(FillRow))
        valuation = session.scalar(select(DailyValuationRow))
        assert order is not None and order.status == "FILLED"
        assert order.reserved_cash_micros == 0
        assert fill is not None and fill.price_micros == 20_020_000
        assert valuation is not None
        assert valuation.nav_cny_micros == 100_002_979_980


def test_unfilled_order_releases_all_reserved_cash(tmp_path: Path) -> None:
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'unfilled.db'}")
    store.initialize()
    evidence = OutsideLimitEvidence()
    application = TradingApplication(
        store,
        evidence,
        StaticBuyProposal(),
        PostmarketService(store, evidence, fee_schedule(), Decimal("0.001")),
    )
    application.premarket(
        TRADE_DATE,
        datetime(2026, 7, 15, 8, 35, tzinfo=SHANGHAI),
    )

    report = application.postmarket(TRADE_DATE)

    assert report.status is WorkflowStatus.COMPLETED
    assert report.fills_recorded == 0
    assert report.daily_pnl_cny == Decimal("0")
    with store.session() as session:
        order = session.scalar(select(OrderRow))
        cash = session.get(CashBalanceRow, (DEFAULT_ACCOUNT_ID, Currency.CNY))
        assert order is not None and order.status is OrderStatus.UNFILLED
        assert order.reserved_cash_micros == 0
        assert cash is not None and cash.available_micros == 100_000_000_000
        assert cash.reserved_micros == 0


def test_postmarket_before_cutoff_preserves_pending_order_and_reservation(tmp_path: Path) -> None:
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'too-early.db'}")
    store.initialize()
    evidence = StaticSessionEvidence()
    service = PostmarketService(
        store,
        evidence,
        fee_schedule(),
        Decimal("0.001"),
        clock=lambda: datetime(2026, 7, 15, 17, 59, tzinfo=SHANGHAI),
    )
    application = TradingApplication(store, evidence, StaticBuyProposal(), service)
    application.premarket(
        TRADE_DATE,
        datetime(2026, 7, 15, 8, 35, tzinfo=SHANGHAI),
    )

    report = application.postmarket(TRADE_DATE)

    assert report.status is WorkflowStatus.HOLD
    assert report.reason == "POSTMARKET_CUTOFF_NOT_REACHED"
    with store.session() as session:
        order = session.scalar(select(OrderRow))
        cash = session.get(CashBalanceRow, (DEFAULT_ACCOUNT_ID, Currency.CNY))
        assert order is not None and order.status is OrderStatus.PENDING_OPEN
        assert cash is not None and cash.reserved_micros == 2_060_250_000
        assert session.scalar(select(DailyValuationRow)) is None


def test_all_cash_account_can_still_record_zero_pnl_without_market_data(tmp_path: Path) -> None:
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'cash-only.db'}")
    store.initialize()
    evidence = EmptyEvidence()
    service = PostmarketService(store, evidence, fee_schedule(), Decimal("0.001"))

    report = service.run(TRADE_DATE)

    assert report.status is WorkflowStatus.COMPLETED
    assert report.fills_recorded == 0
    assert report.nav_cny == Decimal("100000")
    assert report.daily_pnl_cny == Decimal("0")
    with store.session() as session:
        valuation = session.scalar(select(DailyValuationRow))
        assert valuation is not None
        assert valuation.nav_cny_micros == 100_000_000_000


def test_postmarket_replay_does_not_duplicate_fill_or_valuation(tmp_path: Path) -> None:
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'replay.db'}")
    store.initialize()
    evidence = StaticSessionEvidence()
    application = TradingApplication(
        store,
        evidence,
        StaticBuyProposal(),
        PostmarketService(store, evidence, fee_schedule(), Decimal("0.001")),
    )
    application.premarket(
        TRADE_DATE,
        datetime(2026, 7, 15, 8, 35, tzinfo=SHANGHAI),
    )

    first = application.postmarket(TRADE_DATE)
    repeated = application.postmarket(TRADE_DATE)

    assert first.fills_recorded == 1
    assert repeated.status is WorkflowStatus.ALREADY_COMPLETED
    assert repeated.fills_recorded == 0
