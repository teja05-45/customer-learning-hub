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


def init_db() -> None:
    """Create tables that do not exist yet (used when Alembic is not run).

    SQLite cannot add a column with create_all, so a small compatibility guard
    keeps an existing demo volume usable after the auth change. Managed
    deployments should run Alembic instead.
    """
    from app import models  # noqa: F401  (register metadata)

    Base.metadata.create_all(bind=engine)

    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            columns = {
                row[1] for row in connection.exec_driver_sql("PRAGMA table_info(users)")
            }
            if "password_hash" not in columns:
                connection.exec_driver_sql("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)")
