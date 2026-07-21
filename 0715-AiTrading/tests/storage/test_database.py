from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Connection, Engine

from ai_trading.storage.database import (
    _migrate_v2_audit_columns,
    create_schema,
    create_sqlite_engine,
)
from ai_trading.storage.tables import Base

V2_AUDIT_COLUMNS = {
    "reason",
    "strategy_version",
    "target_weight_micros",
    "reference_price_micros",
    "stop_price_micros",
}


def _create_full_legacy_proposal_table(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE trade_proposals")
        connection.exec_driver_sql(
            """
            CREATE TABLE trade_proposals (
                id VARCHAR(128) NOT NULL PRIMARY KEY,
                trade_plan_id VARCHAR(128) NOT NULL,
                instrument_id VARCHAR(16) NOT NULL,
                action VARCHAR(4) NOT NULL,
                current_quantity INTEGER NOT NULL,
                target_quantity INTEGER NOT NULL,
                delta_quantity INTEGER NOT NULL,
                limit_price_micros INTEGER,
                status VARCHAR(16) NOT NULL,
                confidence_micros INTEGER NOT NULL,
                CONSTRAINT uq_proposal_plan_instrument
                    UNIQUE (trade_plan_id, instrument_id),
                CONSTRAINT ck_proposal_current_nonnegative CHECK (current_quantity >= 0),
                CONSTRAINT ck_proposal_target_nonnegative CHECK (target_quantity >= 0),
                CONSTRAINT ck_proposal_limit_positive
                    CHECK (limit_price_micros IS NULL OR limit_price_micros > 0),
                CONSTRAINT ck_proposal_confidence_range
                    CHECK (confidence_micros BETWEEN 0 AND 1000000),
                FOREIGN KEY (trade_plan_id) REFERENCES trade_plans (id) ON DELETE CASCADE,
                FOREIGN KEY (instrument_id) REFERENCES instruments (id)
            )
            """
        )
        connection.exec_driver_sql(
            "INSERT INTO accounts (id, base_currency) VALUES (?, ?)",
            ("account-legacy", "CNY"),
        )
        connection.exec_driver_sql(
            """
            INSERT INTO instruments (
                id, name, market, currency, instrument_type,
                industry, lot_size, is_tradable
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "603005.SH",
                "晶方科技",
                "SSE",
                "CNY",
                "EQUITY",
                "半导体",
                100,
                1,
            ),
        )
        connection.exec_driver_sql(
            """
            INSERT INTO trade_plans (
                id, account_id, trade_date, decision_asof, status
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                "plan-legacy",
                "account-legacy",
                "2026-07-15",
                "2026-07-15 07:50:00",
                "FROZEN",
            ),
        )
        connection.exec_driver_sql(
            """
            INSERT INTO trade_proposals (
                id, trade_plan_id, instrument_id, action,
                current_quantity, target_quantity, delta_quantity,
                limit_price_micros, status, confidence_micros
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "proposal-legacy",
                "plan-legacy",
                "603005.SH",
                "BUY",
                100,
                200,
                100,
                31_500_000,
                "GENERATED",
                720_000,
            ),
        )


def _proposal_columns(engine: Engine) -> list[str]:
    return [item["name"] for item in inspect(engine).get_columns("trade_proposals")]


def test_file_database_enables_safety_pragmas(tmp_path: Path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'trading.db'}")

    with engine.connect() as connection:
        foreign_keys = connection.scalar(text("PRAGMA foreign_keys"))
        journal_mode = connection.scalar(text("PRAGMA journal_mode"))
        busy_timeout = connection.scalar(text("PRAGMA busy_timeout"))

    assert foreign_keys == 1
    assert journal_mode == "wal"
    assert busy_timeout == 5_000


def test_schema_upgrade_preserves_full_legacy_schema_and_data(tmp_path: Path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    _create_full_legacy_proposal_table(engine)

    create_schema(engine)

    assert set(_proposal_columns(engine)) >= V2_AUDIT_COLUMNS
    with engine.connect() as connection:
        migrated = connection.execute(
            text(
                """
                SELECT id, trade_plan_id, instrument_id, action,
                       current_quantity, target_quantity, delta_quantity,
                       limit_price_micros, status, confidence_micros,
                       reason, strategy_version, target_weight_micros,
                       reference_price_micros, stop_price_micros
                FROM trade_proposals
                """
            )
        ).one()
    assert tuple(migrated) == (
        "proposal-legacy",
        "plan-legacy",
        "603005.SH",
        "BUY",
        100,
        200,
        100,
        31_500_000,
        "GENERATED",
        720_000,
        None,
        None,
        None,
        None,
        None,
    )


def test_schema_upgrade_is_idempotent(tmp_path: Path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'idempotent.db'}")
    _create_full_legacy_proposal_table(engine)

    create_schema(engine)
    create_schema(engine)

    columns = _proposal_columns(engine)
    assert all(columns.count(name) == 1 for name in V2_AUDIT_COLUMNS)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM trade_proposals")) == 1


def test_schema_upgrade_recovers_from_partial_v2_migration(tmp_path: Path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'partial.db'}")
    _create_full_legacy_proposal_table(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE trade_proposals ADD COLUMN reason TEXT")
        connection.exec_driver_sql(
            "ALTER TABLE trade_proposals ADD COLUMN strategy_version VARCHAR(32)"
        )
        connection.exec_driver_sql(
            "UPDATE trade_proposals SET reason = ?, strategy_version = ?",
            ("旧迁移已写入", "AGGRESSIVE_V2"),
        )

    create_schema(engine)

    assert set(_proposal_columns(engine)) >= V2_AUDIT_COLUMNS
    with engine.connect() as connection:
        migrated = connection.execute(
            text("SELECT reason, strategy_version FROM trade_proposals")
        ).one()
    assert tuple(migrated) == ("旧迁移已写入", "AGGRESSIVE_V2")


def test_concurrent_duplicate_column_error_is_safe(tmp_path: Path) -> None:
    engine = create_sqlite_engine(f"sqlite:///{tmp_path / 'concurrent.db'}")
    _create_full_legacy_proposal_table(engine)
    competing_alters = Barrier(2)

    def synchronize_first_column(
        _connection: Connection,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if statement == "ALTER TABLE trade_proposals ADD COLUMN reason TEXT":
            competing_alters.wait(timeout=5)

    event.listen(engine, "before_cursor_execute", synchronize_first_column)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(_migrate_v2_audit_columns, engine) for _ in range(2)]
            for future in futures:
                future.result(timeout=10)
    finally:
        event.remove(engine, "before_cursor_execute", synchronize_first_column)

    assert set(_proposal_columns(engine)) >= V2_AUDIT_COLUMNS
