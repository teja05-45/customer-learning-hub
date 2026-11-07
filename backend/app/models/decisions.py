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
from app.models.base import IdMixin, TimestampMixin, new_id, utcnow


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
    """Explicit association entity between one insight and one evidence item.

    The classification lives here, not on the evidence: the same quote can
    support one finding, contradict another and merely add context to a third.
    Every row carries the researcher's rationale and the author, because a
    classification without a reason is an assertion nobody can review later.
    """

    __tablename__ = "insight_evidence"

    insight_id: Mapped[str] = mapped_column(ForeignKey("insights.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="supporting")
    note: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    # Why the researcher judged this relationship the way they did. Free text,
    # never generated from the customer statement. Confidence is an explicit
    # researcher judgement, not a probability.
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    insight: Mapped[Insight] = relationship(back_populates="evidence_links")
    evidence: Mapped["Evidence"] = relationship()  # noqa: F821
    created_by: Mapped["User | None"] = relationship()  # noqa: F821

    __table_args__ = (
        UniqueConstraint("insight_id", "evidence_id", name="uq_insight_evidence"),
        Index("ix_insight_evidence_insight_role", "insight_id", "role"),
    )


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
    outcomes: Mapped[list["Outcome"]] = relationship(
        back_populates="decision", cascade="all, delete-orphan"
    )

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


class Outcome(Base, IdMixin, TimestampMixin):
    """The measured result of a decision, kept separate from the decision itself.

    A decision records what the team chose to do. An outcome records what was
    expected to change, how it would be measured, and what actually happened.
    Storing the expectation and the result in the same append-only history is
    what stops a team from rewriting the target after the fact.
    """

    __tablename__ = "outcomes"

    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    decision_id: Mapped[str] = mapped_column(
        ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_id: Mapped[str | None] = mapped_column(
        ForeignKey("actions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    metric_definition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    baseline_value: Mapped[float | None] = mapped_column(nullable=True)
    target_value: Mapped[float | None] = mapped_column(nullable=True)
    actual_value: Mapped[float | None] = mapped_column(nullable=True)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="increase")
    measurement_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    measurement_end: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="planned", index=True)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    data_source: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    decision: Mapped["Decision"] = relationship(back_populates="outcomes")
    action: Mapped["BusinessAction | None"] = relationship()
    owner: Mapped["User | None"] = relationship(foreign_keys=[owner_id])  # noqa: F821

    __table_args__ = (Index("ix_outcomes_decision_status", "decision_id", "status"),)


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
