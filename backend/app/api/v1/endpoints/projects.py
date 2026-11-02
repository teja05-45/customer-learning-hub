"""Research project endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_actor
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError, RuleViolationError
from app.models import ResearchProject, ResearchQuestion, User
from app.schemas.common import Message
from app.schemas.project import (
    ProjectCreate,
    ProjectDetail,
    ProjectListResponse,
    ProjectTemplate,
    ProjectUpdate,
    QuestionIn,
    QuestionOut,
)
from app.services.activity import log_activity
from app.services.serializers import project_detail, project_summary
from app.services.templates import PROJECT_TEMPLATES

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/templates", response_model=list[ProjectTemplate])
def list_templates() -> list[ProjectTemplate]:
    """Ready-made starting points that encode how this team already works."""
    return PROJECT_TEMPLATES


@router.get("", response_model=ProjectListResponse)
def list_projects(
    db: Session = Depends(get_db),
    pagination: Pagination = Depends(),
    q: str | None = Query(default=None, max_length=120),
    project_status: list[str] | None = Query(default=None, alias="status"),
    priority: list[str] | None = Query(default=None),
    owner_id: str | None = Query(default=None),
    business_function: str | None = Query(default=None),
    include_archived: bool = Query(default=True),
) -> ProjectListResponse:
    stmt = select(ResearchProject)
    if project_status:
        stmt = stmt.where(ResearchProject.status.in_(project_status))
    elif not include_archived:
        stmt = stmt.where(ResearchProject.status != "archived")
    if priority:
        stmt = stmt.where(ResearchProject.priority.in_(priority))
    if owner_id:
        stmt = stmt.where(ResearchProject.owner_id == owner_id)
    if q:
        term = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(ResearchProject.name).like(term),
                func.lower(ResearchProject.objective).like(term),
            )
        )

    stmt = stmt.order_by(ResearchProject.deadline.asc().nulls_last(), ResearchProject.created_at.desc())

    # business_functions is a JSON list, which is not portably filterable in SQL
    # across SQLite and PostgreSQL. Filter before paginating so the reported
    # total matches the rows the caller receives.
    rows = db.execute(stmt).scalars().unique().all()
    if business_function:
        rows = [p for p in rows if business_function in (p.business_functions or [])]
    total = len(rows)
    offset = (pagination.page - 1) * pagination.page_size
    items = [project_summary(db, p) for p in rows[offset : offset + pagination.page_size]]
    return ProjectListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=(total + pagination.page_size - 1) // pagination.page_size if total else 0,
    )


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> ProjectDetail:
    if payload.owner_id and db.get(User, payload.owner_id) is None:
        raise NotFoundError("The selected project owner does not exist.")

    project = ResearchProject(
        name=payload.name.strip(),
        objective=payload.objective.strip(),
        description=payload.description.strip(),
        status=payload.status.value,
        priority=payload.priority.value,
        methodology=payload.methodology,
        owner_id=payload.owner_id,
        business_functions=[f.value for f in payload.business_functions],
        target_segments=[s.value for s in payload.target_segments],
        start_date=payload.start_date,
        deadline=payload.deadline,
    )
    db.add(project)
    db.flush()

    for order, question in enumerate(payload.questions):
        db.add(
            ResearchQuestion(
                project_id=project.id,
                text=question.text.strip(),
                order_index=order,
                is_resolved=question.is_resolved,
                resolution_note=question.resolution_note,
            )
        )
    log_activity(
        db,
        entity_type="project",
        entity_id=project.id,
        entity_label=project.name,
        verb="created",
        summary=f"Research project created with {len(payload.questions)} research question(s).",
        actor_id=actor.id if actor else None,
        project_id=project.id,
    )
    db.commit()
    db.refresh(project)
    return project_detail(db, project)


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectDetail:
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise NotFoundError(f"Research project '{project_id}' does not exist.")
    return project_detail(db, project)


@router.patch("/{project_id}", response_model=ProjectDetail)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> ProjectDetail:
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise NotFoundError(f"Research project '{project_id}' does not exist.")

    data = payload.model_dump(exclude_unset=True)
    if "owner_id" in data and data["owner_id"] and db.get(User, data["owner_id"]) is None:
        raise NotFoundError("The selected project owner does not exist.")

    start = data.get("start_date", project.start_date)
    deadline = data.get("deadline", project.deadline)
    if start and deadline and deadline < start:
        raise RuleViolationError("Deadline cannot be before the start date.")

    if data.get("status") == "archived" and project.status != "archived":
        project.archived_at = datetime.now(timezone.utc)
    if data.get("status") and data["status"] != "archived":
        project.archived_at = None
    if data.get("status") == "completed" and project.completed_at is None:
        project.completed_at = datetime.now(timezone.utc)

    for field, value in data.items():
        if field in ("business_functions", "target_segments") and value is not None:
            setattr(project, field, [v.value if hasattr(v, "value") else v for v in value])
        elif hasattr(value, "value"):
            setattr(project, field, value.value)
        else:
            setattr(project, field, value)

    log_activity(
        db,
        entity_type="project",
        entity_id=project.id,
        entity_label=project.name,
        verb="updated",
        summary=f"Project updated: {', '.join(sorted(data.keys())) or 'no changes'}.",
        actor_id=actor.id if actor else None,
        project_id=project.id,
    )
    db.commit()
    db.refresh(project)
    return project_detail(db, project)


@router.post("/{project_id}/archive", response_model=Message)
def archive_project(
    project_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> Message:
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise NotFoundError(f"Research project '{project_id}' does not exist.")
    if project.status == "archived":
        raise ConflictError("This project is already archived.")
    project.status = "archived"
    project.archived_at = datetime.now(timezone.utc)
    log_activity(
        db,
        entity_type="project",
        entity_id=project.id,
        entity_label=project.name,
        verb="archived",
        summary="Project archived. Evidence and insights remain searchable.",
        actor_id=actor.id if actor else None,
        project_id=project.id,
    )
    db.commit()
    return Message(message="Project archived.", detail="Evidence and insights stay searchable in the library.")


@router.post("/{project_id}/questions", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
def add_question(
    project_id: str,
    payload: QuestionIn,
    db: Session = Depends(get_db),
) -> QuestionOut:
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise NotFoundError(f"Research project '{project_id}' does not exist.")
    question = ResearchQuestion(
        project_id=project.id,
        text=payload.text.strip(),
        order_index=len(project.questions),
        is_resolved=payload.is_resolved,
        resolution_note=payload.resolution_note,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return QuestionOut.model_validate(question)


@router.patch("/{project_id}/questions/{question_id}", response_model=QuestionOut)
def update_question(
    project_id: str,
    question_id: str,
    payload: QuestionIn,
    db: Session = Depends(get_db),
) -> QuestionOut:
    question = db.get(ResearchQuestion, question_id)
    if question is None or question.project_id != project_id:
        raise NotFoundError("That research question does not exist on this project.")
    question.text = payload.text.strip()
    question.is_resolved = payload.is_resolved
    question.resolution_note = payload.resolution_note
    db.commit()
    db.refresh(question)
    return QuestionOut.model_validate(question)


@router.delete("/{project_id}/questions/{question_id}", response_model=Message)
def delete_question(project_id: str, question_id: str, db: Session = Depends(get_db)) -> Message:
    question = db.get(ResearchQuestion, question_id)
    if question is None or question.project_id != project_id:
        raise NotFoundError("That research question does not exist on this project.")
    db.delete(question)
    db.commit()
    return Message(message="Research question removed.")
