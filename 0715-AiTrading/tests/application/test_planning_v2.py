from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from ai_trading.application.models import (
    QualifiedMarketEvidence,
    StrategyDecisionContext,
)
from ai_trading.application.planning import DeepSeekProposalSource, premarket_timing_rejection
from ai_trading.domain import TradeAction
from ai_trading.strategy_v2.models import StrategyFeatures


class RecordingClient:
    def __init__(self) -> None:
        self.system_prompt = ""
        self.user_prompt = ""

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
    ) -> BaseModel:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return response_model.model_validate(
            {
                "proposals": [
                    {
                        "instrument_id": "603005.SH",
                        "action": "BUY",
                        "confidence": Decimal("0.82"),
                        "reason": "中期趋势向上且波动可控",
                    }
                ]
            }
        )


def context() -> StrategyDecisionContext:
    return StrategyDecisionContext(
        market=QualifiedMarketEvidence(
            instrument_id="603005.SH",
            open=Decimal("20"),
            high=Decimal("21"),
            low=Decimal("19"),
            close=Decimal("20.5"),
            volume=1_000_000,
            fx_to_cny=Decimal(1),
            current_quantity=0,
            evidence_date=date(2026, 7, 14),
        ),
        features=StrategyFeatures(
            instrument_id="603005.SH",
            as_of=date(2026, 7, 14),
            history_sessions=60,
            close=Decimal("20.5"),
            sma_20=Decimal("19"),
            sma_60=Decimal("17"),
            atr_20=Decimal("1.2"),
            average_volume_20=900_000,
            support_20=Decimal("18"),
            resistance_20=Decimal("21"),
        ),
    )


def test_deepseek_receives_v2_features_but_returns_direction_only() -> None:
    client = RecordingClient()
    source = DeepSeekProposalSource(client)  # type: ignore[arg-type]

    signals = source.propose((context(),))

    assert signals[0].action is TradeAction.BUY
    assert signals[0].confidence == Decimal("0.82")
    assert signals[0].reason == "中期趋势向上且波动可控"
    assert "不得给价格、数量" in client.system_prompt
    assert '"sma_60":"17"' in client.user_prompt
    assert '"atr_20":"1.2"' in client.user_prompt


def test_exchange_holiday_is_rejected_before_loading_market_data() -> None:
    holiday = date(2026, 2, 23)

    reason = premarket_timing_rejection(
        holiday,
        datetime(2026, 2, 23, 8, 35, tzinfo=ZoneInfo("Asia/Shanghai")),
    )

    assert reason == "NON_TRADING_DAY"
