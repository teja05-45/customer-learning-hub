"""Database engine, session factory and FastAPI dependency."""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def _build_engine() -> Engine:
    url = settings.database_url
    kwargs: dict = {"future": True, "pool_pre_ping": True}

    if url.startswith("sqlite"):
        # SQLite needs check_same_thread disabled for the threaded TestClient
        # and a shared in-memory connection when used by the test suite.
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url:
            kwargs["poolclass"] = StaticPool
        else:
            db_path = url.split("sqlite:///")[-1]
            if db_path:
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, **kwargs)


engine = _build_engine()


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # noqa: ANN001
    """Enable foreign keys so constraints actually bite on SQLite."""
    if engine.dialect.name == "sqlite":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Columns added after a database may already exist. ``create_all`` only creates
# missing tables, so a volume made by an earlier build keeps its old shape. The
# application needs these columns to start, and refusing to start would leave an
# existing demo database unusable. Each entry is (column, SQLite type).
SQLITE_COMPAT_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "evidence": [
        ("feedback_record_id", "VARCHAR(36)"),
        ("source_type", "VARCHAR(32)"),
        ("collection_method", "VARCHAR(32)"),
        ("research_depth", "VARCHAR(16)"),
        ("source_reference", "VARCHAR(320)"),
        ("verification_state", "VARCHAR(24)"),
        ("collected_at", "DATETIME"),
    ],
    "insight_evidence": [
        ("rationale", "TEXT NOT NULL DEFAULT ''"),
        ("confidence", "VARCHAR(16)"),
        ("tags", "JSON NOT NULL DEFAULT '[]'"),
        ("created_by_id", "VARCHAR(36)"),
        # Nullable so the column can be added by ALTER TABLE (SQLite rejects a
        # non-constant default there); the backfill below fills existing rows.
        ("updated_at", "DATETIME"),
    ],
}


def ensure_sqlite_columns(connection) -> list[str]:  # noqa: ANN001 - SQLAlchemy Connection
    """Bring an existing SQLite database up to the columns the code expects.

    This is the unmanaged-database path (docker compose, local development with
    ``create_all``). Alembic remains the migration mechanism, and it also adds
    the foreign keys, which SQLite cannot add to an existing table. Returns the
    list of columns that were added, so a caller or test can see what changed.
    """
    added: list[str] = []
    for table, columns in SQLITE_COMPAT_COLUMNS.items():
        existing = {
            row[1] for row in connection.exec_driver_sql(f"PRAGMA table_info({table})")
        }
        if not existing:
            continue
        for name, ddl in columns:
            if name in existing:
                continue
            connection.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
            added.append(f"{table}.{name}")

    if {"insight_evidence.updated_at"} & set(added):
        # Old links keep a truthful timestamp instead of reading as NULL.
        connection.exec_driver_sql(
            "UPDATE insight_evidence SET updated_at = created_at WHERE updated_at IS NULL"
        )
    return added


def init_db() -> None:
    """Create tables that do not exist yet (used when Alembic is not run).

    SQLite cannot add a column with create_all, so a small compatibility guard
    keeps an existing demo volume usable after the auth and traceability changes.
    Managed deployments should run Alembic instead.
    """
    from app import models  # noqa: F401  (register metadata)

    Base.metadata.create_all(bind=engine)

    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            # Authentication columns (older volumes predate password login).
            columns = {
                row[1] for row in connection.exec_driver_sql("PRAGMA table_info(users)")
            }
            if "password_hash" not in columns:
                connection.exec_driver_sql("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)")
            # Traceability columns (older volumes predate feedback-derived evidence).
            ensure_sqlite_columns(connection)
