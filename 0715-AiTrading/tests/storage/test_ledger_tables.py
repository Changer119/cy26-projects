from pathlib import Path

from sqlalchemy import inspect

from ai_trading.storage import create_schema, create_sqlite_engine


def test_schema_contains_immutable_fills_and_daily_valuations(tmp_path: Path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'ledger.db'}")

    create_schema(engine)

    table_names = set(inspect(engine).get_table_names())
    assert "fills" in table_names
    assert "daily_valuations" in table_names
    assert "market_bars" in table_names
    assert "workflow_runs" in table_names
