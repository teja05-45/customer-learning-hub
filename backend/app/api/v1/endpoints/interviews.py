"""Interview management endpoints.

Two product rules are enforced server-side rather than only in the UI:

* recording cannot be switched on without a granted recording consent, and
* status changes must follow the documented lifecycle.
"""

from datetime import datetime, timezone

from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_actor
from app.core.database import get_db
from app.core.errors import NotFoundError, RuleViolationError
from app.models import (
    ConsentRecord,
    Interview,
    InterviewGuideQuestion,
    Participant,
    RecruitmentRecord,
    ResearchProject,
    User,
)
from app.models.enums import INTERVIEW_TRANSITIONS, InterviewStatus
from app.schemas.common import Message
from app.schemas.interview import (
    ConsentRecordIn,
    InterviewCreate,
    InterviewDetail,
    InterviewListResponse,
    InterviewSummary,
    InterviewUpdate,
)
from app.services.activity import log_activity
from app.services.common import next_code
from app.services.serializers import interview_detail, interview_summary
from app.services.templates import DEFAULT_INTERVIEW_GUIDE, GUIDE_QUALITY_RULES

router = APIRouter(prefix="/interviews", tags=["interviews"])


class RecordingToggle(BaseModel):
    enabled: bool


@router.get("/guide/default", response_model=dict)
def default_guide() -> dict:
    """The neutral starter guide plus the quality rules the team agreed to."""
    return {
        "questions": [{"text": text, "purpose": purpose} for text, purpose in DEFAULT_INTERVIEW_GUIDE],
        "rules": GUIDE_QUALITY_RULES,
        "note": "Recording is disabled by default and no audio is captured anywhere in this prototype.",
    }


@router.get("", response_model=InterviewListResponse)
def list_interviews(
    db: Session = Depends(get_db),
    project_id: str | None = Query(default=None),
    participant_id: str | None = Query(default=None),
    interviewer_id: str | None = Query(default=None),
    interview_status: list[str] | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=120),
    upcoming_only: bool = Query(default=False),
) -> InterviewListResponse:
    stmt = select(Interview)
    if project_id:
        stmt = stmt.where(Interview.project_id == project_id)
    if participant_id:
        stmt = stmt.where(Interview.participant_id == participant_id)
    if interviewer_id:
        stmt = stmt.where(Interview.interviewer_id == interviewer_id)
    if interview_status:
        stmt = stmt.where(Interview.status.in_(interview_status))
    if q:
        term = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(Interview.title).like(term), func.lower(Interview.code).like(term)))
    if upcoming_only:
        stmt = stmt.where(
            Interview.status.in_(("planned", "scheduled")),
            Interview.scheduled_at.is_not(None),
            Interview.scheduled_at >= datetime.now(timezone.utc),
        )

    stmt = stmt.order_by(Interview.scheduled_at.desc().nulls_last())
    rows = db.execute(stmt).scalars().unique().all()
    status_counts = dict(
        db.execute(select(Interview.status, func.count(Interview.id)).group_by(Interview.status)).all()
    )
    return InterviewListResponse(
        items=[interview_summary(db, i) for i in rows],
        total=len(rows),
        status_counts=status_counts,
    )


@router.post("", response_model=InterviewDetail, status_code=status.HTTP_201_CREATED)
def create_interview(
    payload: InterviewCreate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> InterviewDetail:
    project = db.get(ResearchProject, payload.project_id)
    if project is None:
        raise NotFoundError("That research project does not exist.")
    participant = db.get(Participant, payload.participant_id)
    if participant is None:
        raise NotFoundError("That participant does not exist.")
    if payload.interviewer_id and db.get(User, payload.interviewer_id) is None:
        raise NotFoundError("That interviewer does not exist.")

    recruitment = db.execute(
        select(RecruitmentRecord).where(
            RecruitmentRecord.project_id == project.id, RecruitmentRecord.participant_id == participant.id
        )
    ).scalar_one_or_none()

    interview = Interview(
        code=next_code(db, Interview, "code", "INT"),
        project_id=project.id,
        participant_id=participant.id,
        recruitment_id=recruitment.id if recruitment else None,
        title=payload.title.strip(),
        objective=payload.objective or project.objective,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        interviewer_id=payload.interviewer_id or (actor.id if actor else None),
        status=payload.status.value,
        consent_status="pending",
        recording_enabled=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(interview)
    db.flush()

    guide = [(q.text.strip(), q.purpose) for q in payload.guide]
    if payload.use_default_guide and not guide:
        guide = list(DEFAULT_INTERVIEW_GUIDE)
    for order, (text, purpose) in enumerate(guide):
        db.add(
            InterviewGuideQuestion(
                interview_id=interview.id, text=text, purpose=purpose, order_index=order, is_leading=False
            )
        )

    if payload.scheduled_at and recruitment and recruitment.stage in ("invited", "responded"):
        recruitment.stage = "scheduled"
        recruitment.updated_at = datetime.now(timezone.utc)

    log_activity(
        db,
        entity_type="interview",
        entity_id=interview.id,
        entity_label=f"{interview.code} · {interview.title}",
        verb="created",
        summary=f"Interview planned with {participant.display_name} for {project.name}.",
        actor_id=actor.id if actor else None,
        project_id=project.id,
    )
    db.commit()
    db.refresh(interview)
    return interview_detail(db, interview)


@router.get("/{interview_id}", response_model=InterviewDetail)
def get_interview(interview_id: str, db: Session = Depends(get_db)) -> InterviewDetail:
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise NotFoundError(f"Interview '{interview_id}' does not exist.")
    return interview_detail(db, interview)


@router.patch("/{interview_id}", response_model=InterviewDetail)
def update_interview(
    interview_id: str,
    payload: InterviewUpdate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> InterviewDetail:
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise NotFoundError(f"Interview '{interview_id}' does not exist.")

    data = payload.model_dump(exclude_unset=True)
    change_note = data.pop("change_note", "")
    previous_status = interview.status

    if "recording_enabled" in data and data["recording_enabled"]:
        granted = db.execute(
            select(func.count(ConsentRecord.id)).where(
                ConsentRecord.interview_id == interview.id,
                ConsentRecord.consent_type == "recording",
                ConsentRecord.status == "granted",
            )
        ).scalar_one()
        if not granted:
            raise RuleViolationError(
                "Recording cannot be enabled without explicit recorded consent.",
                details={
                    "action": "Record a recording consent decision for this participant first.",
                    "note": "This prototype never captures audio. The flag exists to demonstrate the consent gate.",
                },
            )

    if "status" in data and data["status"] is not None:
        new_status = data["status"].value
        if new_status != previous_status:
            allowed = {s.value for s in INTERVIEW_TRANSITIONS.get(InterviewStatus(previous_status), set())}
            if new_status not in allowed:
                raise RuleViolationError(
                    f"Cannot move an interview from '{previous_status}' to '{new_status}'.",
                    details={"allowed": sorted(allowed)},
                )
            interview.status = new_status
            if new_status == "completed":
                interview.completed_at = datetime.now(timezone.utc)
                recruitment = (
                    db.get(RecruitmentRecord, interview.recruitment_id) if interview.recruitment_id else None
                )
                if recruitment:
                    recruitment.stage = "completed"
                    recruitment.updated_at = datetime.now(timezone.utc)
                    recruitment.next_action = "Capture and link evidence, then close the loop with the participant."
            if new_status == "cancelled" and interview.recruitment_id:
                recruitment = db.get(RecruitmentRecord, interview.recruitment_id)
                if recruitment and recruitment.stage == "scheduled":
                    recruitment.stage = "cancelled"
            log_activity(
                db,
                entity_type="interview",
                entity_id=interview.id,
                entity_label=f"{interview.code} · {interview.title}",
                verb="transitioned",
                summary=f"Interview status changed from {previous_status} to {new_status}. {change_note}".strip(),
                actor_id=actor.id if actor else None,
                project_id=interview.project_id,
            )
        data.pop("status")

    if "interviewer_id" in data and data["interviewer_id"] and db.get(User, data["interviewer_id"]) is None:
        raise NotFoundError("That interviewer does not exist.")

    for field, value in data.items():
        setattr(interview, field, value.value if hasattr(value, "value") else value)

    db.commit()
    db.refresh(interview)
    return interview_detail(db, interview)


@router.post("/{interview_id}/consent", response_model=InterviewDetail)
def record_consent(
    interview_id: str,
    payload: ConsentRecordIn,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> InterviewDetail:
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise NotFoundError(f"Interview '{interview_id}' does not exist.")

    db.add(
        ConsentRecord(
            interview_id=interview.id,
            participant_id=interview.participant_id,
            consent_type=payload.consent_type.value,
            status=payload.status.value,
            recorded_by_id=actor.id if actor else None,
            recorded_at=datetime.now(timezone.utc),
            note=payload.note,
        )
    )
    if payload.consent_type.value == "participation":
        interview.consent_status = payload.status.value
    if payload.consent_type.value == "recording" and payload.status.value != "granted":
        interview.recording_enabled = False

    log_activity(
        db,
        entity_type="interview",
        entity_id=interview.id,
        entity_label=interview.code,
        verb="consent",
        summary=f"Consent recorded: {payload.consent_type.value} = {payload.status.value}.",
        actor_id=actor.id if actor else None,
        project_id=interview.project_id,
    )
    db.commit()
    db.refresh(interview)
    return interview_detail(db, interview)


@router.post("/{interview_id}/recording", response_model=Message)
def toggle_recording(
    interview_id: str,
    payload: RecordingToggle,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> Message:
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise NotFoundError(f"Interview '{interview_id}' does not exist.")
    if payload.enabled:
        granted = db.execute(
            select(func.count(ConsentRecord.id)).where(
                ConsentRecord.interview_id == interview.id,
                ConsentRecord.consent_type == "recording",
                ConsentRecord.status == "granted",
            )
        ).scalar_one()
        if not granted:
            raise RuleViolationError(
                "Recording cannot be enabled without explicit recorded consent.",
                details={"action": "Record a recording consent decision for this participant first."},
            )
    interview.recording_enabled = payload.enabled
    db.commit()
    return Message(
        message="Recording flag updated." if payload.enabled else "Recording flag cleared.",
        detail="No audio is captured in this prototype; the flag only demonstrates the consent gate.",
    )
