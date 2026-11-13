from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import httpx

from ai_trading.application.runtime import _build_evidence_loader
from ai_trading.application.store import ApplicationStore
from ai_trading.config import Settings
from ai_trading.integrations.market_data import MarketBar


def test_default_runtime_uses_backup_without_tiingo_token(tmp_path: Path) -> None:
    store = ApplicationStore(f"sqlite:///{tmp_path / 'test.db'}")
    store.initialize()
    day = date(2026, 10, 28)

    def fetch(provider: object, request: object) -> MarketBar:
        from ai_trading.integrations.market_data import MarketDataRequest

        assert isinstance(request, MarketDataRequest)
        return MarketBar(
            symbol=request.symbol,
            trade_date=day,
            open=Decimal(10),
            high=Decimal(11),
            low=Decimal(9),
            close=Decimal(10),
            volume=10000,
            currency="CNY",
            source="tushare",
        )

    with (
        patch(
            "ai_trading.integrations.china.akshare.AkshareEodProvider.fetch",
            side_effect=TimeoutError,
        ),
        patch("ai_trading.integrations.china.tushare.TushareEodProvider.fetch", new=fetch),
        httpx.Client() as client,
    ):
        loader = _build_evidence_loader(Settings(_env_file=None), store, client)
        result = loader.load_current_session(day)
    assert result.qualified
    assert len(result.qualified) == 2
    assert result.unavailable_instrument_ids == ("01810.HK", "02513.HK")
