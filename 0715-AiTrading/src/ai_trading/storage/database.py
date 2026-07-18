import sqlite3

from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry

from ai_trading.storage.ledger_tables import LEDGER_TABLES
from ai_trading.storage.tables import Base

_V2_AUDIT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("reason", "TEXT"),
    ("strategy_version", "VARCHAR(32)"),
    ("target_weight_micros", "INTEGER"),
    ("reference_price_micros", "INTEGER"),
    ("stop_price_micros", "INTEGER"),
)


def create_sqlite_engine(database_url: str) -> Engine:
    if not database_url.startswith("sqlite"):
        raise ValueError("第一版持久化只允许 SQLite")
    engine = create_engine(database_url)

    @event.listens_for(engine, "connect")
    def configure_connection(
        dbapi_connection: sqlite3.Connection,
        _: ConnectionPoolEntry,
    ) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()

    return engine


def create_schema(engine: Engine) -> None:
    if not LEDGER_TABLES:
        raise RuntimeError("账本表注册失败")
    Base.metadata.create_all(engine)
    _migrate_v2_audit_columns(engine)


def _migrate_v2_audit_columns(engine: Engine) -> None:
    """对既有本机 SQLite 做可恢复的仅增列迁移，历史值保持 NULL。"""

    table = "trade_proposals"
    if not inspect(engine).has_table(table):
        return

    for name, sql_type in _V2_AUDIT_COLUMNS:
        _add_column_if_missing(engine, table, name, sql_type)


def _add_column_if_missing(
    engine: Engine,
    table: str,
    name: str,
    sql_type: str,
) -> None:
    """独立提交单列迁移；并发迁移已抢先增列时视为成功。"""

    with engine.begin() as connection:
        if _has_column(connection, table, name):
            return
        try:
            connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")
        except OperationalError as error:
            if not _is_expected_duplicate_column(error, name) or not _has_column(
                connection, table, name
            ):
                raise


def _has_column(connection: Connection, table: str, name: str) -> bool:
    return name in {item["name"] for item in inspect(connection).get_columns(table)}


def _is_expected_duplicate_column(error: OperationalError, name: str) -> bool:
    expected = f"duplicate column name: {name}".casefold()
    return expected in str(error.orig).casefold()


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
