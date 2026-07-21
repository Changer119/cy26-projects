from datetime import datetime
from decimal import Decimal
from itertools import pairwise

from ai_trading.strategy_v2.models import HistoricalBar, StrategyFeatures


def calculate_features(
    instrument_id: str,
    bars: tuple[HistoricalBar, ...],
    decision_asof: datetime,
) -> StrategyFeatures:
    """仅使用决策时点之前已完成的至少 60 根日线计算特征。"""

    if len(bars) < 60:
        raise ValueError("V2 策略至少需要 60 个历史交易日")
    if any(left.trade_date >= right.trade_date for left, right in pairwise(bars)):
        raise ValueError("历史交易日必须严格递增且不得重复")
    if any(item.available_at > decision_asof for item in bars):
        raise ValueError("历史行情包含决策时点之后才可用的未来数据")
    if any(
        abs(right.close - left.close) / left.close > Decimal("0.25")
        for left, right in pairwise(bars)
    ):
        raise ValueError("历史行情疑似含未复权除权跳空，策略已关闭")

    latest = bars[-1]
    recent_20 = bars[-20:]
    recent_60 = bars[-60:]
    true_ranges: tuple[Decimal, ...] = ()
    start = len(bars) - 20
    for index in range(start, len(bars)):
        item = bars[index]
        previous_close = bars[index - 1].close
        true_ranges += (
            max(
                item.high - item.low,
                abs(item.high - previous_close),
                abs(item.low - previous_close),
            ),
        )
    return StrategyFeatures(
        instrument_id=instrument_id,
        as_of=latest.trade_date,
        history_sessions=len(bars),
        close=latest.close,
        sma_20=sum((item.close for item in recent_20), Decimal(0)) / 20,
        sma_60=sum((item.close for item in recent_60), Decimal(0)) / 60,
        atr_20=sum(true_ranges, Decimal(0)) / 20,
        average_volume_20=sum(item.volume for item in recent_20) // 20,
        support_20=min(item.low for item in recent_20),
        resistance_20=max(item.high for item in recent_20),
    )
