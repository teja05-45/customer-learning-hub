"""Unified feedback sources.

Not every customer can attend an interview. This module accepts synchronous
conversations, asynchronous written feedback and existing support/review
material in one place, while keeping the original customer words separate from
the researcher's interpretation and refusing to call a short survey "deep".
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_actor
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError, RuleViolationError
from app.models import Evidence, FeedbackRecord, Interview, Participant, ResearchProject, User
from app.models.enums import FeedbackSourceType, feedback_depth
from app.schemas.common import Message, Ref
from app.schemas.evidence import EvidenceOut
from app.schemas.feedback import FeedbackCreate, FeedbackListResponse, FeedbackOut, FeedbackUpdate
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
from app.services.serializers import evidence_out

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _as_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _ref(entity, label: str, sublabel: str | None = None) -> Ref:
    return Ref(id=entity.id, label=label, sublabel=sublabel)


def _feedback_out(db: Session, row: FeedbackRecord) -> FeedbackOut:
    project = db.get(ResearchProject, row.project_id)
    participant = db.get(Participant, row.participant_id) if row.participant_id else None
    interview = db.get(Interview, row.interview_id) if row.interview_id else None
    creator = db.get(User, row.created_by_id) if row.created_by_id else None
    depth, depth_note = feedback_depth(row.collection_method)

    return FeedbackOut(
        id=row.id,
        code=row.code,
        project_id=row.project_id,
        participant_id=row.participant_id,
        interview_id=row.interview_id,
        source_type=row.source_type,
        collection_method=row.collection_method,
        source_reference=row.source_reference,
        collected_at=row.collected_at,
        contributor=row.contributor,
        content=row.content,
        interpretation=row.interpretation,
        context=row.context,
        verification_status=row.verification_status,
        created_by_id=row.created_by_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
        is_attributed=bool(row.participant_id),
        research_depth=depth,
        depth_note=depth_note,
        participant=(
            _ref(participant, participant.display_name, participant.code) if participant else None
        ),
        project=_ref(project, project.name, project.status) if project else None,
        interview=(
            _ref(interview, f"{interview.code} · {interview.title}", interview.status)
            if interview
            else None
        ),
        created_by=_ref(creator, creator.name, creator.job_title or creator.role) if creator else None,
    )


def _validate(
    db: Session,
    *,
    project_id: str,
    participant_id: str | None,
    interview_id: str | None,
    source_type: str,
    verification_status: str,
    source_reference: str,
    collected_at: datetime | None,
) -> tuple[ResearchProject, Participant | None, Interview | None]:
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise NotFoundError(f"Project '{project_id}' does not exist.")

    participant = None
    if participant_id:
        participant = db.get(Participant, participant_id)
        if participant is None:
            raise NotFoundError(f"Participant '{participant_id}' does not exist.")

    interview = None
    if interview_id:
        interview = db.get(Interview, interview_id)
        if interview is None:
            raise NotFoundError(f"Interview '{interview_id}' does not exist.")
        if interview.project_id != project.id:
            raise RuleViolationError("That interview belongs to a different project.")
        if interview.status == "cancelled":
            raise RuleViolationError("A cancelled interview cannot produce feedback.")

    if source_type == FeedbackSourceType.INTERVIEW.value and interview is None:
        raise RuleViolationError(
            "An interview feedback source must link to the interview it came from."
        )
    if source_type != FeedbackSourceType.INTERVIEW.value and interview is not None:
        raise RuleViolationError("Only an interview source may link to an interview.")

    if verification_status == "verified" and not source_reference.strip():
        raise RuleViolationError(
            "A verified source needs a source reference. Record where it came from first."
        )

    collected = _as_aware(collected_at)
    if collected is not None and collected > datetime.now(timezone.utc) + timedelta(days=1):
        raise RuleViolationError("The collection date cannot be in the future.")

    return project, participant, interview


@router.get("", response_model=FeedbackListResponse)
def list_feedback(
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
    project_id: str | None = Query(default=None),
    participant_id: str | None = Query(default=None),
    source_type: list[str] | None = Query(default=None),
    verification_status: list[str] | None = Query(default=None),
    unattributed_only: bool = Query(default=False),
    q: str | None = Query(default=None, max_length=120),
) -> FeedbackListResponse:
    user = require_actor(actor)
    allowed = visible_project_ids(db, user)
    stmt = select(FeedbackRecord)
    if allowed is not None:
        if not allowed:
            return FeedbackListResponse(
                items=[], total=0, source_counts={}, unverified_count=0, unattributed_count=0
            )
        stmt = stmt.where(FeedbackRecord.project_id.in_(allowed))
    if project_id:
        assert_project_read(db, user, project_id)
        stmt = stmt.where(FeedbackRecord.project_id == project_id)
    if participant_id:
        stmt = stmt.where(FeedbackRecord.participant_id == participant_id)
    if source_type:
        stmt = stmt.where(FeedbackRecord.source_type.in_(source_type))
    if verification_status:
        stmt = stmt.where(FeedbackRecord.verification_status.in_(verification_status))
    if unattributed_only:
        stmt = stmt.where(FeedbackRecord.participant_id.is_(None))
    if q:
        term = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(FeedbackRecord.content).like(term),
                func.lower(FeedbackRecord.interpretation).like(term),
                func.lower(FeedbackRecord.source_reference).like(term),
                func.lower(FeedbackRecord.contributor).like(term),
                func.lower(FeedbackRecord.code).like(term),
            )
        )

    rows = db.execute(stmt.order_by(FeedbackRecord.collected_at.desc())).scalars().unique().all()
    source_counts: dict[str, int] = {}
    for row in rows:
        source_counts[row.source_type] = source_counts.get(row.source_type, 0) + 1
    unverified = len([row for row in rows if row.verification_status != "verified"])
    unattributed = len([row for row in rows if row.participant_id is None])

    return FeedbackListResponse(
        items=[_feedback_out(db, row) for row in rows],
        total=len(rows),
        source_counts=source_counts,
        unverified_count=unverified,
        unattributed_count=unattributed,
    )


@router.post("", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def create_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> FeedbackOut:
    now = datetime.now(timezone.utc)
    collected_at = _as_aware(payload.collected_at) or now
    project, participant, interview = _validate(
        db,
        project_id=payload.project_id,
        participant_id=payload.participant_id,
        interview_id=payload.interview_id,
        source_type=payload.source_type.value,
        verification_status=payload.verification_status.value,
        source_reference=payload.source_reference,
        collected_at=collected_at,
    )

    assert_project_write(db, actor, project.id)
    record = FeedbackRecord(
        code=next_code(db, FeedbackRecord, "code", "FB"),
        project_id=project.id,
        participant_id=participant.id if participant else None,
        interview_id=interview.id if interview else None,
        source_type=payload.source_type.value,
        collection_method=payload.collection_method.value,
        source_reference=payload.source_reference.strip(),
        collected_at=collected_at,
        contributor=payload.contributor.strip(),
        content=payload.content.strip(),
        interpretation=payload.interpretation.strip(),
        context=payload.context.strip(),
        verification_status=payload.verification_status.value,
        created_by_id=actor.id if actor else None,
    )
    db.add(record)
    log_activity(
        db,
        entity_type="feedback",
        entity_id=record.id,
        entity_label=f"{record.code} · {payload.source_type.value.replace('_', ' ')}",
        verb="captured",
        summary=(
            f"Feedback captured from {payload.collection_method.value.replace('_', ' ')}"
            + (f" for {participant.display_name}." if participant else " without a known participant.")
        ),
        actor_id=actor.id if actor else None,
        project_id=project.id,
    )
    db.commit()
    db.refresh(record)
    return _feedback_out(db, record)


@router.get("/{feedback_id}", response_model=FeedbackOut)
def get_feedback(
    feedback_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> FeedbackOut:
    record = db.get(FeedbackRecord, feedback_id)
    if record is None:
        raise NotFoundError(f"Feedback source '{feedback_id}' does not exist.")
    assert_entity_read(db, actor, record.project_id)
    return _feedback_out(db, record)


@router.patch("/{feedback_id}", response_model=FeedbackOut)
def update_feedback(
    feedback_id: str,
    payload: FeedbackUpdate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> FeedbackOut:
    record = db.get(FeedbackRecord, feedback_id)
    if record is None:
        raise NotFoundError(f"Feedback source '{feedback_id}' does not exist.")
    assert_entity_write(db, actor, record.project_id)

    data = payload.model_dump(exclude_unset=True)
    candidate_participant = data.get("participant_id", record.participant_id)
    candidate_source = data.get("source_type", record.source_type)
    candidate_verification = data.get("verification_status", record.verification_status)
    candidate_reference = data.get("source_reference", record.source_reference)
    candidate_collected = data.get("collected_at", record.collected_at)

    _validate(
        db,
        project_id=record.project_id,
        participant_id=candidate_participant,
        interview_id=record.interview_id,
        source_type=candidate_source.value if hasattr(candidate_source, "value") else candidate_source,
        verification_status=(
            candidate_verification.value
            if hasattr(candidate_verification, "value")
            else candidate_verification
        ),
        source_reference=candidate_reference or "",
        collected_at=candidate_collected,
    )

    changed = sorted(data.keys())
    for field, value in data.items():
        setattr(record, field, value.value if hasattr(value, "value") else value)
    if "source_reference" in data:
        record.source_reference = (data["source_reference"] or "").strip()
    if "content" in data:
        record.content = data["content"].strip()
    if "interpretation" in data:
        record.interpretation = data["interpretation"].strip()

    log_activity(
        db,
        entity_type="feedback",
        entity_id=record.id,
        entity_label=f"{record.code} · {record.source_type.replace('_', ' ')}",
        verb="updated",
        summary=f"Feedback source {record.code} updated: {', '.join(changed)}.",
        actor_id=actor.id if actor else None,
        project_id=record.project_id,
    )
    db.commit()
    db.refresh(record)
    return _feedback_out(db, record)


@router.post(
    "/{feedback_id}/evidence",
    response_model=EvidenceOut,
    status_code=status.HTTP_201_CREATED,
    tags=["evidence"],
)
def create_evidence_from_feedback(
    feedback_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> EvidenceOut:
    """Turn one feedback source into evidence without rewriting the customer's words.

    The statement is copied byte for byte from the stored feedback content; the
    researcher's interpretation and context are copied into their own fields.
    Deriving evidence twice from the same source is refused rather than creating
    duplicate research history.
    """
    record = db.get(FeedbackRecord, feedback_id)
    if record is None:
        raise NotFoundError(f"Feedback source '{feedback_id}' does not exist.")
    assert_entity_write(db, actor, record.project_id)

    existing = db.execute(
        select(Evidence).where(Evidence.feedback_record_id == record.id)
    ).scalars().first()
    if existing is not None:
        raise ConflictError(
            f"Evidence {existing.code} already exists for this feedback source.",
            details={"evidence_id": existing.id, "evidence_code": existing.code},
        )

    participant = db.get(Participant, record.participant_id) if record.participant_id else None
    depth, _depth_note = feedback_depth(record.collection_method)
    source_reference = (record.source_reference or "").strip()
    evidence = Evidence(
        code=next_code(db, Evidence, "code", "EV"),
        interview_id=record.interview_id,
        feedback_record_id=record.id,
        project_id=record.project_id,
        participant_id=record.participant_id,
        # A written, surveyed or imported statement is still a verbatim quote.
        evidence_type="verbatim_quote",
        content=record.content,
        interpretation=record.interpretation,
        customer_context=record.context,
        segment=participant.segment if participant else "unknown",
        provenance=source_reference,
        provenance_status="recorded" if source_reference else "missing",
        confidence="medium" if record.verification_status == "verified" else "low",
        review_status="unreviewed" if source_reference else "flagged",
        captured_by_id=actor.id if actor else None,
        source_type=record.source_type,
        collection_method=record.collection_method,
        research_depth=depth,
        source_reference=source_reference,
        verification_state=record.verification_status,
        collected_at=record.collected_at,
    )
    db.add(evidence)
    db.flush()
    log_activity(
        db,
        entity_type="evidence",
        entity_id=evidence.id,
        entity_label=f"{evidence.code} · from {record.code}",
        verb="derived",
        summary=(
            f"Evidence derived from feedback source {record.code} "
            f"({record.source_type.replace('_', ' ')}). The customer statement was copied unchanged."
        ),
        actor_id=actor.id if actor else None,
        project_id=record.project_id,
    )
    db.commit()
    db.refresh(evidence)
    return evidence_out(db, evidence)


@router.get("/{feedback_id}/evidence", response_model=list[EvidenceOut], tags=["evidence"])
def list_feedback_evidence(
    feedback_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> list[EvidenceOut]:
    record = db.get(FeedbackRecord, feedback_id)
    if record is None:
        raise NotFoundError(f"Feedback source '{feedback_id}' does not exist.")
    assert_entity_read(db, actor, record.project_id)
    rows = db.execute(
        select(Evidence).where(Evidence.feedback_record_id == record.id).order_by(Evidence.captured_at.asc())
    ).scalars().all()
    return [evidence_out(db, row) for row in rows]


@router.delete("/{feedback_id}", response_model=Message)
def delete_feedback(
    feedback_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> Message:
    record = db.get(FeedbackRecord, feedback_id)
    if record is None:
        raise NotFoundError(f"Feedback source '{feedback_id}' does not exist.")
    assert_entity_write(db, actor, record.project_id)
    code = record.code
    log_activity(
        db,
        entity_type="feedback",
        entity_id=None,
        entity_label=f"{code} · feedback source",
        verb="deleted",
        summary=f"Feedback source {code} deleted by {actor.name if actor else 'an unknown user'}.",
        actor_id=actor.id if actor else None,
        project_id=record.project_id,
    )
    db.delete(record)
    db.commit()
    return Message(message=f"Feedback source {code} deleted.")
