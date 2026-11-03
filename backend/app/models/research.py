"""Research projects, interview workspaces and captured evidence."""

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin, utcnow


class ResearchProject(Base, IdMixin, TimestampMixin):
    __tablename__ = "research_projects"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft", index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", index=True)
    methodology: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    business_functions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    target_segments: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped["User | None"] = relationship(back_populates="projects_owned", foreign_keys=[owner_id])  # noqa: F821
    questions: Mapped[list["ResearchQuestion"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ResearchQuestion.order_index",
    )
    recruitment_records: Mapped[list["RecruitmentRecord"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    interviews: Mapped[list["Interview"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_projects_status_deadline", "status", "deadline"),)


class ResearchQuestion(Base, IdMixin):
    __tablename__ = "research_questions"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(String(400), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolution_note: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project: Mapped[ResearchProject] = relationship(back_populates="questions")


class Interview(Base, IdMixin, TimestampMixin):
    __tablename__ = "interviews"

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recruitment_id: Mapped[str | None] = mapped_column(
        ForeignKey("recruitment_records.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False, default="")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    interviewer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="planned", index=True)
    channel: Mapped[str] = mapped_column(String(80), nullable=False, default="Video call (simulated)")
    consent_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    recording_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    follow_up_questions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[ResearchProject] = relationship(back_populates="interviews")
    participant: Mapped["Participant"] = relationship()  # noqa: F821
    interviewer: Mapped["User | None"] = relationship(foreign_keys=[interviewer_id])  # noqa: F821
    guide: Mapped[list["InterviewGuideQuestion"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="InterviewGuideQuestion.order_index",
    )
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="interview")
    consent_records: Mapped[list["ConsentRecord"]] = relationship(
        back_populates="interview", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_interviews_project_status", "project_id", "status"),)


class InterviewGuideQuestion(Base, IdMixin):
    __tablename__ = "interview_guide_questions"

    interview_id: Mapped[str] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(String(400), nullable=False)
    purpose: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_leading: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    interview: Mapped[Interview] = relationship(back_populates="guide")


class ConsentRecord(Base, IdMixin):
    """Consent is recorded separately from the interview so it can be audited."""

    __tablename__ = "consent_records"

    interview_id: Mapped[str | None] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), nullable=True, index=True
    )
    participant_id: Mapped[str] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    recorded_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    note: Mapped[str] = mapped_column(String(320), nullable=False, default="")

    interview: Mapped[Interview | None] = relationship(back_populates="consent_records")
    recorded_by: Mapped["User | None"] = relationship()  # noqa: F821


class Evidence(Base, IdMixin):
    """The atom of the product: customer words, kept with their provenance."""

    __tablename__ = "evidence"

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    interview_id: Mapped[str | None] = mapped_column(
        ForeignKey("interviews.id", ondelete="CASCADE"), nullable=True, index=True
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    participant_id: Mapped[str | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    interpretation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    customer_context: Mapped[str] = mapped_column(Text, nullable=False, default="")
    segment: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown", index=True)
    provenance: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    provenance_status: Mapped[str] = mapped_column(String(16), nullable=False, default="recorded")
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="unreviewed")
    captured_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project: Mapped[ResearchProject] = relationship(back_populates="evidence")
    interview: Mapped[Interview | None] = relationship(back_populates="evidence")
    participant: Mapped["Participant | None"] = relationship()  # noqa: F821
    captured_by: Mapped["User | None"] = relationship()  # noqa: F821

    @property
    def is_verified_source(self) -> bool:
        return self.provenance_status == "recorded" and bool(self.provenance.strip())


class FeedbackRecord(Base, IdMixin, TimestampMixin):
    """A unified feedback source.

    Covers synchronous interviews, asynchronous written feedback and imported
    support/review material. ``content`` is always the original customer words;
    ``interpretation`` is the researcher's reading and is never merged into it.
    A record may be unattributed, but it is then labelled as such everywhere.
    """

    __tablename__ = "feedback_records"

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    participant_id: Mapped[str | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    interview_id: Mapped[str | None] = mapped_column(
        ForeignKey("interviews.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    collection_method: Mapped[str] = mapped_column(String(32), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    contributor: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    interpretation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    context: Mapped[str] = mapped_column(Text, nullable=False, default="")
    verification_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="unverified", index=True
    )
    created_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    project: Mapped[ResearchProject] = relationship()
    participant: Mapped["Participant | None"] = relationship()  # noqa: F821
    interview: Mapped[Interview | None] = relationship()
    created_by: Mapped["User | None"] = relationship()  # noqa: F821

    __table_args__ = (Index("ix_feedback_project_source", "project_id", "source_type"),)
