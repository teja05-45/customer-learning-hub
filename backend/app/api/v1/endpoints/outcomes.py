"""Outcome measurement endpoints.

This closes the learning loop: a decision is not finished when the action ships,
it is finished when someone records whether the expected change happened.

Rules enforced here, rather than only in the UI:

* an outcome must belong to a decision and, optionally, one of its actions;
* a measured status needs an actual value and a recorded-at timestamp;
* the status is derived from the baseline/target/actual values and the stated
  direction, so a target cannot be quietly reinterpreted after the result;
* every change is written to the audit trail.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_actor
from app.core.database import get_db
from app.core.errors import NotFoundError, RuleViolationError
from app.models import BusinessAction, Decision, Outcome, ResearchProject, User
from app.models.enums import OutcomeStatus
from app.schemas.outcome import OutcomeCreate, OutcomeListResponse, OutcomeOut, OutcomeUpdate
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

router = APIRouter(prefix="/outcomes", tags=["outcomes"])

MEASURED_STATUSES = {
    OutcomeStatus.ACHIEVED.value,
    OutcomeStatus.NOT_ACHIEVED.value,
    OutcomeStatus.INCONCLUSIVE.value,
}


def _ref_outcome(db: Session, outcome: Outcome) -> OutcomeOut:
    decision = db.get(Decision, outcome.decision_id)
    action = db.get(BusinessAction, outcome.action_id) if outcome.action_id else None
    owner = db.get(User, outcome.owner_id) if outcome.owner_id else None
    project_id = decision.project_id if decision else None
    project = db.get(ResearchProject, project_id) if project_id else None

    is_overdue = bool(
        outcome.measurement_end
        and outcome.measurement_end < date.today()
        and outcome.status not in MEASURED_STATUSES
    )
    reason = ""
    if outcome.status == OutcomeStatus.PLANNED.value:
        reason = "The measurement window has not started. No result is claimed."
    elif outcome.status == OutcomeStatus.MEASUREMENT_PENDING.value:
        reason = "The measurement window is open or the result has not been recorded yet."
    elif outcome.status in MEASURED_STATUSES:
        reason = (
            f"Measured against target {outcome.target_value}{(' ' + outcome.unit) if outcome.unit else ''} "
            f"using the {outcome.direction} rule."
        )

    return OutcomeOut(
        id=outcome.id,
        code=outcome.code,
        name=outcome.name,
        decision_id=outcome.decision_id,
        action_id=outcome.action_id,
        metric_definition=outcome.metric_definition,
        baseline_value=outcome.baseline_value,
        target_value=outcome.target_value,
        actual_value=outcome.actual_value,
        unit=outcome.unit,
        direction=outcome.direction,
        measurement_start=outcome.measurement_start,
        measurement_end=outcome.measurement_end,
        status=outcome.status,
        owner_id=outcome.owner_id,
        data_source=outcome.data_source,
        recorded_at=outcome.recorded_at,
        notes=outcome.notes,
        created_at=outcome.created_at,
        updated_at=outcome.updated_at,
        decision=(
            {"id": decision.id, "label": decision.title, "sublabel": decision.code} if decision else None
        ),
        action=(
            {"id": action.id, "label": action.title, "sublabel": action.code} if action else None
        ),
        owner=(
            {"id": owner.id, "label": owner.name, "sublabel": owner.job_title or owner.role}
            if owner
            else None
        ),
        project_id=project_id,
        is_overdue=is_overdue,
        status_reason=reason,
    )


def _derive_status(
    *,
    actual_value: float | None,
    target_value: float | None,
    direction: str,
    measurement_start: date | None,
    explicit: str | None,
) -> tuple[str, str | None]:
    """Return (status, recorded_result_reason).

    A supplied actual value is authoritative. Without one, the workflow can only
    be planned or pending; an explicit achieved/not-achieved claim is refused,
    because an outcome without a result is a hope, not a measurement.
    """
    if actual_value is None:
        if explicit in MEASURED_STATUSES:
            return "", "Record the actual result before marking this outcome measured."
        if explicit in (OutcomeStatus.PLANNED.value, OutcomeStatus.MEASUREMENT_PENDING.value):
            return explicit, None
        if measurement_start and measurement_start <= date.today():
            return OutcomeStatus.MEASUREMENT_PENDING.value, None
        return OutcomeStatus.PLANNED.value, None

    if target_value is None:
        return OutcomeStatus.INCONCLUSIVE.value, "A target is required before a result can be judged."

    if direction == "decrease":
        achieved = actual_value <= target_value
    else:
        achieved = actual_value >= target_value
    return (
        OutcomeStatus.ACHIEVED.value if achieved else OutcomeStatus.NOT_ACHIEVED.value,
        None,
    )


@router.get("", response_model=OutcomeListResponse)
def list_outcomes(
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
    decision_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    outcome_status: list[str] | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=120),
) -> OutcomeListResponse:
    user = require_actor(actor)
    allowed = visible_project_ids(db, user)
    stmt = select(Outcome)
    if allowed is not None:
        if not allowed:
            return OutcomeListResponse(items=[], total=0, status_counts={}, measurement_due=0)
        stmt = stmt.where(
            Outcome.decision_id.in_(select(Decision.id).where(Decision.project_id.in_(allowed)))
        )
    if decision_id:
        stmt = stmt.where(Outcome.decision_id == decision_id)
    if project_id:
        assert_project_read(db, user, project_id)
        stmt = stmt.where(
            Outcome.decision_id.in_(select(Decision.id).where(Decision.project_id == project_id))
        )
    if outcome_status:
        stmt = stmt.where(Outcome.status.in_(outcome_status))
    if q:
        term = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Outcome.name).like(term),
                func.lower(Outcome.metric_definition).like(term),
                func.lower(Outcome.code).like(term),
            )
        )
    rows = db.execute(stmt.order_by(Outcome.created_at.desc())).scalars().unique().all()
    items = [_ref_outcome(db, row) for row in rows]
    status_counts: dict[str, int] = {}
    for item in items:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1
    due = len([item for item in items if item.is_overdue])
    return OutcomeListResponse(items=items, total=len(items), status_counts=status_counts, measurement_due=due)


@router.post("", response_model=OutcomeOut, status_code=status.HTTP_201_CREATED)
def create_outcome(
    payload: OutcomeCreate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> OutcomeOut:
    decision = db.get(Decision, payload.decision_id)
    if decision is None:
        raise NotFoundError("That decision does not exist.")
    assert_project_write(db, actor, decision.project_id)
    if payload.action_id:
        action = db.get(BusinessAction, payload.action_id)
        if action is None:
            raise NotFoundError("That action does not exist.")
        if action.decision_id != decision.id:
            raise RuleViolationError("The action belongs to a different decision.")
    if payload.owner_id and db.get(User, payload.owner_id) is None:
        raise NotFoundError("That outcome owner does not exist.")

    derived, refusal = _derive_status(
        actual_value=payload.actual_value,
        target_value=payload.target_value,
        direction=payload.direction.value,
        measurement_start=payload.measurement_start,
        explicit=payload.status.value if payload.status else None,
    )
    if refusal and not derived:
        raise RuleViolationError(refusal)

    status_value = derived
    if payload.actual_value is not None and payload.status:
        if payload.status.value in (OutcomeStatus.PLANNED.value, OutcomeStatus.MEASUREMENT_PENDING.value):
            raise RuleViolationError(
                "A recorded result cannot be left as planned or pending. Record it as achieved, "
                "not achieved, or inconclusive."
            )
        # An explicit inconclusive is a judgement and is respected; achieved /
        # not achieved must agree with the stated target rule.
        if payload.status.value != OutcomeStatus.INCONCLUSIVE.value and derived != payload.status.value:
            raise RuleViolationError(
                "The recorded result does not match the target and direction. "
                "Update the target or record the outcome as inconclusive."
            )
        status_value = payload.status.value

    outcome = Outcome(
        code=next_code(db, Outcome, "code", "OUT", width=3),
        name=payload.name.strip(),
        decision_id=decision.id,
        action_id=payload.action_id,
        metric_definition=payload.metric_definition.strip(),
        baseline_value=payload.baseline_value,
        target_value=payload.target_value,
        actual_value=payload.actual_value,
        unit=payload.unit.strip(),
        direction=payload.direction.value,
        measurement_start=payload.measurement_start,
        measurement_end=payload.measurement_end,
        status=status_value,
        owner_id=payload.owner_id or decision.owner_id,
        data_source=payload.data_source.strip(),
        recorded_at=datetime.now(timezone.utc) if payload.actual_value is not None else None,
        notes=payload.notes,
    )
    db.add(outcome)
    log_activity(
        db,
        entity_type="outcome",
        entity_id=outcome.id,
        entity_label=f"{outcome.code} · {outcome.name}",
        verb="created",
        summary=(
            f"Outcome planned for decision {decision.code}."
            if payload.actual_value is None
            else f"Outcome recorded with result {payload.actual_value}{(' ' + outcome.unit) if outcome.unit else ''}."
        ),
        actor_id=actor.id if actor else None,
        project_id=decision.project_id,
    )
    db.commit()
    db.refresh(outcome)
    return _ref_outcome(db, outcome)


@router.get("/{outcome_id}", response_model=OutcomeOut)
def get_outcome(
    outcome_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> OutcomeOut:
    outcome = db.get(Outcome, outcome_id)
    if outcome is None:
        raise NotFoundError(f"Outcome '{outcome_id}' does not exist.")
    decision = db.get(Decision, outcome.decision_id)
    assert_entity_read(db, actor, decision.project_id if decision else None)
    return _ref_outcome(db, outcome)


@router.patch("/{outcome_id}", response_model=OutcomeOut)
def update_outcome(
    outcome_id: str,
    payload: OutcomeUpdate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> OutcomeOut:
    outcome = db.get(Outcome, outcome_id)
    if outcome is None:
        raise NotFoundError(f"Outcome '{outcome_id}' does not exist.")
    owning_decision = db.get(Decision, outcome.decision_id)
    assert_entity_write(db, actor, owning_decision.project_id if owning_decision else None)

    data = payload.model_dump(exclude_unset=True)
    if "action_id" in data and data["action_id"]:
        action = db.get(BusinessAction, data["action_id"])
        if action is None:
            raise NotFoundError("That action does not exist.")
        if action.decision_id != outcome.decision_id:
            raise RuleViolationError("The action belongs to a different decision.")
    if "owner_id" in data and data["owner_id"] and db.get(User, data["owner_id"]) is None:
        raise NotFoundError("That outcome owner does not exist.")

    start = data.get("measurement_start", outcome.measurement_start)
    end = data.get("measurement_end", outcome.measurement_end)
    if start and end and end < start:
        raise RuleViolationError("The measurement end date cannot be before the start date.")

    previous_status = outcome.status
    explicit_status = data.pop("status", None)
    explicit_value = explicit_status.value if hasattr(explicit_status, "value") else explicit_status

    for field, value in data.items():
        setattr(outcome, field, value.value if hasattr(value, "value") else value)

    if outcome.actual_value is not None and outcome.recorded_at is None:
        outcome.recorded_at = datetime.now(timezone.utc)
    if outcome.actual_value is None:
        outcome.recorded_at = None

    derived, refusal = _derive_status(
        actual_value=outcome.actual_value,
        target_value=outcome.target_value,
        direction=outcome.direction,
        measurement_start=outcome.measurement_start,
        explicit=explicit_value,
    )
    if refusal and not derived:
        db.rollback()
        raise RuleViolationError(refusal)
    if outcome.actual_value is not None and explicit_value in (
        OutcomeStatus.PLANNED.value,
        OutcomeStatus.MEASUREMENT_PENDING.value,
    ):
        db.rollback()
        raise RuleViolationError(
            "A recorded result cannot be left as planned or pending. Record it as achieved, "
            "not achieved, or inconclusive."
        )
    outcome.status = (
        explicit_value
        if outcome.actual_value is not None and explicit_value == OutcomeStatus.INCONCLUSIVE.value
        else derived
    )

    decision = db.get(Decision, outcome.decision_id)
    if previous_status != outcome.status:
        log_activity(
            db,
            entity_type="outcome",
            entity_id=outcome.id,
            entity_label=f"{outcome.code} · {outcome.name}",
            verb="measured" if outcome.status in MEASURED_STATUSES else "updated",
            summary=f"Outcome status changed from {previous_status} to {outcome.status}.",
            actor_id=actor.id if actor else None,
            project_id=decision.project_id if decision else None,
        )
    else:
        log_activity(
            db,
            entity_type="outcome",
            entity_id=outcome.id,
            entity_label=f"{outcome.code} · {outcome.name}",
            verb="updated",
            summary=f"Outcome updated: {', '.join(sorted(data.keys())) or 'no field changes'}.",
            actor_id=actor.id if actor else None,
            project_id=decision.project_id if decision else None,
        )
    db.commit()
    db.refresh(outcome)
    return _ref_outcome(db, outcome)
