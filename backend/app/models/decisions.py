"""Insights, decisions, actions and the links that make evidence traceable."""

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import IdMixin, TimestampMixin, utcnow


class Insight(Base, IdMixin, TimestampMixin):
    __tablename__ = "insights"

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    interpretation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    research_question: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="low")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    limitations: Mapped[str] = mapped_column(Text, nullable=False, default="")
    segments: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_by_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    project: Mapped["ResearchProject | None"] = relationship()  # noqa: F821
    owner: Mapped["User | None"] = relationship(foreign_keys=[owner_id])  # noqa: F821
    evidence_links: Mapped[list["InsightEvidence"]] = relationship(
        back_populates="insight", cascade="all, delete-orphan"
    )
    decision_links: Mapped[list["DecisionInsight"]] = relationship(
        back_populates="insight", cascade="all, delete-orphan"
    )


class InsightEvidence(Base, IdMixin):
    __tablename__ = "insight_evidence"

    insight_id: Mapped[str] = mapped_column(ForeignKey("insights.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="supporting")
    note: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    insight: Mapped[Insight] = relationship(back_populates="evidence_links")
    evidence: Mapped["Evidence"] = relationship()  # noqa: F821

    __table_args__ = (UniqueConstraint("insight_id", "evidence_id", name="uq_insight_evidence"),)


class Decision(Base, IdMixin, TimestampMixin):
    __tablename__ = "decisions"

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    business_function: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    limitations: Mapped[str] = mapped_column(Text, nullable=False, default="")
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("research_projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decision_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="proposed", index=True)
    evidence_sufficient: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    project: Mapped["ResearchProject | None"] = relationship()  # noqa: F821
    owner: Mapped["User | None"] = relationship(foreign_keys=[owner_id])  # noqa: F821
    evidence_links: Mapped[list["DecisionEvidence"]] = relationship(
        back_populates="decision", cascade="all, delete-orphan"
    )
    insight_links: Mapped[list["DecisionInsight"]] = relationship(
        back_populates="decision", cascade="all, delete-orphan"
    )
    actions: Mapped[list["BusinessAction"]] = relationship(back_populates="decision")

    @property
    def has_evidence(self) -> bool:
        return bool(self.evidence_links) or bool(self.insight_links)

    __table_args__ = (Index("ix_decisions_status_date", "status", "decision_date"),)


class DecisionEvidence(Base, IdMixin):
    __tablename__ = "decision_evidence"

    decision_id: Mapped[str] = mapped_column(
        ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="supporting")
    note: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    decision: Mapped[Decision] = relationship(back_populates="evidence_links")
    evidence: Mapped["Evidence"] = relationship()  # noqa: F821

    __table_args__ = (UniqueConstraint("decision_id", "evidence_id", name="uq_decision_evidence"),)


class DecisionInsight(Base, IdMixin):
    __tablename__ = "decision_insights"

    decision_id: Mapped[str] = mapped_column(
        ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    insight_id: Mapped[str] = mapped_column(ForeignKey("insights.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    decision: Mapped[Decision] = relationship(back_populates="insight_links")
    insight: Mapped[Insight] = relationship(back_populates="decision_links")

    __table_args__ = (UniqueConstraint("decision_id", "insight_id", name="uq_decision_insight"),)


class BusinessAction(Base, IdMixin, TimestampMixin):
    __tablename__ = "actions"

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium", index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="not_started", index=True)
    decision_id: Mapped[str | None] = mapped_column(
        ForeignKey("decisions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    insight_id: Mapped[str | None] = mapped_column(
        ForeignKey("insights.id", ondelete="SET NULL"), nullable=True, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    decision: Mapped[Decision | None] = relationship(back_populates="actions")
    insight: Mapped[Insight | None] = relationship()
    owner: Mapped["User | None"] = relationship(foreign_keys=[owner_id])  # noqa: F821

    @property
    def is_overdue(self) -> bool:
        return bool(
            self.due_date
            and self.status not in ("completed",)
            and self.due_date < datetime.now().date()
        )


class OrganizationSetting(Base):
    """Single-row organisation configuration for the Settings screen."""

    __tablename__ = "organization_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="default")
    name: Mapped[str] = mapped_column(String(160), nullable=False, default="Everyday Goods")
    research_lead_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    recording_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retention_months: Mapped[int] = mapped_column(default=12, nullable=False)
    show_demo_banner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
