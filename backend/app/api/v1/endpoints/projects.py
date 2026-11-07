"""Research project endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_actor
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError, RuleViolationError
from app.models import ProjectMembership, ResearchProject, ResearchQuestion, User
from app.schemas.common import Message, Ref
from app.schemas.membership import MembershipIn, MembershipOut, MembershipUpdate
from app.services.access import (
    assert_project_manage,
    assert_project_read,
    assert_project_write,
    membership_for,
    require_actor,
    role_for,
    visible_project_ids,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectDetail,
    ProjectListResponse,
    ProjectTemplate,
    ProjectUpdate,
    QuestionIn,
    QuestionOut,
)
from app.schemas.journey import ProjectJourney
from app.services.activity import log_activity
from app.services.journey import build_journey
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
    actor: User | None = Depends(get_actor),
    pagination: Pagination = Depends(),
    q: str | None = Query(default=None, max_length=120),
    project_status: list[str] | None = Query(default=None, alias="status"),
    priority: list[str] | None = Query(default=None),
    owner_id: str | None = Query(default=None),
    business_function: str | None = Query(default=None),
    include_archived: bool = Query(default=True),
) -> ProjectListResponse:
    user = require_actor(actor)
    allowed = visible_project_ids(db, user)
    stmt = select(ResearchProject)
    if allowed is not None:
        # Workspace-wide reads were the original vulnerability: a signed-in
        # viewer could list every project. Scope the query before filters and
        # pagination so the reported total matches what the caller may see.
        if not allowed:
            return ProjectListResponse(
                items=[], total=0, page=pagination.page, page_size=pagination.page_size, pages=0
            )
        stmt = stmt.where(ResearchProject.id.in_(allowed))
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
    items = [
        project_summary(db, p, role=role_for(db, user, p.id))
        for p in rows[offset : offset + pagination.page_size]
    ]
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
    creator = require_actor(actor)
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

    # Whoever creates a project owns it. The nominated owner also gets an
    # explicit grant, so ownership survives the creator losing interest.
    db.add(
        ProjectMembership(
            project_id=project.id, user_id=creator.id, role="project_owner", granted_by_id=creator.id
        )
    )
    if payload.owner_id and payload.owner_id != creator.id:
        db.add(
            ProjectMembership(
                project_id=project.id,
                user_id=payload.owner_id,
                role="project_owner",
                granted_by_id=creator.id,
            )
        )

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
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> ProjectDetail:
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise NotFoundError(f"Research project '{project_id}' does not exist.")
    assert_project_read(db, actor, project_id)
    return project_detail(db, project, role=role_for(db, require_actor(actor), project_id))


@router.get("/{project_id}/journey", response_model=ProjectJourney)
def get_project_journey(
    project_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> ProjectJourney:
    """A derived board and timeline from the project's real records.

    This is deliberately read-only: the next action is always taken on the
    entity's own page, so the same permissions and transition rules apply.
    """
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise NotFoundError(f"Research project '{project_id}' does not exist.")
    assert_project_read(db, actor, project_id)
    return build_journey(db, project)


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
    assert_project_write(db, actor, project_id)
    editor = require_actor(actor)

    data = payload.model_dump(exclude_unset=True)
    if "owner_id" in data and data["owner_id"] and db.get(User, data["owner_id"]) is None:
        raise NotFoundError("The selected project owner does not exist.")

    if data.get("owner_id") and data["owner_id"] != project.owner_id:
        existing = membership_for(db, data["owner_id"], project.id)
        if existing is None:
            db.add(
                ProjectMembership(
                    project_id=project.id,
                    user_id=data["owner_id"],
                    role="project_owner",
                    granted_by_id=editor.id,
                )
            )
        else:
            existing.role = "project_owner"

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
    assert_project_manage(db, actor, project_id)
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
    actor: User | None = Depends(get_actor),
) -> QuestionOut:
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise NotFoundError(f"Research project '{project_id}' does not exist.")
    assert_project_write(db, actor, project_id)
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
    actor: User | None = Depends(get_actor),
) -> QuestionOut:
    assert_project_write(db, actor, project_id)
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
def delete_question(
    project_id: str,
    question_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> Message:
    assert_project_write(db, actor, project_id)
    question = db.get(ResearchQuestion, question_id)
    if question is None or question.project_id != project_id:
        raise NotFoundError("That research question does not exist on this project.")
    db.delete(question)
    db.commit()
    return Message(message="Research question removed.")


# ------------------------------------------------------------ project members
def _membership_out(db: Session, membership: ProjectMembership) -> MembershipOut:
    user = db.get(User, membership.user_id)
    return MembershipOut(
        id=membership.id,
        project_id=membership.project_id,
        user=Ref(
            id=membership.user_id,
            label=user.name if user else "Unknown member",
            sublabel=user.job_title if user else None,
        ),
        role=membership.role,
        created_at=membership.created_at,
        email=user.email if user else "",
    )


@router.get("/{project_id}/members", response_model=list[MembershipOut])
def list_project_members(
    project_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> list[MembershipOut]:
    """Who can see this project. Readable by anyone with access, because a
    researcher needs to know who else is working on the study."""
    assert_project_read(db, actor, project_id)
    rows = (
        db.execute(
            select(ProjectMembership)
            .where(ProjectMembership.project_id == project_id)
            .order_by(ProjectMembership.role.desc(), ProjectMembership.created_at.asc())
        )
        .scalars()
        .all()
    )
    return [_membership_out(db, row) for row in rows]


@router.post("/{project_id}/members", response_model=MembershipOut, status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: str,
    payload: MembershipIn,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> MembershipOut:
    assert_project_manage(db, actor, project_id)
    manager = require_actor(actor)
    target = db.get(User, payload.user_id)
    if target is None or not target.is_active:
        raise NotFoundError("That team member does not exist or is inactive.")

    existing = membership_for(db, target.id, project_id)
    if existing is not None:
        existing.role = payload.role.value
        db.commit()
        db.refresh(existing)
        return _membership_out(db, existing)

    membership = ProjectMembership(
        project_id=project_id,
        user_id=target.id,
        role=payload.role.value,
        granted_by_id=manager.id,
    )
    db.add(membership)
    log_activity(
        db,
        entity_type="project",
        entity_id=project_id,
        entity_label=f"Project {project_id}",
        verb="member_added",
        summary=f"{target.name} was granted {payload.role.value.replace('_', ' ')} access.",
        actor_id=manager.id,
        project_id=project_id,
    )
    db.commit()
    db.refresh(membership)
    return _membership_out(db, membership)


def _owner_count(db: Session, project_id: str) -> int:
    return len(
        [
            row
            for row in db.execute(
                select(ProjectMembership).where(
                    ProjectMembership.project_id == project_id,
                    ProjectMembership.role == "project_owner",
                )
            ).scalars()
        ]
    )


@router.patch("/{project_id}/members/{membership_id}", response_model=MembershipOut)
def update_project_member(
    project_id: str,
    membership_id: str,
    payload: MembershipUpdate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> MembershipOut:
    assert_project_manage(db, actor, project_id)
    membership = db.get(ProjectMembership, membership_id)
    if membership is None or membership.project_id != project_id:
        raise NotFoundError("That membership does not exist on this project.")
    if membership.role == "project_owner" and payload.role.value != "project_owner":
        if _owner_count(db, project_id) <= 1:
            raise ConflictError(
                "A project must keep at least one owner. Grant another owner before changing this one."
            )
    membership.role = payload.role.value
    db.commit()
    db.refresh(membership)
    return _membership_out(db, membership)


@router.delete("/{project_id}/members/{membership_id}", response_model=Message)
def remove_project_member(
    project_id: str,
    membership_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> Message:
    assert_project_manage(db, actor, project_id)
    membership = db.get(ProjectMembership, membership_id)
    if membership is None or membership.project_id != project_id:
        raise NotFoundError("That membership does not exist on this project.")
    if membership.role == "project_owner" and _owner_count(db, project_id) <= 1:
        raise ConflictError(
            "A project must keep at least one owner. Grant another owner before removing this one."
        )
    db.delete(membership)
    db.commit()
    return Message(message="Project access removed.")
