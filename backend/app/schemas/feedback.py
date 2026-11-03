"""Unified feedback-source schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import CollectionMethod, FeedbackSourceType, VerificationStatus
from app.schemas.common import ORMModel, Ref


class FeedbackCreate(BaseModel):
    project_id: str
    participant_id: Optional[str] = None
    interview_id: Optional[str] = None
    source_type: FeedbackSourceType
    collection_method: CollectionMethod
    source_reference: str = Field(default="", max_length=320)
    collected_at: Optional[datetime] = None
    contributor: str = Field(default="", max_length=160)
    content: str = Field(min_length=3, max_length=12000)
    interpretation: str = Field(default="", max_length=4000)
    context: str = Field(default="", max_length=2000)
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED


class FeedbackUpdate(BaseModel):
    """Project and interview links are immutable; provenance is not rewritten."""

    participant_id: Optional[str] = None
    source_type: Optional[FeedbackSourceType] = None
    collection_method: Optional[CollectionMethod] = None
    source_reference: Optional[str] = Field(default=None, max_length=320)
    collected_at: Optional[datetime] = None
    contributor: Optional[str] = Field(default=None, max_length=160)
    content: Optional[str] = Field(default=None, min_length=3, max_length=12000)
    interpretation: Optional[str] = Field(default=None, max_length=4000)
    context: Optional[str] = Field(default=None, max_length=2000)
    verification_status: Optional[VerificationStatus] = None


class FeedbackOut(ORMModel):
    id: str
    code: str
    project_id: str
    participant_id: Optional[str]
    interview_id: Optional[str]
    source_type: FeedbackSourceType
    collection_method: CollectionMethod
    source_reference: str
    collected_at: datetime
    contributor: str
    content: str
    interpretation: str
    context: str
    verification_status: VerificationStatus
    created_by_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_attributed: bool = False
    research_depth: str = "context"
    depth_note: str = ""
    participant: Optional[Ref] = None
    project: Optional[Ref] = None
    interview: Optional[Ref] = None
    created_by: Optional[Ref] = None


class FeedbackListResponse(BaseModel):
    items: list[FeedbackOut]
    total: int
    source_counts: dict[str, int] = Field(default_factory=dict)
    unverified_count: int = 0
    unattributed_count: int = 0
