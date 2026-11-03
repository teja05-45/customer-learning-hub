"""Migration verification on an isolated database.

The traceability change adds columns to ``evidence`` and ``insight_evidence``.
An upgrade that only works on a fresh database is not a migration, so this test
builds a real SQLite file, moves it to head, back down to the previous revision,
and up again — asserting the columns appear and disappear and that existing rows
survive the round trip with their values intact.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "e5f6a7b8c9d0"


def _alembic(*args: str, database_url: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": database_url, "LOG_LEVEL": "WARNING"}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def _columns(db_path: Path, table: str) -> set[str]:
    connection = sqlite3.connect(db_path)
    try:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    finally:
        connection.close()


def _insert_fixture_rows(db_path: Path) -> None:
    """Parent rows are real so foreign keys stay valid across the rebuild."""
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "INSERT INTO research_projects "
            "(id, name, objective, description, status, priority, methodology, business_functions, "
            "target_segments, created_at, updated_at) "
            "VALUES ('proj-1', 'Migration project', 'Check the migration', '', 'draft', 'medium', '', "
            "'[]', '[]', '2026-11-03', '2026-11-03')"
        )
        connection.execute(
            "INSERT INTO insights "
            "(id, code, title, summary, interpretation, research_question, project_id, status, "
            "confidence, limitations, segments, created_at, updated_at) "
            "VALUES ('insight-1', 'INS-9001', 'Migration insight', 'Summary text long enough', '', '', "
            "'proj-1', 'draft', 'low', '', '[]', '2026-11-03', '2026-11-03')"
        )
        connection.execute(
            "INSERT INTO evidence "
            "(id, code, project_id, evidence_type, content, interpretation, customer_context, segment, "
            "provenance, provenance_status, confidence, review_status, captured_at) "
            "VALUES ('evidence-1', 'EV-9001', 'proj-1', 'verbatim_quote', 'Original words', '', '', "
            "'unknown', 'note 1', 'recorded', 'medium', 'unreviewed', '2026-11-03')"
        )
        connection.execute(
            "INSERT INTO insight_evidence "
            "(id, insight_id, evidence_id, role, note, rationale, tags, created_at, updated_at) "
            "VALUES ('link-1', 'insight-1', 'evidence-1', 'contextual', '', 'kept across migrations', "
            "'[]', '2026-11-03 10:00:00', '2026-11-03 10:00:00')"
        )
        connection.commit()
    finally:
        connection.close()


def test_traceability_migration_upgrades_and_downgrades(tmp_path):
    db_path = tmp_path / "migration.db"
    url = f"sqlite:///{db_path.as_posix()}"

    upgraded = _alembic("upgrade", "head", database_url=url)
    assert upgraded.returncode == 0, upgraded.stderr

    evidence_columns = _columns(db_path, "evidence")
    assert {
        "feedback_record_id",
        "source_type",
        "collection_method",
        "research_depth",
        "source_reference",
        "verification_state",
        "collected_at",
    } <= evidence_columns

    link_columns = _columns(db_path, "insight_evidence")
    assert {"rationale", "confidence", "tags", "created_by_id", "updated_at"} <= link_columns
    # Pre-existing columns must not be dropped by the table rebuild.
    assert {"insight_id", "evidence_id", "role", "note", "created_at"} <= link_columns

    _insert_fixture_rows(db_path)

    downgraded = _alembic("downgrade", PREVIOUS_REVISION, database_url=url)
    assert downgraded.returncode == 0, downgraded.stderr
    assert "feedback_record_id" not in _columns(db_path, "evidence")
    assert "rationale" not in _columns(db_path, "insight_evidence")
    assert {"insight_id", "evidence_id", "role", "created_at"} <= _columns(db_path, "insight_evidence")

    reupgraded = _alembic("upgrade", "head", database_url=url)
    assert reupgraded.returncode == 0, reupgraded.stderr
    assert "rationale" in _columns(db_path, "insight_evidence")

    connection = sqlite3.connect(db_path)
    try:
        survived = connection.execute(
            "SELECT role, insight_id, evidence_id, note FROM insight_evidence WHERE id = 'link-1'"
        ).fetchone()
        statement = connection.execute(
            "SELECT content FROM evidence WHERE id = 'evidence-1'"
        ).fetchone()
    finally:
        connection.close()
    assert survived == ("contextual", "insight-1", "evidence-1", "")
    assert statement == ("Original words",)
