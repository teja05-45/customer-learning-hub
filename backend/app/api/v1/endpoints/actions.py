"""Follow-up action endpoints."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_actor
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models import BusinessAction, Decision, Insight, User
from app.schemas.common import Message
from app.schemas.decision import ActionCreate, ActionListResponse, ActionOut, ActionUpdate
from app.services.activity import log_activity
from app.services.common import next_code
from app.services.serializers import action_out

router = APIRouter(prefix="/actions", tags=["actions"])


@router.get("", response_model=ActionListResponse)
def list_actions(
    db: Session = Depends(get_db),
    action_status: list[str] | None = Query(default=None, alias="status"),
    owner_id: str | None = Query(default=None),
    decision_id: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=160),
    overdue_only: bool = Query(default=False),
    due_before: date | None = Query(default=None),
) -> ActionListResponse:
    stmt = select(BusinessAction)
    if action_status:
        stmt = stmt.where(BusinessAction.status.in_(action_status))
    if owner_id:
        stmt = stmt.where(BusinessAction.owner_id == owner_id)
    if decision_id:
        stmt = stmt.where(BusinessAction.decision_id == decision_id)
    if q:
        term = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(func.lower(BusinessAction.title).like(term), func.lower(BusinessAction.code).like(term))
        )
    if overdue_only:
        stmt = stmt.where(
            BusinessAction.due_date.is_not(None),
            BusinessAction.due_date < date.today(),
            BusinessAction.status != "completed",
        )
    if due_before:
        stmt = stmt.where(BusinessAction.due_date <= due_before)

    rows = db.execute(
        stmt.order_by(BusinessAction.due_date.asc().nulls_last(), BusinessAction.created_at.desc())
    ).scalars().unique().all()
    items = [action_out(db, a) for a in rows]
    status_counts = dict(
        db.execute(select(BusinessAction.status, func.count(BusinessAction.id)).group_by(BusinessAction.status)).all()
    )
    return ActionListResponse(
        items=items,
        total=len(items),
        status_counts=status_counts,
        overdue=len([i for i in items if i.is_overdue]),
    )


@router.post("", response_model=ActionOut, status_code=status.HTTP_201_CREATED)
def create_action(
    payload: ActionCreate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> ActionOut:
    if payload.decision_id and db.get(Decision, payload.decision_id) is None:
        raise NotFoundError("That decision does not exist.")
    if payload.insight_id and db.get(Insight, payload.insight_id) is None:
        raise NotFoundError("That insight does not exist.")
    if payload.owner_id and db.get(User, payload.owner_id) is None:
        raise NotFoundError("That action owner does not exist.")

    action = BusinessAction(
        code=next_code(db, BusinessAction, "code", "ACT", width=3),
        title=payload.title.strip(),
        description=payload.description,
        owner_id=payload.owner_id or (actor.id if actor else None),
        due_date=payload.due_date,
        priority=payload.priority.value,
        status=payload.status.value,
        decision_id=payload.decision_id,
        insight_id=payload.insight_id,
    )
    db.add(action)
    project_id = None
    if payload.decision_id:
        decision = db.get(Decision, payload.decision_id)
        project_id = decision.project_id if decision else None
    log_activity(
        db,
        entity_type="action",
        entity_id=action.id,
        entity_label=action.title,
        verb="created",
        summary="Follow-up action created with an owner and a due date.",
        actor_id=actor.id if actor else None,
        project_id=project_id,
    )
    db.commit()
    db.refresh(action)
    return action_out(db, action)


@router.get("/{action_id}", response_model=ActionOut)
def get_action(action_id: str, db: Session = Depends(get_db)) -> ActionOut:
    action = db.get(BusinessAction, action_id)
    if action is None:
        raise NotFoundError(f"Action '{action_id}' does not exist.")
    return action_out(db, action)


@router.patch("/{action_id}", response_model=ActionOut)
def update_action(
    action_id: str,
    payload: ActionUpdate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> ActionOut:
    action = db.get(BusinessAction, action_id)
    if action is None:
        raise NotFoundError(f"Action '{action_id}' does not exist.")
    data = payload.model_dump(exclude_unset=True)
    if data.get("owner_id") and db.get(User, data["owner_id"]) is None:
        raise NotFoundError("That action owner does not exist.")

    previous_status = action.status
    for field, value in data.items():
        setattr(action, field, value.value if hasattr(value, "value") else value)

    if action.status == "completed" and previous_status != "completed":
        action.completed_at = datetime.now(timezone.utc)
    if action.status != "completed":
        action.completed_at = None

    log_activity(
        db,
        entity_type="action",
        entity_id=action.id,
        entity_label=action.title,
        verb="updated",
        summary=(
            f"Action moved from {previous_status.replace('_', ' ')} to {action.status.replace('_', ' ')}."
            if action.status != previous_status
            else f"Action updated: {', '.join(sorted(data.keys())) or 'no changes'}."
        ),
        actor_id=actor.id if actor else None,
        project_id=action.decision.project_id if action.decision else None,
    )
    db.commit()
    db.refresh(action)
    return action_out(db, action)


@router.delete("/{action_id}", response_model=Message)
def delete_action(action_id: str, db: Session = Depends(get_db)) -> Message:
    action = db.get(BusinessAction, action_id)
    if action is None:
        raise NotFoundError(f"Action '{action_id}' does not exist.")
    db.delete(action)
    db.commit()
    return Message(message="Action deleted.", detail="The decision it belonged to is unchanged.")
