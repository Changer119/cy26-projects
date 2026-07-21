from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from ai_trading.application.models import (
    EvidenceBatch,
    QualifiedMarketEvidence,
    StrategyDecisionContext,
    WorkflowStatus,
)
from ai_trading.application.ports import ProposalUnavailable
from ai_trading.application.store import ApplicationStore
from ai_trading.application.workflows import TradingApplication
from ai_trading.domain import ProposalStatus, TradeAction
from ai_trading.storage import DEFAULT_ACCOUNT_ID, OrderRow, PositionRow, TradeProposalRow
from ai_trading.strategy_v2.models import StrategyFeatures, TradeSignal

SHANGHAI = ZoneInfo("Asia/Shanghai")
TRADE_DATE = date(2026, 7, 15)


class StaticEvidenceLoader:
    def __init__(self, batch: EvidenceBatch) -> None:
        self._batch = batch

    def load(self, trade_date: date) -> EvidenceBatch:
        assert trade_date == TRADE_DATE
        return self._batch


class StaticProposalSource:
    def __init__(self, signal: TradeSignal) -> None:
        self._signal = signal
        self.calls = 0

    def propose(self, context: tuple[StrategyDecisionContext, ...]) -> tuple[TradeSignal, ...]:
        self.calls += 1
        assert context[0].market.instrument_id == self._signal.instrument_id
        return (self._signal,)


class NeverEvidenceLoader:
    def load(self, trade_date: date) -> EvidenceBatch:
        raise AssertionError("时间门拒绝后不得读取行情")


class UnavailableProposalSource:
    def propose(self, context: tuple[StrategyDecisionContext, ...]) -> tuple[TradeSignal, ...]:
        raise ProposalUnavailable("测试：DeepSeek 不可用")


def evidence_batch() -> EvidenceBatch:
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
                evidence_date=date(2026, 7, 14),
            ),
        ),
        strategy_features=(
            StrategyFeatures(
                instrument_id="603005.SH",
                as_of=date(2026, 7, 14),
                history_sessions=60,
                close=Decimal("20.10"),
                sma_20=Decimal("19.50"),
                sma_60=Decimal("18.00"),
                atr_20=Decimal("1.00"),
                average_volume_20=1_000_000,
                support_20=Decimal("18.50"),
                resistance_20=Decimal("20.80"),
            ),
        ),
        unavailable_instrument_ids=("600584.SH", "02513.HK", "01810.HK"),
        reason="PARTIAL_DATA",
    )


def make_signal(confidence: str = "0.80") -> TradeSignal:
    return TradeSignal(
        instrument_id="603005.SH",
        action=TradeAction.BUY,
        confidence=Decimal(confidence),
        reason="趋势、波动和量能支持买入",
    )


def build_application(
    tmp_path: Path,
    source: StaticProposalSource,
) -> tuple[TradingApplication, ApplicationStore]:
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'trading.db'}")
    store.initialize()
    return TradingApplication(store, StaticEvidenceLoader(evidence_batch()), source), store


def test_ai_cannot_force_an_oversized_order_and_local_strategy_caps_position(
    tmp_path: Path,
) -> None:
    application, store = build_application(tmp_path, StaticProposalSource(make_signal()))

    report = application.premarket(
        TRADE_DATE,
        datetime(2026, 7, 15, 8, 35, tzinfo=SHANGHAI),
    )

    assert report.status is WorkflowStatus.COMPLETED
    assert report.orders_created == 1
    with store.session() as session:
        assert session.scalar(select(func.count()).select_from(OrderRow)) == 1
        row = session.scalar(
            select(TradeProposalRow).where(TradeProposalRow.instrument_id == "603005.SH")
        )
        assert row is not None
        assert row.status is ProposalStatus.RISK_APPROVED
        assert row.target_quantity == 500


def test_approved_ai_proposal_creates_one_paper_order_and_is_idempotent(tmp_path: Path) -> None:
    source = StaticProposalSource(make_signal())
    application, store = build_application(tmp_path, source)

    first = application.premarket(
        TRADE_DATE,
        datetime(2026, 7, 15, 8, 35, tzinfo=SHANGHAI),
    )
    second = application.premarket(
        TRADE_DATE,
        datetime(2026, 7, 15, 8, 40, tzinfo=SHANGHAI),
    )

    assert first.status is WorkflowStatus.COMPLETED
    assert first.orders_created == 1
    assert second.status is WorkflowStatus.ALREADY_COMPLETED
    assert source.calls == 1
    assert first.plan_id is not None
    decisions = store.plan_decisions(first.plan_id)
    buy = next(item for item in decisions if item.instrument_id == "603005.SH")
    assert buy.action is TradeAction.BUY
    assert buy.target_quantity == 500
    assert buy.limit_price == Decimal("20.35")
    with store.session() as session:
        assert session.scalar(select(func.count()).select_from(OrderRow)) == 1


def test_missing_market_evidence_creates_hold_plan_without_calling_ai(tmp_path: Path) -> None:
    source = StaticProposalSource(make_signal())
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'trading.db'}")
    store.initialize()
    batch = EvidenceBatch(
        trade_date=TRADE_DATE,
        qualified=(),
        unavailable_instrument_ids=("603005.SH", "600584.SH", "02513.HK", "01810.HK"),
        reason="DUAL_SOURCE_DATA_UNAVAILABLE",
    )
    application = TradingApplication(store, StaticEvidenceLoader(batch), source)

    report = application.premarket(
        TRADE_DATE,
        datetime(2026, 7, 15, 8, 35, tzinfo=SHANGHAI),
    )

    assert report.status is WorkflowStatus.HOLD
    assert report.orders_created == 0
    assert report.reason == "DUAL_SOURCE_DATA_UNAVAILABLE"
    assert source.calls == 0


def test_local_stop_still_creates_sell_order_when_deepseek_is_unavailable(
    tmp_path: Path,
) -> None:
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'trading.db'}")
    store.initialize()
    with store.session() as session, session.begin():
        session.add(
            PositionRow(
                account_id=DEFAULT_ACCOUNT_ID,
                instrument_id="603005.SH",
                quantity=300,
                average_cost_micros=100_000_000,
            )
        )
    application = TradingApplication(
        store,
        StaticEvidenceLoader(evidence_batch()),
        UnavailableProposalSource(),
    )

    report = application.premarket(
        TRADE_DATE,
        datetime(2026, 7, 15, 8, 35, tzinfo=SHANGHAI),
    )

    assert report.status is WorkflowStatus.COMPLETED
    with store.session() as session:
        order = session.scalar(select(OrderRow))
        assert order is not None
        assert order.quantity == 300


def test_postmarket_never_fabricates_fill_without_qualified_execution_evidence(
    tmp_path: Path,
) -> None:
    application, store = build_application(tmp_path, StaticProposalSource(make_signal()))
    application.premarket(
        TRADE_DATE,
        datetime(2026, 7, 15, 8, 35, tzinfo=SHANGHAI),
    )

    report = application.postmarket(TRADE_DATE)

    assert report.status is WorkflowStatus.HOLD
    assert report.fills_recorded == 0
    assert report.reason == "QUALIFIED_EXECUTION_EVIDENCE_UNAVAILABLE"
    assert store.status().position_count == 0


def test_backtest_without_persisted_historical_evidence_fails_closed(tmp_path: Path) -> None:
    application, _ = build_application(tmp_path, StaticProposalSource(make_signal()))

    report = application.backtest(date(2026, 7, 1), date(2026, 7, 15))

    assert report.status is WorkflowStatus.NO_DATA
    assert report.fills_recorded == 0
    assert report.reason == "HISTORICAL_EVIDENCE_UNAVAILABLE"


def test_premarket_after_0845_does_not_backfill_orders(tmp_path: Path) -> None:
    source = StaticProposalSource(make_signal())
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'trading.db'}")
    store.initialize()
    application = TradingApplication(store, NeverEvidenceLoader(), source)

    report = application.premarket(
        TRADE_DATE,
        datetime(2026, 7, 15, 8, 46, tzinfo=SHANGHAI),
    )

    assert report.status is WorkflowStatus.HOLD
    assert report.reason == "PREMARKET_CUTOFF_EXCEEDED"
    assert source.calls == 0
    assert store.status().order_count == 0


def test_weekend_premarket_is_hold_without_loading_data(tmp_path: Path) -> None:
    saturday = date(2026, 7, 18)
    source = StaticProposalSource(make_signal())
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'trading.db'}")
    store.initialize()
    application = TradingApplication(store, NeverEvidenceLoader(), source)

    report = application.premarket(
        saturday,
        datetime(2026, 7, 18, 8, 35, tzinfo=SHANGHAI),
    )

    assert report.status is WorkflowStatus.HOLD
    assert report.reason == "NON_TRADING_DAY"
    assert source.calls == 0
    assert store.status().order_count == 0


def test_naive_decision_time_fails_closed_without_persisting_invalid_plan(tmp_path: Path) -> None:
    source = StaticProposalSource(make_signal())
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'trading.db'}")
    store.initialize()
    application = TradingApplication(store, NeverEvidenceLoader(), source)

    report = application.premarket(TRADE_DATE, datetime(2026, 7, 15, 8, 35))

    assert report.status is WorkflowStatus.HOLD
    assert report.reason == "DECISION_TIMEZONE_MISSING"
    assert report.plan_id is None
    assert source.calls == 0
    assert store.status().order_count == 0
