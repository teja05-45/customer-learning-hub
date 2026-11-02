"""Research project request/response schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import BusinessFunction, Priority, ProjectStatus, Segment
from app.schemas.common import ORMModel, Ref


class QuestionIn(BaseModel):
    text: str = Field(min_length=5, max_length=400)
    is_resolved: bool = False
    resolution_note: str = ""


class QuestionOut(ORMModel):
    id: str
    text: str
    order_index: int
    is_resolved: bool
    resolution_note: str

    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    objective: str = Field(min_length=10, max_length=4000)
    description: str = Field(default="", max_length=8000)
    status: ProjectStatus = ProjectStatus.DRAFT
    priority: Priority = Priority.MEDIUM
    methodology: str = Field(default="", max_length=80)
    owner_id: Optional[str] = None
    business_functions: list[BusinessFunction] = Field(default_factory=list)
    target_segments: list[Segment] = Field(default_factory=list)
    start_date: Optional[date] = None
    deadline: Optional[date] = None

    @model_validator(mode="after")
    def _dates_ordered(self):
        if self.start_date and self.deadline and self.deadline < self.start_date:
            raise ValueError("Deadline cannot be before the start date")
        return self


class ProjectCreate(ProjectBase):
    questions: list[QuestionIn] = Field(default_factory=list, max_length=20)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=3, max_length=200)
    objective: Optional[str] = Field(default=None, min_length=10, max_length=4000)
    description: Optional[str] = Field(default=None, max_length=8000)
    status: Optional[ProjectStatus] = None
    priority: Optional[Priority] = None
    methodology: Optional[str] = Field(default=None, max_length=80)
    owner_id: Optional[str] = None
    business_functions: Optional[list[BusinessFunction]] = None
    target_segments: Optional[list[Segment]] = None
    start_date: Optional[date] = None
    deadline: Optional[date] = None


class ProjectCounts(BaseModel):
    participants: int = 0
    interviews: int = 0
    interviews_completed: int = 0
    evidence: int = 0
    insights: int = 0
    decisions: int = 0
    open_actions: int = 0


class ProjectOut(ORMModel):
    id: str
    name: str
    objective: str
    description: str
    status: ProjectStatus
    priority: Priority
    methodology: str
    owner_id: Optional[str]
    business_functions: list[str]
    target_segments: list[str]
    start_date: Optional[date]
    deadline: Optional[date]
    archived_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ProjectSummary(ProjectOut):
    owner: Optional[Ref] = None
    counts: ProjectCounts = Field(default_factory=ProjectCounts)
    unresolved_questions: int = 0
    segment_gap: bool = False


class ProjectDetail(ProjectSummary):
    questions: list[QuestionOut] = Field(default_factory=list)


class ProjectTemplate(BaseModel):
    key: str
    name: str
    description: str
    objective: str
    methodology: str
    priority: Priority
    business_functions: list[BusinessFunction]
    target_segments: list[Segment]
    questions: list[str]


class ProjectListResponse(BaseModel):
    items: list[ProjectSummary]
    total: int
    page: int
    page_size: int
    pages: int
