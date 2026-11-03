"""Insight library schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Confidence, EvidenceRole, InsightStatus, Segment
from app.schemas.common import ORMModel, Ref
from app.schemas.evidence import EvidenceOut


class InsightCreate(BaseModel):
    title: str = Field(min_length=5, max_length=240)
    summary: str = Field(min_length=20, max_length=6000)
    interpretation: str = Field(default="", max_length=6000)
    research_question: str = Field(default="", max_length=400)
    project_id: Optional[str] = None
    status: InsightStatus = InsightStatus.DRAFT
    confidence: Confidence = Confidence.LOW
    owner_id: Optional[str] = None
    limitations: str = Field(default="", max_length=4000)
    segments: list[Segment] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)


class InsightUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=5, max_length=240)
    summary: Optional[str] = Field(default=None, min_length=20, max_length=6000)
    interpretation: Optional[str] = Field(default=None, max_length=6000)
    research_question: Optional[str] = Field(default=None, max_length=400)
    status: Optional[InsightStatus] = None
    confidence: Optional[Confidence] = None
    owner_id: Optional[str] = None
    limitations: Optional[str] = Field(default=None, max_length=4000)
    segments: Optional[list[Segment]] = None


class EvidenceLinkIn(BaseModel):
    """A researcher's explicit judgement about how evidence is used.

    ``role`` is required to be one of supporting, contradictory or contextual.
    Nothing here can mutate the evidence itself; the link records usage only.
    """

    evidence_id: str
    role: EvidenceRole = EvidenceRole.SUPPORTING
    note: str = Field(default="", max_length=240)
    rationale: str = Field(default="", max_length=2000)
    confidence: Optional[Confidence] = None
    tags: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, values: list[str]) -> list[str]:
        return [value.strip()[:32] for value in values if value.strip()]


class EvidenceLinkUpdate(BaseModel):
    """Relationship metadata only. The evidence and insight are immutable here."""

    role: Optional[EvidenceRole] = None
    rationale: Optional[str] = Field(default=None, max_length=2000)
    confidence: Optional[Confidence] = None
    tags: Optional[list[str]] = Field(default=None, max_length=8)
    note: Optional[str] = Field(default=None, max_length=240)

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        return [value.strip()[:32] for value in values if value.strip()]


class InsightOut(ORMModel):
    id: str
    code: str
    title: str
    summary: str
    interpretation: str
    research_question: str
    project_id: Optional[str]
    status: InsightStatus
    confidence: Confidence
    owner_id: Optional[str]
    limitations: str
    segments: list[str]
    validated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class InsightSummary(InsightOut):
    owner: Optional[Ref] = None
    project: Optional[Ref] = None
    supporting_count: int = 0
    contradictory_count: int = 0
    contextual_count: int = 0
    evidence_count: int = 0
    decision_count: int = 0
    reuse_flag: bool = False


class DecisionRef(BaseModel):
    id: str
    code: str
    title: str
    status: str
    business_function: str
    decision_date: Optional[datetime] = None


class InsightDetail(InsightSummary):
    evidence: list[EvidenceOut] = Field(default_factory=list)
    decisions: list[DecisionRef] = Field(default_factory=list)
    evidence_warning: Optional[str] = None


class InsightListResponse(BaseModel):
    items: list[InsightSummary]
    total: int
    status_counts: dict[str, int] = Field(default_factory=dict)


class InsightEvidenceLinkOut(BaseModel):
    id: str
    role: EvidenceRole
    note: str
    evidence: EvidenceOut
