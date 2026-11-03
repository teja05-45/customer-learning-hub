"""Add evidence provenance and insight relationship metadata

Revision ID: b7d2f4a91c03
Revises: e5f6a7b8c9d0
Create Date: 2026-11-03

Evidence can now be derived from any feedback source, not only an interview, and
therefore carries a provenance snapshot of that source. The insight-evidence
association gains the researcher's rationale, an optional confidence judgement,
tags and an author, because a classification without a reason is not reviewable.

SQLite hazard, verified in ``backend/tests/test_migrations.py``:
adding a foreign key to ``evidence`` forces Alembic to rebuild that table. With
``PRAGMA foreign_keys=ON`` (which the application enables), SQLite runs an
implicit DELETE before dropping the old table, and its ``ON DELETE CASCADE``
children — ``insight_evidence`` and ``decision_evidence`` — are emptied. A naive
migration would therefore upgrade cleanly and silently destroy every
evidence-to-insight and evidence-to-decision link.

Both child tables are copied to temporary backups before the rebuild and
restored afterwards, in both directions. PostgreSQL does not need the workaround,
but running the same explicit copy keeps the migration reproducible on every
engine. No research row is deleted or rewritten by design.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7d2f4a91c03"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INSIGHT_LINK_BACKUP = "_clh_insight_evidence_backup"
DECISION_LINK_BACKUP = "_clh_decision_evidence_backup"

# Column lists are explicit so the restore works whatever the table's current
# shape is. Columns introduced by this revision are left to their defaults.
INSIGHT_LINK_COLUMNS = (
    "id, insight_id, evidence_id, role, note, created_at, "
    "rationale, confidence, tags, created_by_id, updated_at"
)
INSIGHT_LINK_COLUMNS_BEFORE = "id, insight_id, evidence_id, role, note, created_at"
DECISION_LINK_COLUMNS = "id, decision_id, evidence_id, role, note, created_at"


def _backup_child_tables() -> None:
    op.execute(f"DROP TABLE IF EXISTS {INSIGHT_LINK_BACKUP}")
    op.execute(f"DROP TABLE IF EXISTS {DECISION_LINK_BACKUP}")
    op.execute(f"CREATE TABLE {INSIGHT_LINK_BACKUP} AS SELECT * FROM insight_evidence")
    op.execute(f"CREATE TABLE {DECISION_LINK_BACKUP} AS SELECT * FROM decision_evidence")


def _restore_child_tables(insight_columns: str) -> None:
    # Clear first: whether or not the rebuild cascaded, the backup is the
    # authoritative copy and inserting twice would duplicate research links.
    op.execute("DELETE FROM insight_evidence")
    op.execute("DELETE FROM decision_evidence")
    op.execute(
        f"INSERT INTO insight_evidence ({insight_columns}) "
        f"SELECT {insight_columns} FROM {INSIGHT_LINK_BACKUP}"
    )
    op.execute(
        f"INSERT INTO decision_evidence ({DECISION_LINK_COLUMNS}) "
        f"SELECT {DECISION_LINK_COLUMNS} FROM {DECISION_LINK_BACKUP}"
    )
    op.execute(f"DROP TABLE {INSIGHT_LINK_BACKUP}")
    op.execute(f"DROP TABLE {DECISION_LINK_BACKUP}")


def upgrade() -> None:
    # Backup before any rebuild: the evidence rebuild below cascades.
    _backup_child_tables()

    with op.batch_alter_table("insight_evidence", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("rationale", sa.Text(), nullable=False, server_default=sa.text("''"))
        )
        batch_op.add_column(sa.Column("confidence", sa.String(length=16), nullable=True))
        batch_op.add_column(
            sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
        )
        batch_op.add_column(sa.Column("created_by_id", sa.String(length=36), nullable=True))
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )
        batch_op.create_foreign_key(
            "fk_insight_evidence_created_by_id",
            "users",
            ["created_by_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_insight_evidence_insight_role", ["insight_id", "role"], unique=False)

    with op.batch_alter_table("evidence", schema=None) as batch_op:
        batch_op.add_column(sa.Column("feedback_record_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("source_type", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("collection_method", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("research_depth", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("source_reference", sa.String(length=320), nullable=True))
        batch_op.add_column(sa.Column("verification_state", sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_evidence_feedback_record_id",
            "feedback_records",
            ["feedback_record_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_evidence_feedback_record_id", ["feedback_record_id"], unique=False)

    _restore_child_tables(INSIGHT_LINK_COLUMNS_BEFORE)


def downgrade() -> None:
    _backup_child_tables()

    with op.batch_alter_table("evidence", schema=None) as batch_op:
        batch_op.drop_index("ix_evidence_feedback_record_id")
        batch_op.drop_constraint("fk_evidence_feedback_record_id", type_="foreignkey")
        batch_op.drop_column("collected_at")
        batch_op.drop_column("verification_state")
        batch_op.drop_column("source_reference")
        batch_op.drop_column("research_depth")
        batch_op.drop_column("collection_method")
        batch_op.drop_column("source_type")
        batch_op.drop_column("feedback_record_id")

    with op.batch_alter_table("insight_evidence", schema=None) as batch_op:
        batch_op.drop_index("ix_insight_evidence_insight_role")
        batch_op.drop_constraint("fk_insight_evidence_created_by_id", type_="foreignkey")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_by_id")
        batch_op.drop_column("tags")
        batch_op.drop_column("confidence")
        batch_op.drop_column("rationale")

    _restore_child_tables(INSIGHT_LINK_COLUMNS_BEFORE)
