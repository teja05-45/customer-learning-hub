"""Participant directory endpoints."""

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_actor
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError
from app.models import (
    Evidence,
    FeedbackRecord,
    Insight,
    InsightEvidence,
    Interview,
    Participant,
    RecruitmentRecord,
    ResearchProject,
    User,
)
from app.models.enums import feedback_depth
from app.schemas.common import Message
from app.schemas.participant import (
    ParticipantCreate,
    ParticipantDetail,
    ParticipantListResponse,
    ParticipantFeedbackItem,
    ParticipantOut,
    ParticipantUpdate,
    ParticipationHistoryItem,
    RecruitmentOut,
)
from app.services.access import (
    assert_participant_read,
    assert_participant_write,
    assert_project_write,
    require_actor,
    visible_project_ids,
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
    actor: User | None = Depends(get_actor),
    pagination: Pagination = Depends(),
    q: str | None = Query(default=None, max_length=120),
    segment: list[str] | None = Query(default=None),
    eligibility: list[str] | None = Query(default=None),
    product_category: str | None = Query(default=None),
    sort: str = Query(default="name", pattern="^(name|recent|orders|segment)$"),
) -> ParticipantListResponse:
    user = require_actor(actor)
    allowed = visible_project_ids(db, user)
    stmt = select(Participant)
    if allowed is not None:
        # Customers are workspace-level records; scope them to the people who
        # actually appear in a study the caller may read.
        from app.services.access import participant_project_ids

        visible_ids = set()
        for participant_id in db.execute(select(Participant.id)).scalars():
            if participant_project_ids(db, participant_id) & allowed:
                visible_ids.add(participant_id)
        if not visible_ids:
            return ParticipantListResponse(
                items=[], total=0, page=pagination.page, page_size=pagination.page_size, pages=0, segment_counts={}
            )
        stmt = stmt.where(Participant.id.in_(visible_ids))
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
    segment_counts: dict[str, int] = {}
    for participant in db.execute(select(Participant).where(Participant.id.in_([p.id for p in rows]))).scalars():
        segment_counts[participant.segment] = segment_counts.get(participant.segment, 0) + 1
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
        # A record entered by the team is real customer data, not demo data.
        is_synthetic=False,
    )
    db.add(participant)
    log_activity(
        db,
        entity_type="participant",
        entity_id=participant.id,
        entity_label=participant.display_name,
        verb="created",
        summary="Participant added to the directory. No contact details are stored.",
        actor_id=actor.id if actor else None,
    )
    db.commit()
    db.refresh(participant)
    return participant_out(db, participant)


@router.get("/{participant_id}", response_model=ParticipantDetail)
def get_participant(
    participant_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> ParticipantDetail:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError(f"Participant '{participant_id}' does not exist.")
    assert_participant_read(db, actor, participant_id)
    user = require_actor(actor)
    allowed = visible_project_ids(db, user)

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
    if allowed is not None:
        # The profile aggregates every study this person appears in. Show only
        # the ones this caller may read; otherwise one shared customer would
        # become a window into other teams' projects.
        records = [r for r in records if r.project_id in allowed]
        interview_rows = [(i, p) for i, p in interview_rows if p.id in allowed]

    history: list[ParticipationHistoryItem] = []
    for interview, project in interview_rows:
        evidence_count = db.execute(
            select(func.count(Evidence.id)).where(Evidence.interview_id == interview.id)
        ).scalar_one()
        # Insights are linked through evidence, so resolve the distinct insights
        # that cite anything captured in this conversation.
        insight_count = db.execute(
            select(func.count(func.distinct(InsightEvidence.insight_id)))
            .join(Evidence, Evidence.id == InsightEvidence.evidence_id)
            .where(Evidence.interview_id == interview.id)
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
                insight_count=insight_count,
            )
        )

    feedback_rows = (
        db.execute(
            select(FeedbackRecord, ResearchProject, Interview)
            .join(ResearchProject, ResearchProject.id == FeedbackRecord.project_id)
            .outerjoin(Interview, Interview.id == FeedbackRecord.interview_id)
            .where(FeedbackRecord.participant_id == participant.id)
            .order_by(FeedbackRecord.collected_at.desc())
            .limit(100)
        )
        .all()
    )
    if allowed is not None:
        feedback_rows = [row for row in feedback_rows if row[1].id in allowed]
    feedback_history = [
        ParticipantFeedbackItem(
            id=record.id,
            code=record.code,
            project_id=project.id,
            project_name=project.name,
            source_type=record.source_type,
            collection_method=record.collection_method,
            collected_at=record.collected_at,
            content=record.content,
            interpretation=record.interpretation,
            verification_status=record.verification_status,
            research_depth=feedback_depth(record.collection_method)[0],
            interview_id=interview.id if interview else None,
            interview_code=interview.code if interview else None,
        )
        for record, project, interview in feedback_rows
    ]

    evidence_stmt = select(func.count(Evidence.id)).where(Evidence.participant_id == participant.id)
    if allowed is not None:
        evidence_stmt = evidence_stmt.where(Evidence.project_id.in_(allowed))
    evidence_count = db.execute(evidence_stmt).scalar_one()
    base = participant_out(db, participant)
    return ParticipantDetail(
        **base.model_dump(),
        recruitment=[recruitment_out(db, r) for r in records],
        participation_history=history,
        feedback_history=feedback_history,
        evidence_count=evidence_count,
    )


@router.patch("/{participant_id}", response_model=ParticipantOut)
def update_participant(
    participant_id: str,
    payload: ParticipantUpdate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> ParticipantOut:
    participant = db.get(Participant, participant_id)
    if participant is None:
        raise NotFoundError(f"Participant '{participant_id}' does not exist.")
    assert_participant_write(db, actor, participant_id)
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
    assert_project_write(db, actor, project.id)
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
