"""Add unified feedback sources

Revision ID: e5f6a7b8c9d0
Revises: a7c41d2f9b10
Create Date: 2026-11-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "a7c41d2f9b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("participant_id", sa.String(length=36), nullable=True),
        sa.Column("interview_id", sa.String(length=36), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("collection_method", sa.String(length=32), nullable=False),
        sa.Column("source_reference", sa.String(length=320), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contributor", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("interpretation", sa.Text(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("verification_status", sa.String(length=24), nullable=False),
        sa.Column("created_by_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["interview_id"], ["interviews.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_feedback_records_code", "feedback_records", ["code"])
    op.create_index("ix_feedback_records_project_id", "feedback_records", ["project_id"])
    op.create_index("ix_feedback_records_participant_id", "feedback_records", ["participant_id"])
    op.create_index("ix_feedback_records_interview_id", "feedback_records", ["interview_id"])
    op.create_index("ix_feedback_records_source_type", "feedback_records", ["source_type"])
    op.create_index("ix_feedback_records_collected_at", "feedback_records", ["collected_at"])
    op.create_index(
        "ix_feedback_records_verification_status", "feedback_records", ["verification_status"]
    )
    op.create_index(
        "ix_feedback_project_source", "feedback_records", ["project_id", "source_type"]
    )


def downgrade() -> None:
    op.drop_index("ix_feedback_project_source", table_name="feedback_records")
    op.drop_index("ix_feedback_records_verification_status", table_name="feedback_records")
    op.drop_index("ix_feedback_records_collected_at", table_name="feedback_records")
    op.drop_index("ix_feedback_records_source_type", table_name="feedback_records")
    op.drop_index("ix_feedback_records_interview_id", table_name="feedback_records")
    op.drop_index("ix_feedback_records_participant_id", table_name="feedback_records")
    op.drop_index("ix_feedback_records_project_id", table_name="feedback_records")
    op.drop_index("ix_feedback_records_code", table_name="feedback_records")
    op.drop_table("feedback_records")
