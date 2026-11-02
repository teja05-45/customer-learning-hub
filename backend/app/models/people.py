"""Users (internal team) and participants (synthetic customers)."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin, new_id, utcnow


class User(Base, IdMixin, TimestampMixin):
    """Internal team member.

    This is a *demonstration* identity record. It holds no password, hash or
    session token: the prototype has no authentication (see docs/auth.md).
    """

    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    job_title: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    initials: Mapped[str] = mapped_column(String(4), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Nullable so legacy demo rows and SSO-only users can exist; password login
    # simply fails for them rather than locking the account model.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    projects_owned: Mapped[list["ResearchProject"]] = relationship(  # noqa: F821
        back_populates="owner", foreign_keys="ResearchProject.owner_id"
    )


class AuthSession(Base):
    """Server-side session. Only a digest of the cookie token is stored."""

    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    user_agent: Mapped[str] = mapped_column(String(200), nullable=False, default="")

    user: Mapped[User] = relationship(foreign_keys=[user_id])


class Participant(Base, IdMixin, TimestampMixin):
    """A synthetic research participant.

    Deliberately stores **no** email address, phone number or address. The
    ``contact_route`` field records *how* a controlled Ops process would reach
    the person, never the contact values themselves.
    """

    __tablename__ = "participants"

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    segment: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    purchase_frequency: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_purchase_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    product_category: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    eligibility: Mapped[str] = mapped_column(String(24), nullable=False, default="eligible", index=True)
    eligibility_note: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    contact_route: Mapped[str | None] = mapped_column(String(160), nullable=True)
    contact_consent: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_research_contact_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    recruitment_records: Mapped[list["RecruitmentRecord"]] = relationship(  # noqa: F821
        back_populates="participant", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_participants_segment_eligibility", "segment", "eligibility"),)


class RecruitmentRecord(Base, IdMixin, TimestampMixin):
    __tablename__ = "recruitment_records"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[str] = mapped_column(String(24), nullable=False, default="identified", index=True)
    next_action: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    participant: Mapped[Participant] = relationship(back_populates="recruitment_records")
    project: Mapped["ResearchProject"] = relationship(back_populates="recruitment_records")  # noqa: F821
    updated_by: Mapped[User | None] = relationship(foreign_keys=[updated_by_id])
    events: Mapped[list["RecruitmentEvent"]] = relationship(
        back_populates="recruitment", cascade="all, delete-orphan", order_by="desc(RecruitmentEvent.created_at)"
    )


class RecruitmentEvent(Base, IdMixin):
    """Append-only timeline for a recruitment record."""

    __tablename__ = "recruitment_events"

    recruitment_id: Mapped[str] = mapped_column(
        ForeignKey("recruitment_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_stage: Mapped[str | None] = mapped_column(String(24), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(24), nullable=False)
    note: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    recruitment: Mapped[RecruitmentRecord] = relationship(back_populates="events")
    actor: Mapped[User | None] = relationship()


class ActivityLog(Base, IdMixin):
    """Cross-entity audit trail powering dashboards and project timelines."""

    __tablename__ = "activity_logs"

    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    entity_label: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    verb: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(String(320), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    actor: Mapped[User | None] = relationship()


def activity_event(
    *,
    entity_type: str,
    entity_id: str | None,
    entity_label: str,
    verb: str,
    summary: str,
    actor_id: str | None = None,
    project_id: str | None = None,
    created_at: datetime | None = None,
) -> ActivityLog:
    return ActivityLog(
        id=new_id(),
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=entity_label,
        verb=verb,
        summary=summary,
        actor_id=actor_id,
        project_id=project_id,
        created_at=created_at or utcnow(),
    )
