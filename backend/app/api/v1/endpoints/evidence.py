"""Evidence capture endpoints.

Evidence is the atom of the product. The API refuses to invent attribution: if
the caller cannot say where a statement came from, the record is stored as
unverified and labelled as such everywhere it appears.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_actor
from app.core.database import get_db
from app.core.errors import NotFoundError, RuleViolationError
from app.models import Evidence, InsightEvidence, Interview, Participant, User
from app.schemas.common import Message
from app.schemas.evidence import EvidenceCreate, EvidenceListResponse, EvidenceOut, EvidenceStats, EvidenceUpdate
from app.schemas.traceability import EvidenceInsightsResponse
from app.services.access import (
    assert_entity_read,
    assert_entity_write,
    assert_project_read,
    assert_project_write,
    require_actor,
    visible_project_ids,
)
from app.services.activity import log_activity
from app.services.common import next_code
from app.services.serializers import evidence_insights, evidence_out

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("", response_model=EvidenceListResponse)
def list_evidence(
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
    project_id: str | None = Query(default=None),
    interview_id: str | None = Query(default=None),
    participant_id: str | None = Query(default=None),
    evidence_type: list[str] | None = Query(default=None),
    review_status: list[str] | None = Query(default=None),
    segment: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=120),
    unverified_only: bool = Query(default=False),
    feedback_record_id: str | None = Query(default=None),
) -> EvidenceListResponse:
    user = require_actor(actor)
    allowed = visible_project_ids(db, user)
    stmt = select(Evidence)
    if allowed is not None:
        if not allowed:
            return EvidenceListResponse(items=[], total=0, type_counts={}, unverified_count=0)
        stmt = stmt.where(Evidence.project_id.in_(allowed))
    if project_id:
        assert_project_read(db, user, project_id)
        stmt = stmt.where(Evidence.project_id == project_id)
    if feedback_record_id:
        stmt = stmt.where(Evidence.feedback_record_id == feedback_record_id)
    if interview_id:
        stmt = stmt.where(Evidence.interview_id == interview_id)
    if participant_id:
        stmt = stmt.where(Evidence.participant_id == participant_id)
    if evidence_type:
        stmt = stmt.where(Evidence.evidence_type.in_(evidence_type))
    if review_status:
        stmt = stmt.where(Evidence.review_status.in_(review_status))
    if segment:
        stmt = stmt.where(Evidence.segment == segment)
    if q:
        term = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Evidence.content).like(term),
                func.lower(Evidence.interpretation).like(term),
                func.lower(Evidence.code).like(term),
            )
        )
    if unverified_only:
        stmt = stmt.where(Evidence.provenance_status != "recorded")

    stmt = stmt.order_by(Evidence.captured_at.desc())
    rows = db.execute(stmt).scalars().unique().all()
    # Counts describe the rows this caller may see, never the whole workspace.
    type_counts: dict[str, int] = {}
    for row in rows:
        type_counts[row.evidence_type] = type_counts.get(row.evidence_type, 0) + 1
    unverified = len([row for row in rows if row.provenance_status != "recorded"])
    return EvidenceListResponse(
        items=[evidence_out(db, e) for e in rows],
        total=len(rows),
        type_counts=type_counts,
        unverified_count=unverified,
    )


@router.get("/stats", response_model=EvidenceStats)
def evidence_stats(
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
    project_id: str | None = Query(default=None),
) -> EvidenceStats:
    user = require_actor(actor)
    allowed = visible_project_ids(db, user)
    stmt = select(Evidence)
    if allowed is not None:
        if not allowed:
            return EvidenceStats(total=0, by_type={}, unverified=0, unreviewed=0)
        stmt = stmt.where(Evidence.project_id.in_(allowed))
    if project_id:
        assert_project_read(db, user, project_id)
        stmt = stmt.where(Evidence.project_id == project_id)
    rows = db.execute(stmt).scalars().all()
    by_type: dict[str, int] = {}
    for row in rows:
        by_type[row.evidence_type] = by_type.get(row.evidence_type, 0) + 1
    return EvidenceStats(
        total=len(rows),
        by_type=by_type,
        unverified=len([r for r in rows if r.provenance_status != "recorded"]),
        unreviewed=len([r for r in rows if r.review_status == "unreviewed"]),
    )


@router.post("", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
def create_evidence(
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> EvidenceOut:
    interview = db.get(Interview, payload.interview_id)
    if interview is None:
        raise NotFoundError("Evidence must be attached to an existing interview.")
    assert_project_write(db, actor, interview.project_id)
    if interview.status == "cancelled":
        raise RuleViolationError("A cancelled interview cannot produce evidence.")

    participant = db.get(Participant, payload.participant_id or interview.participant_id)
    segment = payload.segment.value if payload.segment else (participant.segment if participant else "unknown")

    provenance = (payload.provenance or "").strip()
    provenance_status = "recorded" if provenance else "missing"
    review_status = payload.review_status.value
    confidence = payload.confidence.value
    if provenance_status == "missing":
        # Never silently upgrade an unattributed claim.
        review_status = "flagged"
        confidence = "low"

    evidence = Evidence(
        code=next_code(db, Evidence, "code", "EV"),
        interview_id=interview.id,
        project_id=interview.project_id,
        participant_id=participant.id if participant else None,
        evidence_type=payload.evidence_type.value,
        content=payload.content.strip(),
        interpretation=payload.interpretation.strip(),
        customer_context=payload.customer_context.strip(),
        segment=segment,
        provenance=provenance,
        provenance_status=provenance_status,
        confidence=confidence,
        review_status=review_status,
        captured_by_id=actor.id if actor else None,
        captured_at=datetime.now(timezone.utc),
    )
    db.add(evidence)
    log_activity(
        db,
        entity_type="evidence",
        entity_id=evidence.id,
        entity_label=f"{evidence.code} · {payload.evidence_type.value.replace('_', ' ')}",
        verb="captured",
        summary=(
            "Evidence captured with recorded provenance."
            if provenance_status == "recorded"
            else "Evidence captured without provenance and flagged as unverified."
        ),
        actor_id=actor.id if actor else None,
        project_id=interview.project_id,
    )
    db.commit()
    db.refresh(evidence)
    return evidence_out(db, evidence)


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> EvidenceOut:
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise NotFoundError(f"Evidence '{evidence_id}' does not exist.")
    assert_entity_read(db, actor, evidence.project_id)
    return evidence_out(db, evidence)


@router.get("/{evidence_id}/insights", response_model=EvidenceInsightsResponse)
def list_evidence_insights(
    evidence_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> EvidenceInsightsResponse:
    """Every insight this item supports, contradicts or contextualises."""
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise NotFoundError(f"Evidence '{evidence_id}' does not exist.")
    assert_entity_read(db, actor, evidence.project_id)
    return evidence_insights(db, evidence)


@router.patch("/{evidence_id}", response_model=EvidenceOut)
def update_evidence(
    evidence_id: str,
    payload: EvidenceUpdate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> EvidenceOut:
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise NotFoundError(f"Evidence '{evidence_id}' does not exist.")
    assert_entity_write(db, actor, evidence.project_id)

    data = payload.model_dump(exclude_unset=True)
    if "provenance" in data:
        provenance = (data["provenance"] or "").strip()
        data["provenance"] = provenance
        evidence.provenance_status = "recorded" if provenance else "missing"
    for field, value in data.items():
        setattr(evidence, field, value.value if hasattr(value, "value") else value)

    if evidence.provenance_status != "recorded":
        evidence.review_status = "flagged"
        evidence.confidence = "low"

    db.commit()
    db.refresh(evidence)
    return evidence_out(db, evidence)


@router.delete("/{evidence_id}", response_model=Message)
def delete_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> Message:
    evidence = db.get(Evidence, evidence_id)
    if evidence is None:
        raise NotFoundError(f"Evidence '{evidence_id}' does not exist.")
    assert_entity_write(db, actor, evidence.project_id)
    linked = db.execute(
        select(func.count(InsightEvidence.id)).where(InsightEvidence.evidence_id == evidence.id)
    ).scalar_one()
    log_activity(
        db,
        entity_type="evidence",
        entity_id=None,
        entity_label=f"{evidence.code} · evidence",
        verb="deleted",
        summary=(
            f"Evidence {evidence.code} deleted by {actor.name if actor else 'an unknown user'}; "
            f"{linked} insight link(s) removed with it."
        ),
        actor_id=actor.id if actor else None,
        project_id=evidence.project_id,
    )
    db.delete(evidence)
    db.commit()
    return Message(
        message="Evidence deleted.",
        detail=(
            f"{linked} insight link(s) were removed with it. The insight itself is kept so the team can see "
            "that its evidence base changed."
            if linked
            else None
        ),
    )
