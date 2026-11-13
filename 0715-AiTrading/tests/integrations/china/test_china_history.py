from datetime import date

import pandas as pd

from ai_trading.integrations.china.akshare import AkshareEodProvider
from ai_trading.integrations.market_data import MarketDataRangeRequest


def test_akshare_history_anchors_adjustment_at_request_end() -> None:
    class Loader:
        def load(self, symbol: str, start: str, end: str, adjusted: bool) -> pd.DataFrame:
            rows = (
                [[date(2026, 10, 27), 4, 5, 3, 4, 100], [date(2026, 10, 28), 4, 5, 3, 4, 200]]
                if adjusted
                else [[date(2026, 10, 28), 5, 6, 4, 5, 200]]
            )
            return pd.DataFrame(rows, columns=["日期", "开盘", "最高", "最低", "收盘", "成交量"])

    bars = AkshareEodProvider(Loader()).fetch_range(
        MarketDataRangeRequest(
            symbol="600519.SH",
            provider_symbol="ignored",
            start_date=date(2026, 10, 27),
            end_date=date(2026, 10, 28),
            currency="CNY",
        )
    )
    assert bars[0].close == bars[1].close == 5
