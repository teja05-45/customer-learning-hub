"""Recruitment pipeline endpoints.

The pipeline is the place where sampling bias becomes visible: the interface
shows which segments are actually represented, not just how many people were
invited.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_actor
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError, RuleViolationError
from app.models import Participant, RecruitmentEvent, RecruitmentRecord, ResearchProject, User
from app.models.enums import RECRUITMENT_TRANSITIONS, RecruitmentStage
from app.schemas.common import Message
from app.schemas.participant import (
    ParticipantAssignResult,
    RecruitmentCreate,
    RecruitmentListResponse,
    RecruitmentOut,
    RecruitmentUpdate,
)
from app.services.activity import log_activity
from app.services.serializers import recruitment_out, segment_coverage

router = APIRouter(prefix="/recruitment", tags=["recruitment"])

RESPONDED_STAGES = {"responded", "scheduled", "completed", "declined", "withdrawn"}
INCLUDED_STAGES = ["scheduled", "completed"]

SEGMENT_LABELS = {
    "first_time_buyer": "first-time buyers",
    "repeat_buyer": "repeat buyers",
    "lapsed_buyer": "lapsed buyers",
    "household_buyer": "household buyers",
    "unknown": "unclassified participants",
}


def _warnings(db: Session, project_id: str | None, records: list[RecruitmentRecord]) -> list[str]:
    warnings: list[str] = []
    included = [r for r in records if r.stage in INCLUDED_STAGES]
    if len(included) < 6:
        warnings.append(
            f"Only {len(included)} conversation(s) are booked or complete. This is not a representative sample of the "
            "customer base — present it as a set of individual accounts."
        )

    if included:
        by_segment: dict[str, int] = {}
        for record in included:
            participant = db.get(Participant, record.participant_id)
            if participant:
                by_segment[participant.segment] = by_segment.get(participant.segment, 0) + 1
        top_segment, top_count = max(by_segment.items(), key=lambda item: item[1])
        if top_count / len(included) >= 0.6 and len(by_segment) > 1:
            warnings.append(
                f"{round(top_count / len(included) * 100)}% of booked or completed conversations are "
                f"{SEGMENT_LABELS.get(top_segment, top_segment)}. Consider whether other perspectives are missing."
            )

    if project_id:
        project = db.get(ResearchProject, project_id)
        if project and project.target_segments:
            coverage = segment_coverage(db, project.id)
            missing = [s for s in project.target_segments if coverage.get(s, 0) == 0]
            if missing:
                names = ", ".join(SEGMENT_LABELS.get(s, s) for s in missing)
                warnings.append(f"Target segments with no participants yet: {names}.")
    return warnings


@router.get("", response_model=RecruitmentListResponse)
def list_recruitment(
    db: Session = Depends(get_db),
    project_id: str | None = Query(default=None),
    stage: list[str] | None = Query(default=None),
    segment: list[str] | None = Query(default=None),
    q: str | None = Query(default=None, max_length=120),
    owner_id: str | None = Query(default=None),
) -> RecruitmentListResponse:
    stmt = select(RecruitmentRecord)
    if project_id:
        stmt = stmt.where(RecruitmentRecord.project_id == project_id)
    if stage:
        stmt = stmt.where(RecruitmentRecord.stage.in_(stage))
    if q or segment:
        stmt = stmt.join(Participant, Participant.id == RecruitmentRecord.participant_id)
    if q:
        term = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(func.lower(Participant.display_name).like(term), func.lower(Participant.code).like(term))
        )
    if segment:
        stmt = stmt.where(Participant.segment.in_(segment))

    stmt = stmt.order_by(RecruitmentRecord.updated_at.desc())
    records = db.execute(stmt).scalars().unique().all()

    stage_counts = dict(
        db.execute(
            select(RecruitmentRecord.stage, func.count(RecruitmentRecord.id))
            .where(RecruitmentRecord.project_id == project_id if project_id else True)
            .group_by(RecruitmentRecord.stage)
        ).all()
    )
    coverage = segment_coverage(db, project_id) if project_id else {}

    return RecruitmentListResponse(
        items=[recruitment_out(db, r) for r in records],
        total=len(records),
        stage_counts=stage_counts,
        segment_coverage=coverage,
        warnings=_warnings(db, project_id, records),
    )


@router.post("", response_model=ParticipantAssignResult, status_code=status.HTTP_201_CREATED)
def create_recruitment(
    payload: RecruitmentCreate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> ParticipantAssignResult:
    project = db.get(ResearchProject, payload.project_id)
    if project is None:
        raise NotFoundError("That research project does not exist.")

    created: list[RecruitmentOut] = []
    skipped: list[dict] = []
    duplicates = 0
    for participant_id in payload.participant_ids:
        participant = db.get(Participant, participant_id)
        if participant is None:
            skipped.append({"participant_id": participant_id, "reason": "Participant not found"})
            continue
        if participant.eligibility == "ineligible":
            skipped.append(
                {"participant_id": participant_id, "reason": f"{participant.display_name} is marked ineligible"}
            )
            continue
        exists = db.execute(
            select(RecruitmentRecord).where(
                RecruitmentRecord.project_id == project.id,
                RecruitmentRecord.participant_id == participant.id,
            )
        ).scalar_one_or_none()
        if exists:
            duplicates += 1
            skipped.append(
                {"participant_id": participant_id, "reason": f"{participant.display_name} is already on this list"}
            )
            continue
        record = RecruitmentRecord(
            project_id=project.id,
            participant_id=participant.id,
            stage="selected",
            next_action=payload.next_action,
            notes=payload.note,
            updated_by_id=actor.id if actor else None,
        )
        db.add(record)
        db.flush()
        db.add(
            RecruitmentEvent(
                recruitment_id=record.id,
                from_stage=None,
                to_stage="selected",
                note=payload.note or "Selected for the recruitment list.",
                actor_id=actor.id if actor else None,
            )
        )
        created.append(record)
        db.refresh(record)

    if not created:
        db.rollback()
        raise ConflictError(
            "No participants were added to the pipeline.", details={"skipped": skipped}
        )

    log_activity(
        db,
        entity_type="recruitment",
        entity_id=project.id,
        entity_label=project.name,
        verb="created",
        summary=f"{len(created)} participant(s) added to the recruitment list.",
        actor_id=actor.id if actor else None,
        project_id=project.id,
    )
    db.commit()
    return ParticipantAssignResult(created=[recruitment_out(db, r) for r in created], skipped=skipped)


@router.get("/{recruitment_id}", response_model=RecruitmentOut)
def get_recruitment(recruitment_id: str, db: Session = Depends(get_db)) -> RecruitmentOut:
    record = db.get(RecruitmentRecord, recruitment_id)
    if record is None:
        raise NotFoundError("That recruitment record does not exist.")
    return recruitment_out(db, record, include_events=True)


@router.patch("/{recruitment_id}", response_model=RecruitmentOut)
def update_recruitment(
    recruitment_id: str,
    payload: RecruitmentUpdate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> RecruitmentOut:
    record = db.get(RecruitmentRecord, recruitment_id)
    if record is None:
        raise NotFoundError("That recruitment record does not exist.")

    previous = record.stage
    if payload.stage and payload.stage.value != previous:
        allowed = {s.value for s in RECRUITMENT_TRANSITIONS.get(RecruitmentStage(previous), set())}
        if payload.stage.value not in allowed:
            raise RuleViolationError(
                f"Cannot move from '{previous}' to '{payload.stage.value}'.",
                details={"allowed": sorted(allowed)},
            )
        record.stage = payload.stage.value
        now = datetime.now(timezone.utc)
        if payload.stage.value == "invited" and record.invited_at is None:
            record.invited_at = now
        if payload.stage.value in RESPONDED_STAGES and record.responded_at is None:
            record.responded_at = now
        if payload.stage.value == "invited":
            record.responded_at = None
        record.updated_at = now
        db.add(
            RecruitmentEvent(
                recruitment_id=record.id,
                from_stage=previous,
                to_stage=record.stage,
                note=payload.note or f"Moved from {previous.replace('_', ' ')} to {payload.stage.value.replace('_', ' ')}.",
                actor_id=actor.id if actor else None,
            )
        )
        participant = db.get(Participant, record.participant_id)
        if participant and payload.stage.value in ("invited", "scheduled", "completed"):
            participant.last_research_contact_at = now
        log_activity(
            db,
            entity_type="recruitment",
            entity_id=record.id,
            entity_label=f"{participant.display_name if participant else 'Participant'} · {record.stage}",
            verb="transitioned",
            summary=f"Recruitment stage changed from {previous.replace('_', ' ')} to {record.stage.replace('_', ' ')}.",
            actor_id=actor.id if actor else None,
            project_id=record.project_id,
        )

    if payload.next_action is not None:
        record.next_action = payload.next_action
    if payload.notes is not None:
        record.notes = payload.notes
    record.updated_by_id = actor.id if actor else record.updated_by_id

    db.commit()
    db.refresh(record)
    return recruitment_out(db, record, include_events=True)


@router.delete("/{recruitment_id}", response_model=Message)
def delete_recruitment(recruitment_id: str, db: Session = Depends(get_db)) -> Message:
    record = db.get(RecruitmentRecord, recruitment_id)
    if record is None:
        raise NotFoundError("That recruitment record does not exist.")
    db.delete(record)
    db.commit()
    return Message(message="Participant removed from the recruitment list.")
