"""Participant directory and recruitment pipeline schemas."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Eligibility, RecruitmentStage, Segment
from app.schemas.common import ORMModel, Ref


class ParticipantBase(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    segment: Segment
    purchase_frequency: str = Field(default="", max_length=64)
    orders_count: int = Field(default=1, ge=0, le=500)
    last_purchase_at: Optional[date] = None
    product_category: str = Field(default="", max_length=64)
    eligibility: Eligibility = Eligibility.ELIGIBLE
    eligibility_note: str = Field(default="", max_length=240)
    contact_route: Optional[str] = Field(default=None, max_length=160)
    notes: str = Field(default="", max_length=4000)


class ParticipantCreate(ParticipantBase):
    """No contact details are accepted here by design (data minimisation)."""


class ParticipantUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    segment: Optional[Segment] = None
    purchase_frequency: Optional[str] = Field(default=None, max_length=64)
    orders_count: Optional[int] = Field(default=None, ge=0, le=500)
    last_purchase_at: Optional[date] = None
    product_category: Optional[str] = Field(default=None, max_length=64)
    eligibility: Optional[Eligibility] = None
    eligibility_note: Optional[str] = Field(default=None, max_length=240)
    contact_route: Optional[str] = Field(default=None, max_length=160)
    notes: Optional[str] = Field(default=None, max_length=4000)


class ParticipantOut(ORMModel):
    id: str
    code: str
    display_name: str
    segment: Segment
    purchase_frequency: str
    orders_count: int
    last_purchase_at: Optional[date]
    product_category: str
    eligibility: Eligibility
    eligibility_note: str
    contact_route: Optional[str]
    contact_consent: str
    notes: str
    is_synthetic: bool
    last_research_contact_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ParticipationHistoryItem(BaseModel):
    interview_id: Optional[str]
    interview_code: Optional[str]
    project_id: str
    project_name: str
    status: str
    scheduled_at: Optional[datetime]
    evidence_count: int
    insight_count: int


class ParticipantDetail(ParticipantOut):
    recruitment: list["RecruitmentOut"] = Field(default_factory=list)
    participation_history: list[ParticipationHistoryItem] = Field(default_factory=list)
    evidence_count: int = 0


class ParticipantListResponse(BaseModel):
    items: list[ParticipantOut]
    total: int
    page: int
    page_size: int
    pages: int
    segment_counts: dict[str, int] = Field(default_factory=dict)


class RecruitmentCreate(BaseModel):
    project_id: str
    participant_ids: list[str] = Field(min_length=1, max_length=50)
    next_action: str = Field(default="Send invitation through the controlled Ops process", max_length=240)
    note: str = Field(default="", max_length=240)


class RecruitmentUpdate(BaseModel):
    stage: Optional[RecruitmentStage] = None
    next_action: Optional[str] = Field(default=None, max_length=240)
    notes: Optional[str] = Field(default=None, max_length=4000)
    note: str = Field(default="", max_length=240)


class RecruitmentEventOut(ORMModel):
    id: str
    from_stage: Optional[str]
    to_stage: str
    note: str
    created_at: datetime
    actor: Optional[Ref] = None

    model_config = ConfigDict(from_attributes=True)


class RecruitmentOut(ORMModel):
    id: str
    project_id: str
    participant_id: str
    stage: RecruitmentStage
    next_action: str
    notes: str
    invited_at: Optional[datetime]
    responded_at: Optional[datetime]
    scheduled_at: Optional[datetime]
    updated_at: datetime
    participant: Optional[ParticipantOut] = None
    project: Optional[Ref] = None
    updated_by: Optional[Ref] = None
    days_in_stage: Optional[int] = None
    events: list[RecruitmentEventOut] = Field(default_factory=list)


class RecruitmentListResponse(BaseModel):
    items: list[RecruitmentOut]
    total: int
    stage_counts: dict[str, int] = Field(default_factory=dict)
    segment_coverage: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ParticipantAssignResult(BaseModel):
    created: list[RecruitmentOut]
    skipped: list[dict] = Field(default_factory=list)


ParticipantDetail.model_rebuild()
