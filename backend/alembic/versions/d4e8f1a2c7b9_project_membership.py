"""Add project-level membership

Revision ID: d4e8f1a2c7b9
Revises: c8e3a1d5f204
Create Date: 2026-11-07

Backfill strategy (deterministic, least privilege):

1. The owner of a project becomes ``project_owner``.
2. Every active workspace administrator becomes ``project_owner`` on every
   project. Administrators run the workspace; this also guarantees no existing
   administrator is locked out by the new boundary.
3. Any user with a direct contribution to a project becomes ``editor`` on that
   project only: interview interviewer, evidence capturer, feedback creator, or
   the owner of an insight, decision or outcome. This is the demonstrable "this
   person already worked on this study" set.
4. Nobody else is granted anything. Users who previously relied on
   workspace-wide read access must be granted membership by a project owner.

Deliberately *not* done: granting every existing user access to every project.
That would leave the vulnerability in place under a new table name.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e8f1a2c7b9"
down_revision: Union[str, None] = "c8e3a1d5f204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _insert_memberships(bind, rows) -> None:
    """Insert (project_id, user_id, role) triples, skipping duplicates."""
    seen: set[tuple[str, str]] = set()
    payload = []
    for project_id, user_id, role in rows:
        if not project_id or not user_id:
            continue
        key = (project_id, user_id)
        if key in seen:
            continue
        seen.add(key)
        payload.append(
            {
                "id": str(__import__("uuid").uuid4()),
                "project_id": project_id,
                "user_id": user_id,
                "role": role,
            }
        )
    if payload:
        bind.execute(
            sa.text(
                "INSERT INTO project_memberships (id, project_id, user_id, role, created_at) "
                "VALUES (:id, :project_id, :user_id, :role, CURRENT_TIMESTAMP)"
            ),
            payload,
        )


def upgrade() -> None:
    op.create_table(
        "project_memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("granted_by_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["research_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_membership"),
    )
    op.create_index(
        "ix_project_memberships_project_id", "project_memberships", ["project_id"], unique=False
    )
    op.create_index("ix_project_memberships_user_id", "project_memberships", ["user_id"], unique=False)
    op.create_index(
        "ix_project_memberships_user_project",
        "project_memberships",
        ["user_id", "project_id"],
        unique=False,
    )

    bind = op.get_bind()

    # 1. Project owners.
    rows = [
        (row.project_id, row.owner_id, "project_owner")
        for row in bind.execute(
            sa.text("SELECT id AS project_id, owner_id FROM research_projects WHERE owner_id IS NOT NULL")
        )
    ]
    # 2. Workspace administrators, on every project.
    admin_ids = [
        row.id
        for row in bind.execute(sa.text("SELECT id FROM users WHERE role = 'admin' AND is_active = 1"))
    ]
    project_ids = [row.id for row in bind.execute(sa.text("SELECT id FROM research_projects"))]
    rows.extend((project_id, admin_id, "project_owner") for project_id in project_ids for admin_id in admin_ids)

    # 3. Demonstrable contributors, as editors.
    contributor_queries = (
        "SELECT project_id, interviewer_id AS user_id FROM interviews WHERE interviewer_id IS NOT NULL",
        "SELECT project_id, captured_by_id AS user_id FROM evidence WHERE captured_by_id IS NOT NULL",
        "SELECT project_id, created_by_id AS user_id FROM feedback_records WHERE created_by_id IS NOT NULL",
        "SELECT project_id, owner_id AS user_id FROM insights WHERE project_id IS NOT NULL AND owner_id IS NOT NULL",
        "SELECT project_id, owner_id AS user_id FROM decisions WHERE project_id IS NOT NULL AND owner_id IS NOT NULL",
        "SELECT d.project_id AS project_id, o.owner_id AS user_id FROM outcomes o "
        "JOIN decisions d ON d.id = o.decision_id WHERE o.owner_id IS NOT NULL",
    )
    for query in contributor_queries:
        rows.extend(
            (row.project_id, row.user_id, "editor")
            for row in bind.execute(sa.text(query))
            if row.project_id and row.user_id
        )

    _insert_memberships(bind, rows)


def downgrade() -> None:
    op.drop_index("ix_project_memberships_user_project", table_name="project_memberships")
    op.drop_index("ix_project_memberships_user_id", table_name="project_memberships")
    op.drop_index("ix_project_memberships_project_id", table_name="project_memberships")
    op.drop_table("project_memberships")
