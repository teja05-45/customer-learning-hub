"""Decision register and action tracking schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActionStatus, BusinessFunction, DecisionStatus, EvidenceRole, Priority
from app.schemas.common import ORMModel, Ref
from app.schemas.evidence import EvidenceOut
from app.schemas.insight import InsightSummary


class ActionBase(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(default="", max_length=4000)
    owner_id: Optional[str] = None
    due_date: Optional[date] = None
    priority: Priority = Priority.MEDIUM
    status: ActionStatus = ActionStatus.NOT_STARTED
    insight_id: Optional[str] = None


class ActionCreate(ActionBase):
    decision_id: Optional[str] = None


class ActionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=240)
    description: Optional[str] = Field(default=None, max_length=4000)
    owner_id: Optional[str] = None
    due_date: Optional[date] = None
    priority: Optional[Priority] = None
    status: Optional[ActionStatus] = None


class ActionOut(ORMModel):
    id: str
    code: str
    title: str
    description: str
    owner_id: Optional[str]
    due_date: Optional[date]
    priority: Priority
    status: ActionStatus
    decision_id: Optional[str]
    insight_id: Optional[str]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    owner: Optional[Ref] = None
    decision: Optional[Ref] = None
    insight: Optional[Ref] = None
    is_overdue: bool = False
    days_until_due: Optional[int] = None


class ActionListResponse(BaseModel):
    items: list[ActionOut]
    total: int
    status_counts: dict[str, int] = Field(default_factory=dict)
    overdue: int = 0


class DecisionCreate(BaseModel):
    title: str = Field(min_length=5, max_length=240)
    business_function: BusinessFunction
    problem_statement: str = Field(min_length=10, max_length=4000)
    description: str = Field(min_length=10, max_length=8000)
    rationale: str = Field(default="", max_length=4000)
    limitations: str = Field(default="", max_length=4000)
    project_id: Optional[str] = None
    owner_id: Optional[str] = None
    decision_date: Optional[date] = None
    status: DecisionStatus = DecisionStatus.PROPOSED
    evidence_sufficient: Optional[bool] = None
    insight_ids: list[str] = Field(default_factory=list, max_length=50)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)


class DecisionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=5, max_length=240)
    business_function: Optional[BusinessFunction] = None
    problem_statement: Optional[str] = Field(default=None, min_length=10, max_length=4000)
    description: Optional[str] = Field(default=None, min_length=10, max_length=8000)
    rationale: Optional[str] = Field(default=None, max_length=4000)
    limitations: Optional[str] = Field(default=None, max_length=4000)
    project_id: Optional[str] = None
    owner_id: Optional[str] = None
    decision_date: Optional[date] = None
    status: Optional[DecisionStatus] = None
    evidence_sufficient: Optional[bool] = None


class DecisionLinkIn(BaseModel):
    insight_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    role: EvidenceRole = EvidenceRole.SUPPORTING


class DecisionOut(ORMModel):
    id: str
    code: str
    title: str
    business_function: BusinessFunction
    problem_statement: str
    description: str
    rationale: str
    limitations: str
    project_id: Optional[str]
    owner_id: Optional[str]
    decision_date: Optional[date]
    status: DecisionStatus
    evidence_sufficient: Optional[bool]
    created_at: datetime
    updated_at: datetime


class DecisionSummary(DecisionOut):
    owner: Optional[Ref] = None
    project: Optional[Ref] = None
    insight_count: int = 0
    evidence_count: int = 0
    action_count: int = 0
    open_action_count: int = 0
    evidence_warning: Optional[str] = None
    contradicting_count: int = 0


class ActionRef(BaseModel):
    id: str
    code: str
    title: str
    status: ActionStatus
    owner: Optional[Ref] = None
    due_date: Optional[date] = None
    is_overdue: bool = False


class DecisionDetail(DecisionSummary):
    insights: list[InsightSummary] = Field(default_factory=list)
    evidence: list[EvidenceOut] = Field(default_factory=list)
    actions: list[ActionRef] = Field(default_factory=list)
    history: list["DecisionHistoryItem"] = Field(default_factory=list)


class DecisionHistoryItem(BaseModel):
    at: datetime
    summary: str
    actor: Optional[str] = None
    verb: str


class DecisionListResponse(BaseModel):
    items: list[DecisionSummary]
    total: int
    status_counts: dict[str, int] = Field(default_factory=dict)
    unevidenced: int = 0


DecisionDetail.model_rebuild()
