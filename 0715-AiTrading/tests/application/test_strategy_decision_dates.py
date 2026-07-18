from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from ai_trading.application.models import (
    EvidenceBatch,
    QualifiedMarketEvidence,
    StrategyDecisionContext,
)
from ai_trading.strategy_v2.models import StrategyFeatures

INSTRUMENT_ID = "603005.SH"
TRADE_DATE = date(2026, 7, 15)


def market(evidence_date: date | None) -> QualifiedMarketEvidence:
    return QualifiedMarketEvidence(
        instrument_id=INSTRUMENT_ID,
        open=Decimal("20.00"),
        high=Decimal("20.50"),
        low=Decimal("19.80"),
        close=Decimal("20.10"),
        volume=1_000_000,
        fx_to_cny=Decimal("1"),
        evidence_date=evidence_date,
    )


def features(as_of: date) -> StrategyFeatures:
    return StrategyFeatures(
        instrument_id=INSTRUMENT_ID,
        as_of=as_of,
        history_sessions=60,
        close=Decimal("20.10"),
        sma_20=Decimal("19.50"),
        sma_60=Decimal("18.00"),
        atr_20=Decimal("1.00"),
        average_volume_20=1_000_000,
        support_20=Decimal("18.50"),
        resistance_20=Decimal("20.80"),
    )


def test_strategy_context_rejects_feature_and_market_date_mismatch() -> None:
    with pytest.raises(ValidationError, match="历史特征日期与行情证据日期不一致"):
        StrategyDecisionContext(
            market=market(date(2026, 7, 14)),
            features=features(date(2026, 7, 13)),
        )


def test_strategy_context_rejects_missing_market_evidence_date() -> None:
    with pytest.raises(ValidationError, match="行情证据日期不能为空"):
        StrategyDecisionContext(
            market=market(None),
            features=features(date(2026, 7, 14)),
        )


@pytest.mark.parametrize("evidence_date", (TRADE_DATE, date(2026, 7, 16)))
def test_strategy_batch_rejects_current_or_future_session_data(
    evidence_date: date,
) -> None:
    with pytest.raises(ValidationError, match="策略证据日期必须早于交易日"):
        EvidenceBatch(
            trade_date=TRADE_DATE,
            qualified=(market(evidence_date),),
            strategy_features=(features(evidence_date),),
            unavailable_instrument_ids=(),
            reason="DUAL_SOURCE_DATA_VALID",
        )


def test_strategy_batch_accepts_matching_previous_session_data() -> None:
    evidence_date = date(2026, 7, 14)

    batch = EvidenceBatch(
        trade_date=TRADE_DATE,
        qualified=(market(evidence_date),),
        strategy_features=(features(evidence_date),),
        unavailable_instrument_ids=(),
        reason="DUAL_SOURCE_DATA_VALID",
    )

    assert batch.qualified[0].evidence_date == evidence_date
    assert batch.strategy_features[0].as_of == evidence_date
