"""Evidence capture schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Confidence, EvidenceRole, EvidenceType, ProvenanceStatus, ReviewStatus, Segment
from app.schemas.common import ORMModel, Ref

SOURCE_UNAVAILABLE = "Source context unavailable — do not treat this as verified evidence."


class EvidenceBase(BaseModel):
    evidence_type: EvidenceType = EvidenceType.VERBATIM_QUOTE
    content: str = Field(min_length=3, max_length=8000)
    interpretation: str = Field(default="", max_length=4000)
    customer_context: str = Field(default="", max_length=2000)
    provenance: str = Field(default="", max_length=320)
    confidence: Confidence = Confidence.MEDIUM


class EvidenceCreate(EvidenceBase):
    interview_id: str
    participant_id: Optional[str] = None
    segment: Optional[Segment] = None
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED

    @field_validator("interpretation")
    @classmethod
    def _interpretation_is_separate(cls, value: str, info):
        return value


class EvidenceUpdate(BaseModel):
    evidence_type: Optional[EvidenceType] = None
    content: Optional[str] = Field(default=None, min_length=3, max_length=8000)
    interpretation: Optional[str] = Field(default=None, max_length=4000)
    customer_context: Optional[str] = Field(default=None, max_length=2000)
    provenance: Optional[str] = Field(default=None, max_length=320)
    confidence: Optional[Confidence] = None
    review_status: Optional[ReviewStatus] = None
    segment: Optional[Segment] = None


class EvidenceLinkOut(BaseModel):
    insight_id: str
    insight_code: str
    insight_title: str
    role: EvidenceRole


class EvidenceOut(ORMModel):
    id: str
    code: str
    interview_id: Optional[str]
    feedback_record_id: Optional[str] = None
    project_id: str
    participant_id: Optional[str]
    evidence_type: EvidenceType
    content: str
    interpretation: str
    customer_context: str
    segment: Segment
    provenance: str
    provenance_status: ProvenanceStatus
    confidence: Confidence
    review_status: ReviewStatus
    captured_at: datetime
    captured_by_id: Optional[str]
    # Provenance of the originating feedback source. Stored as a snapshot for
    # feedback-derived evidence, derived from the interview for interview evidence.
    source_type: Optional[str] = None
    collection_method: Optional[str] = None
    research_depth: Optional[str] = None
    source_reference: Optional[str] = None
    verification_state: Optional[str] = None
    collected_at: Optional[datetime] = None
    is_attributed: bool = False
    is_verified_source: bool = False
    provenance_warning: Optional[str] = None
    participant: Optional[Ref] = None
    captured_by: Optional[Ref] = None
    interview: Optional[Ref] = None
    feedback_record: Optional[Ref] = None
    project: Optional[Ref] = None
    insight_links: list[EvidenceLinkOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class EvidenceListResponse(BaseModel):
    items: list[EvidenceOut]
    total: int
    type_counts: dict[str, int] = Field(default_factory=dict)
    unverified_count: int = 0


class EvidenceStats(BaseModel):
    total: int
    by_type: dict[str, int]
    unverified: int
    unreviewed: int
