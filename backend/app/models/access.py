"""Project-level access control.

The original delivery authenticated users and enforced a coarse write policy by
workspace role, but every authenticated user could read every project. That made
project ids the only thing standing between a viewer and another team's customer
research. ``ProjectMembership`` closes that gap: access to a project is an
explicit grant, not a side effect of having signed in.

Workspace administrators keep an implicit owner role on every project (they run
the workspace). Everyone else needs a row here.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, utcnow


class ProjectMembership(Base, IdMixin):
    __tablename__ = "project_memberships"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # viewer < editor < project_owner. Stored as text so adding a role never
    # requires rewriting the table.
    role: Mapped[str] = mapped_column(String(24), nullable=False, default="viewer")
    created_at: Mapped[datetime] = mapped_column(default=utcnow, nullable=False)
    granted_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    project: Mapped["ResearchProject"] = relationship()  # noqa: F821
    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821
    granted_by: Mapped["User | None"] = relationship(foreign_keys=[granted_by_id])  # noqa: F821

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_membership"),
        Index("ix_project_memberships_user_project", "user_id", "project_id"),
    )
