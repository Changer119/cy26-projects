from pathlib import Path

from ai_trading.application.store import ApplicationStore


def test_initialize_is_idempotent_and_status_is_strongly_typed(tmp_path: Path) -> None:
    store = ApplicationStore(f"sqlite+pysqlite:///{tmp_path / 'trading.db'}")

    before = store.status()
    assert before.initialized is False
    assert before.paper_trading_only is True
    assert before.broker_connected is False

    store.initialize()
    store.initialize()

    after = store.status()
    assert after.initialized is True
    assert after.account_id == "paper-main"
    assert after.cash_cny_micros == 100_000_000_000
    assert after.watchlist_count == 4
    assert after.position_count == 0
    assert after.order_count == 0
