"""Dashboard, search, analytics and settings schemas."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, Ref
from app.schemas.decision import ActionOut, DecisionSummary
from app.schemas.insight import InsightSummary
from app.schemas.interview import InterviewSummary
from app.schemas.project import ProjectSummary


class MetricValue(BaseModel):
    label: str
    value: float
    display: str
    denominator: Optional[str] = None
    definition: str


class ResponseRate(BaseModel):
    value: Optional[float]
    display: str
    numerator: int
    denominator: int
    definition: str
    sample_warning: Optional[str] = None


class LearningSignals(BaseModel):
    findings_with_evidence: int
    findings_total: int
    findings_coverage_display: str
    decisions_supported: int
    decisions_total: int
    insights_reused: int
    insights_reuse_display: str
    unresolved_questions: int
    overdue_actions: int
    unevidenced_decisions: int


class TimelinePoint(BaseModel):
    month: str
    label: str
    interviews: int
    evidence: int
    insights: int


class SegmentPoint(BaseModel):
    segment: str
    participants: int
    interviews: int
    evidence: int


class StatusCount(BaseModel):
    status: str
    count: int


class ActivityItem(BaseModel):
    id: str
    entity_type: str
    entity_id: Optional[str]
    entity_label: str
    summary: str
    verb: str
    actor: Optional[Ref] = None
    created_at: datetime
    project_id: Optional[str] = None


class DashboardResponse(BaseModel):
    generated_at: datetime
    active_projects: int
    interviews_completed: int
    interviews_upcoming: int
    participants_contacted: int
    response_rate: ResponseRate
    insights_awaiting_review: int
    decisions_with_evidence: int
    decisions_total: int
    open_actions: int
    overdue_actions: int
    learning: LearningSignals
    timeline: list[TimelinePoint]
    segments: list[SegmentPoint]
    decision_status: list[StatusCount]
    action_status: list[StatusCount]
    recent_insights: list[InsightSummary]
    upcoming_interviews: list[InterviewSummary]
    recent_activity: list[ActivityItem]
    outstanding_actions: list[ActionOut]
    projects: list[ProjectSummary]
    data_note: str


class SearchResult(BaseModel):
    id: str
    entity_type: Literal["project", "participant", "interview", "evidence", "insight", "decision", "action"]
    title: str
    subtitle: str
    snippet: str
    href: str
    badges: list[str] = Field(default_factory=list)
    project_id: Optional[str] = None


class SearchGroup(BaseModel):
    entity_type: str
    label: str
    items: list[SearchResult]


class SearchResponse(BaseModel):
    query: str
    total: int
    groups: list[SearchGroup]
    suggestions: list[SearchResult] = Field(default_factory=list)
    suggestion_reason: Optional[str] = None
    contacts_excluded_note: str = (
        "Participant contact details are never stored in this system, so they cannot appear in search results."
    )


class AnalyticsMetric(BaseModel):
    key: str
    label: str
    display: str
    basis: Literal["observed", "calculated", "illustrative", "pending_baseline"]
    definition: str
    note: Optional[str] = None
    target: Optional[str] = None


class MeasurementGap(BaseModel):
    key: str
    label: str
    why: str
    how_to_collect: str


class AnalyticsResponse(BaseModel):
    generated_at: datetime
    metrics: list[AnalyticsMetric]
    segment_distribution: list[SegmentPoint]
    decision_funnel: list[StatusCount]
    action_completion: list[StatusCount]
    unresolved_questions: list[dict]
    reuse_detail: list[dict]
    measurement_gaps: list[MeasurementGap]
    honesty_note: str


class OrgSettingsOut(ORMModel):
    id: str
    name: str
    recording_default: bool
    retention_months: int
    show_demo_banner: bool
    updated_at: datetime


class OrgSettingsUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    research_lead_id: Optional[str] = None
    recording_default: Optional[bool] = None
    retention_months: Optional[int] = Field(default=None, ge=1, le=120)
    show_demo_banner: Optional[bool] = None


class DemoUser(BaseModel):
    id: str
    name: str
    role: str
    job_title: str
    initials: str
    can_view: list[str]
    description: str


class SessionResponse(BaseModel):
    demo_mode: bool
    current_user: Optional[DemoUser] = None
    users: list[DemoUser]
    notice: str


class ResetResponse(BaseModel):
    message: str
    counts: dict[str, int]


class ResetRequest(BaseModel):
    confirm: bool = Field(description="Must be true. Reseeds synthetic data and discards changes.")
    phrase: str = Field(description="Type RESET to confirm the destructive demo action")


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    demo_mode: bool
    seeded: bool
    checked_at: datetime
