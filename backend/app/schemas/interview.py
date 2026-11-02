"""Interview workspace schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConsentStatus, ConsentType, InterviewStatus
from app.schemas.common import ORMModel, Ref
from app.schemas.participant import ParticipantOut


class GuideQuestionIn(BaseModel):
    text: str = Field(min_length=5, max_length=400)
    purpose: str = Field(default="", max_length=240)
    is_leading: bool = False


class GuideQuestionOut(ORMModel):
    id: str
    text: str
    purpose: str
    order_index: int
    is_leading: bool


class InterviewCreate(BaseModel):
    project_id: str
    participant_id: str
    title: str = Field(min_length=3, max_length=200)
    objective: str = Field(default="", max_length=4000)
    scheduled_at: Optional[datetime] = None
    duration_minutes: int = Field(default=30, ge=10, le=180)
    interviewer_id: Optional[str] = None
    status: InterviewStatus = InterviewStatus.PLANNED
    guide: list[GuideQuestionIn] = Field(default_factory=list, max_length=25)
    use_default_guide: bool = False


class InterviewUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    objective: Optional[str] = Field(default=None, max_length=4000)
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, ge=10, le=180)
    interviewer_id: Optional[str] = None
    status: Optional[InterviewStatus] = None
    channel: Optional[str] = Field(default=None, max_length=80)
    notes: Optional[str] = Field(default=None, max_length=20000)
    summary: Optional[str] = Field(default=None, max_length=8000)
    follow_up_questions: Optional[list[str]] = None
    consent_status: Optional[ConsentStatus] = None
    recording_enabled: Optional[bool] = None
    change_note: str = Field(default="", max_length=240)


class ConsentRecordIn(BaseModel):
    consent_type: ConsentType
    status: ConsentStatus
    note: str = Field(default="", max_length=320)


class ConsentRecordOut(ORMModel):
    id: str
    consent_type: ConsentType
    status: ConsentStatus
    note: str
    recorded_at: datetime
    recorded_by: Optional[Ref] = None


class InterviewOut(ORMModel):
    id: str
    code: str
    project_id: str
    participant_id: str
    recruitment_id: Optional[str]
    title: str
    objective: str
    scheduled_at: Optional[datetime]
    duration_minutes: int
    interviewer_id: Optional[str]
    status: InterviewStatus
    channel: str
    consent_status: ConsentStatus
    recording_enabled: bool
    notes: str
    summary: str
    follow_up_questions: list[str]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class InterviewSummary(InterviewOut):
    participant: Optional[ParticipantOut] = None
    project: Optional[Ref] = None
    interviewer: Optional[Ref] = None
    evidence_count: int = 0
    evidence_pending_review: int = 0


class InterviewDetail(InterviewSummary):
    guide: list[GuideQuestionOut] = Field(default_factory=list)
    consent_records: list[ConsentRecordOut] = Field(default_factory=list)
    evidence: list["EvidenceOut"] = Field(default_factory=list)


class InterviewListResponse(BaseModel):
    items: list[InterviewSummary]
    total: int
    status_counts: dict[str, int] = Field(default_factory=dict)


from app.schemas.evidence import EvidenceOut  # noqa: E402  (circular-safe import)

InterviewDetail.model_rebuild()
