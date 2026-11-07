"""Add outcome measurement

Revision ID: c8e3a1d5f204
Revises: b7d2f4a91c03
Create Date: 2026-11-06

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8e3a1d5f204"
down_revision: Union[str, None] = "b7d2f4a91c03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "outcomes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("decision_id", sa.String(length=36), nullable=False),
        sa.Column("action_id", sa.String(length=36), nullable=True),
        sa.Column("metric_definition", sa.Text(), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=True),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("actual_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("measurement_start", sa.Date(), nullable=True),
        sa.Column("measurement_end", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=True),
        sa.Column("data_source", sa.String(length=240), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["action_id"], ["actions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_outcomes_code", "outcomes", ["code"])
    op.create_index("ix_outcomes_decision_id", "outcomes", ["decision_id"])
    op.create_index("ix_outcomes_action_id", "outcomes", ["action_id"])
    op.create_index("ix_outcomes_measurement_end", "outcomes", ["measurement_end"])
    op.create_index("ix_outcomes_status", "outcomes", ["status"])
    op.create_index("ix_outcomes_decision_status", "outcomes", ["decision_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_outcomes_decision_status", table_name="outcomes")
    op.drop_index("ix_outcomes_status", table_name="outcomes")
    op.drop_index("ix_outcomes_measurement_end", table_name="outcomes")
    op.drop_index("ix_outcomes_action_id", table_name="outcomes")
    op.drop_index("ix_outcomes_decision_id", table_name="outcomes")
    op.drop_index("ix_outcomes_code", table_name="outcomes")
    op.drop_table("outcomes")
