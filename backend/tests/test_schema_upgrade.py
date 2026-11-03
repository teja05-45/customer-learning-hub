"""The unmanaged-database upgrade path must not strand an existing volume.

``create_all`` creates missing tables but never adds columns. A Docker volume
made by an earlier build therefore keeps the old shape, and starting the current
code against it failed at the first insert ("table evidence has no column named
feedback_record_id"). This test reproduces that database and proves the
compatibility guard adds the columns without losing a row.
"""

from sqlalchemy import create_engine

from app.core.database import ensure_sqlite_columns


def _legacy_database(path):
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE evidence ("
            "id VARCHAR(36) PRIMARY KEY, code VARCHAR(16), project_id VARCHAR(36), "
            "evidence_type VARCHAR(32), content TEXT, interpretation TEXT, "
            "customer_context TEXT, segment VARCHAR(32), provenance VARCHAR(320), "
            "provenance_status VARCHAR(16), confidence VARCHAR(16), review_status VARCHAR(16), "
            "captured_at DATETIME)"
        )
        connection.exec_driver_sql(
            "INSERT INTO evidence (id, code, content, captured_at) "
            "VALUES ('ev-1', 'EV-0001', 'The original customer words.', '2026-10-01 09:00:00')"
        )
        connection.exec_driver_sql(
            "CREATE TABLE insight_evidence ("
            "id VARCHAR(36) PRIMARY KEY, insight_id VARCHAR(36), evidence_id VARCHAR(36), "
            "role VARCHAR(16), note VARCHAR(240), created_at DATETIME)"
        )
        connection.exec_driver_sql(
            "INSERT INTO insight_evidence "
            "(id, insight_id, evidence_id, role, note, created_at) "
            "VALUES ('link-1', 'in-1', 'ev-1', 'contextual', '', '2026-10-02 09:00:00')"
        )
    return engine


def test_existing_volume_gains_traceability_columns(tmp_path):
    engine = _legacy_database(tmp_path / "legacy.db")

    with engine.begin() as connection:
        added = ensure_sqlite_columns(connection)

    assert "evidence.feedback_record_id" in added
    assert "evidence.source_type" in added
    assert "insight_evidence.rationale" in added
    assert "insight_evidence.updated_at" in added

    # Running it again is a no-op, not an error.
    with engine.begin() as connection:
        assert ensure_sqlite_columns(connection) == []

    with engine.connect() as connection:
        statement = connection.exec_driver_sql(
            "SELECT content FROM evidence WHERE id = 'ev-1'"
        ).scalar_one()
        link = connection.exec_driver_sql(
            "SELECT role, rationale, updated_at, created_at FROM insight_evidence "
            "WHERE id = 'link-1'"
        ).one()

    assert statement == "The original customer words."
    assert link.role == "contextual"
    assert link.rationale == ""
    assert link.updated_at == link.created_at
