"""Evidence-to-insight traceability contracts.

The shapes here exist so the UI can render the chain without re-deriving it:
each relationship carries its own classification and rationale, each evidence
item carries the provenance it was collected with, and the traceability response
states explicitly when a finding is unsubstantiated.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import Confidence, EvidenceRole
from app.schemas.common import Ref
from app.schemas.evidence import EvidenceOut
from app.schemas.insight import InsightSummary


class InsightEvidenceLinkOut(BaseModel):
    """One insight-evidence relationship, with its own researcher assessment."""

    relationship_id: str
    classification: EvidenceRole
    rationale: str = ""
    confidence: Optional[Confidence] = None
    tags: list[str] = Field(default_factory=list)
    note: str = ""
    created_by: Optional[Ref] = None
    created_at: datetime
    updated_at: datetime
    evidence: EvidenceOut


class EvidenceGroupOut(BaseModel):
    items: list[InsightEvidenceLinkOut] = Field(default_factory=list)
    count: int = 0


class InsightEvidenceResponse(BaseModel):
    insight_id: str
    insight_code: str
    insight_title: str
    project_id: Optional[str] = None
    supporting: EvidenceGroupOut = Field(default_factory=EvidenceGroupOut)
    contradictory: EvidenceGroupOut = Field(default_factory=EvidenceGroupOut)
    contextual: EvidenceGroupOut = Field(default_factory=EvidenceGroupOut)
    total: int = 0


class TraceabilityQuality(BaseModel):
    """Counts, not verdicts.

    ``is_validated`` is deliberately absent: quantity of support cannot validate
    an insight. ``unsubstantiated`` is true only when nothing is linked.
    """

    total: int = 0
    supporting: int = 0
    contradictory: int = 0
    contextual: int = 0
    verified: int = 0
    unverified: int = 0
    distinct_source_types: int = 0
    unattributed: int = 0
    unsubstantiated: bool = False
    has_conflict: bool = False
    confidence_definition: str = (
        "Confidence records how sure the researcher is that this item is genuinely relevant to "
        "this insight. It is a judgement, not a probability, and it is not aggregated into a "
        "statistical claim."
    )


class TraceabilityActionOut(BaseModel):
    id: str
    code: str
    title: str
    status: str
    owner: Optional[Ref] = None
    due_date: Optional[date] = None


class TraceabilityDecisionOut(BaseModel):
    id: str
    code: str
    title: str
    status: str
    business_function: str
    rationale: str = ""
    decision_date: Optional[datetime] = None
    evidence_sufficient: Optional[bool] = None
    actions: list[TraceabilityActionOut] = Field(default_factory=list)


class InsightTraceability(BaseModel):
    insight: InsightSummary
    evidence: InsightEvidenceResponse
    quality: TraceabilityQuality
    decisions: list[TraceabilityDecisionOut] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    chain_note: str


class EvidenceInsightLinkOut(BaseModel):
    relationship_id: str
    classification: EvidenceRole
    rationale: str = ""
    confidence: Optional[Confidence] = None
    tags: list[str] = Field(default_factory=list)
    created_by: Optional[Ref] = None
    created_at: datetime
    updated_at: datetime
    insight: InsightSummary


class EvidenceInsightsResponse(BaseModel):
    evidence_id: str
    evidence_code: str
    supporting: list[EvidenceInsightLinkOut] = Field(default_factory=list)
    contradictory: list[EvidenceInsightLinkOut] = Field(default_factory=list)
    contextual: list[EvidenceInsightLinkOut] = Field(default_factory=list)
    total: int = 0
    unattributed: bool = False
    statement_note: str


class DecisionTraceabilityInsight(BaseModel):
    insight: InsightSummary
    support_count: int = 0
    contradiction_count: int = 0
    context_count: int = 0
    evidence: list[EvidenceOut] = Field(default_factory=list)


class DecisionTraceability(BaseModel):
    decision_id: str
    decision_code: str
    decision_title: str
    insights: list[DecisionTraceabilityInsight] = Field(default_factory=list)
    direct_evidence: list[EvidenceOut] = Field(default_factory=list)
    actions: list[TraceabilityActionOut] = Field(default_factory=list)
    escalated_contradictions: list[EvidenceOut] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    chain: list[str] = Field(default_factory=list)
    provenance_note: str


class RelationshipWriteResponse(BaseModel):
    """Returned after creating or updating a single relationship."""

    relationship: InsightEvidenceLinkOut
    message: str
