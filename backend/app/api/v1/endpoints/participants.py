"""Participant directory endpoints."""

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_actor
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError
from app.models import Evidence, Interview, Participant, RecruitmentRecord, ResearchProject, User
from app.schemas.common import Message
from app.schemas.participant import (
    ParticipantCreate,
    ParticipantDetail,
    ParticipantListResponse,
    ParticipantOut,
    ParticipantUpdate,
    ParticipationHistoryItem,
    RecruitmentOut,
)
from app.services.activity import log_activity
from app.services.common import next_code
from app.services.serializers import participant_out, recruitment_out

router = APIRouter(prefix="/participants", tags=["participants"])


class AssignRequest(BaseModel):
    project_id: str
    next_action: str = Field(default="Confirm eligibility, then invite through the controlled Ops process", max_length=240)


@router.get("", response_model=ParticipantListResponse)
def list_participants(
    db: Session = Depends(get_db),
    pagination: Pagination = Depends(),
    q: str | None = Query(default=None, max_length=120),
    segment: list[str] | None = Query(default=None),
    eligibility: list[str] | None = Query(default=None),
    product_category: str | None = Query(default=None),
    sort: str = Query(default="name", pattern="^(name|recent|orders|segment)$"),
) -> ParticipantListResponse:
    stmt = select(Participant)
    if q:
        term = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Participant.display_name).like(term),
                func.lower(Participant.code).like(term),
                func.lower(Participant.eligibility_note).like(term),
            )
        )
    if segment:
        stmt = stmt.where(Participant.segment.in_(segment))
    if eligibility:
        stmt = stmt.where(Participant.eligibility.in_(eligibility))
    if product_category:
        stmt = stmt.where(Participant.product_category == product_category)

    order = {
        "name": Participant.display_name.asc(),
        "recent": Participant.last_purchase_at.desc().nulls_last(),
        "orders": Participant.orders_count.desc(),
        "segment": Participant.segment.asc(),
    }[sort]
    stmt = stmt.order_by(order)

    total = db.execute(select(func.count()).select_from(stmt.order_by(None).subquery())).scalar_one()
    rows = (
        db.execute(stmt.offset((pagination.page - 1) * pagination.page_size).limit(pagination.page_size))
        .scalars()
        .unique()
        .all()
    )
    segment_counts = dict(
        db.execute(select(Participant.segment, func.count(Participant.id)).group_by(Participant.segment)).all()
    )
    return ParticipantListResponse(
        items=[participant_out(db, p) for p in rows],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size if total else 0,
        segment_counts=segment_counts,
    )


@router.post("", response_model=ParticipantOut, status_code=status.HTTP_201_CREATED)
def create_participant(
    payload: ParticipantCreate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> ParticipantOut:
    participant = Participant(
        code=next_code(db, Participant, "code", "P", width=4),
        display_name=payload.display_name.strip(),
        segment=payload.segment.value,
        purchase_frequency=payload.purchase_frequency,
        orders_count=payload.orders_count,
        last_purchase_at=payload.last_purchase_at,
        product_category=payload.product_category,
        eligibility=payload.eligibility.value,
        eligibility_note=payload.eligibility_note,
        contact_route=payload.contact_route,
        notes=payload.notes,
    )
    db.add(participant)
    log_activity(
        db,
        entity_type="participant",
        entity_id=participant.id,
        entity_label=participant.display_name,
        verb="created",
        summary="Synthetic participant added to the directory. No contact details stored.",
        actor_id=actor.id if actor else None,
    )
    db.commit()
    db.refresh(participant)
    return participant_out(db, participant)


@router.get("/{participant_id}", response_model=ParticipantDetail)
def get_participant(participant_id: str, db: Session = Depends(get_db)) -> ParticipantDetail:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError(f"Participant '{participant_id}' does not exist.")

    records = (
        db.execute(
            select(RecruitmentRecord)
            .where(RecruitmentRecord.participant_id == participant.id)
            .order_by(RecruitmentRecord.updated_at.desc())
        )
        .scalars()
        .all()
    )
    interview_rows = (
        db.execute(
            select(Interview, ResearchProject)
            .join(ResearchProject, ResearchProject.id == Interview.project_id)
            .where(Interview.participant_id == participant.id)
            .order_by(Interview.scheduled_at.desc().nulls_last())
        )
        .all()
    )
    history: list[ParticipationHistoryItem] = []
    for interview, project in interview_rows:
        evidence_count = db.execute(
            select(func.count(Evidence.id)).where(Evidence.interview_id == interview.id)
        ).scalar_one()
        history.append(
            ParticipationHistoryItem(
                interview_id=interview.id,
                interview_code=interview.code,
                project_id=project.id,
                project_name=project.name,
                status=interview.status,
                scheduled_at=interview.scheduled_at,
                evidence_count=evidence_count,
                insight_count=0,
            )
        )

    evidence_count = db.execute(
        select(func.count(Evidence.id)).where(Evidence.participant_id == participant.id)
    ).scalar_one()
    base = participant_out(db, participant)
    return ParticipantDetail(
        **base.model_dump(),
        recruitment=[recruitment_out(db, r) for r in records],
        participation_history=history,
        evidence_count=evidence_count,
    )


@router.patch("/{participant_id}", response_model=ParticipantOut)
def update_participant(
    participant_id: str,
    payload: ParticipantUpdate,
    db: Session = Depends(get_db),
) -> ParticipantOut:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError(f"Participant '{participant_id}' does not exist.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(participant, field, value.value if hasattr(value, "value") else value)
    db.commit()
    db.refresh(participant)
    return participant_out(db, participant)


@router.post("/{participant_id}/assign", response_model=Message, status_code=status.HTTP_201_CREATED)
def assign_to_project(
    participant_id: str,
    payload: AssignRequest,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> Message:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError(f"Participant '{participant_id}' does not exist.")
    project = db.get(ResearchProject, payload.project_id)
    if project is None:
        raise NotFoundError("That research project does not exist.")
    if participant.eligibility == "ineligible":
        raise ConflictError(
            "This participant is marked ineligible for research contact. Update eligibility first, with a reason."
        )
    existing = db.execute(
        select(RecruitmentRecord).where(
            RecruitmentRecord.participant_id == participant.id,
            RecruitmentRecord.project_id == project.id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictError("This participant is already on the recruitment list for that project.")

    record = RecruitmentRecord(
        project_id=project.id,
        participant_id=participant.id,
        stage="selected",
        next_action=payload.next_action,
        updated_by_id=actor.id if actor else None,
    )
    db.add(record)
    log_activity(
        db,
        entity_type="recruitment",
        entity_id=record.id,
        entity_label=f"{participant.display_name} → {project.name}",
        verb="created",
        summary="Participant assigned to a project recruitment list.",
        actor_id=actor.id if actor else None,
        project_id=project.id,
    )
    db.commit()
    return Message(message="Participant added to the recruitment pipeline.", detail=project.name)
