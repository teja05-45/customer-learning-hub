"""Decision register endpoints.

The register is deliberately permissive about *recording* a decision and strict
about *labelling* it: a decision with no linked customer source is stored, but
the response carries a warning so no screen can present it as evidence-backed.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_actor
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError, RuleViolationError
from app.models import (
    BusinessAction,
    Decision,
    DecisionEvidence,
    DecisionInsight,
    Evidence,
    Insight,
    ResearchProject,
    User,
)
from app.models.enums import DECISION_TRANSITIONS, DecisionStatus
from app.schemas.common import Message
from app.schemas.decision import (
    ActionCreate,
    ActionOut,
    DecisionCreate,
    DecisionDetail,
    DecisionLinkIn,
    DecisionListResponse,
    DecisionUpdate,
)
from app.schemas.traceability import DecisionTraceability
from app.services.activity import log_activity
from app.services.common import next_code
from app.services.serializers import (
    action_out,
    decision_detail,
    decision_summary,
    decision_traceability,
)

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("", response_model=DecisionListResponse)
def list_decisions(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=160),
    decision_status: list[str] | None = Query(default=None, alias="status"),
    business_function: list[str] | None = Query(default=None),
    project_id: str | None = Query(default=None),
    owner_id: str | None = Query(default=None),
    has_evidence: bool | None = Query(default=None),
    sort: str = Query(default="recent", pattern="^(recent|date|title)$"),
) -> DecisionListResponse:
    stmt = select(Decision)
    if q:
        term = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Decision.title).like(term),
                func.lower(Decision.problem_statement).like(term),
                func.lower(Decision.description).like(term),
                func.lower(Decision.code).like(term),
            )
        )
    if decision_status:
        stmt = stmt.where(Decision.status.in_(decision_status))
    if business_function:
        stmt = stmt.where(Decision.business_function.in_(business_function))
    if project_id:
        stmt = stmt.where(Decision.project_id == project_id)
    if owner_id:
        stmt = stmt.where(Decision.owner_id == owner_id)

    order = {
        "recent": Decision.created_at.desc(),
        "date": Decision.decision_date.desc().nulls_last(),
        "title": Decision.title.asc(),
    }[sort]
    rows = db.execute(stmt.order_by(order)).scalars().unique().all()
    items = [decision_summary(db, d) for d in rows]
    if has_evidence is not None:
        items = [d for d in items if (d.insight_count + d.evidence_count > 0) == has_evidence]

    status_counts = dict(
        db.execute(select(Decision.status, func.count(Decision.id)).group_by(Decision.status)).all()
    )
    unevidenced = len([d for d in items if d.insight_count == 0 and d.evidence_count == 0])
    return DecisionListResponse(items=items, total=len(items), status_counts=status_counts, unevidenced=unevidenced)


@router.post("", response_model=DecisionDetail, status_code=status.HTTP_201_CREATED)
def create_decision(
    payload: DecisionCreate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> DecisionDetail:
    if payload.project_id and db.get(ResearchProject, payload.project_id) is None:
        raise NotFoundError("That research project does not exist.")
    if payload.owner_id and db.get(User, payload.owner_id) is None:
        raise NotFoundError("That decision owner does not exist.")

    decision = Decision(
        code=next_code(db, Decision, "code", "DEC", width=3),
        title=payload.title.strip(),
        business_function=payload.business_function.value,
        problem_statement=payload.problem_statement.strip(),
        description=payload.description.strip(),
        rationale=payload.rationale,
        limitations=payload.limitations,
        project_id=payload.project_id,
        owner_id=payload.owner_id or (actor.id if actor else None),
        decision_date=payload.decision_date,
        status=payload.status.value,
        evidence_sufficient=payload.evidence_sufficient,
    )
    db.add(decision)
    db.flush()

    linked_evidence = 0
    for insight_id in payload.insight_ids:
        insight = db.get(Insight, insight_id)
        if insight is None:
            db.rollback()
            raise NotFoundError(f"Insight '{insight_id}' does not exist.")
        db.add(DecisionInsight(decision_id=decision.id, insight_id=insight.id))
    for evidence_id in payload.evidence_ids:
        evidence = db.get(Evidence, evidence_id)
        if evidence is None:
            db.rollback()
            raise NotFoundError(f"Evidence '{evidence_id}' does not exist.")
        db.add(DecisionEvidence(decision_id=decision.id, evidence_id=evidence.id, role="supporting"))
        linked_evidence += 1

    log_activity(
        db,
        entity_type="decision",
        entity_id=decision.id,
        entity_label=decision.title,
        verb="created",
        summary=(
            f"Decision recorded with {len(payload.insight_ids)} insight(s) and {linked_evidence} evidence item(s)."
            if payload.insight_ids or linked_evidence
            else "Decision recorded without any linked customer evidence."
        ),
        actor_id=actor.id if actor else None,
        project_id=decision.project_id,
    )
    db.commit()
    db.refresh(decision)
    return decision_detail(db, decision)


@router.get("/{decision_id}", response_model=DecisionDetail)
def get_decision(decision_id: str, db: Session = Depends(get_db)) -> DecisionDetail:
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise NotFoundError(f"Decision '{decision_id}' does not exist.")
    return decision_detail(db, decision)


@router.get("/{decision_id}/traceability", response_model=DecisionTraceability)
def get_decision_traceability(decision_id: str, db: Session = Depends(get_db)) -> DecisionTraceability:
    """Walk backwards from the decision to the customer statements behind it."""
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise NotFoundError(f"Decision '{decision_id}' does not exist.")
    return decision_traceability(db, decision)


@router.patch("/{decision_id}", response_model=DecisionDetail)
def update_decision(
    decision_id: str,
    payload: DecisionUpdate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> DecisionDetail:
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise NotFoundError(f"Decision '{decision_id}' does not exist.")

    data = payload.model_dump(exclude_unset=True)
    new_status = data.get("status")
    if new_status is not None and new_status.value != decision.status:
        allowed = {s.value for s in DECISION_TRANSITIONS.get(DecisionStatus(decision.status), set())}
        if new_status.value not in allowed:
            raise RuleViolationError(
                f"Cannot move a decision from '{decision.status}' to '{new_status.value}'.",
                details={"allowed": sorted(allowed)},
            )
        log_activity(
            db,
            entity_type="decision",
            entity_id=decision.id,
            entity_label=decision.title,
            verb="transitioned",
            summary=f"Decision status changed from {decision.status} to {new_status.value}.",
            actor_id=actor.id if actor else None,
            project_id=decision.project_id,
        )

    for field, value in data.items():
        setattr(decision, field, value.value if hasattr(value, "value") else value)
    db.commit()
    db.refresh(decision)
    return decision_detail(db, decision)


@router.post("/{decision_id}/links", response_model=DecisionDetail, status_code=status.HTTP_201_CREATED)
def link_evidence(
    decision_id: str,
    payload: DecisionLinkIn,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> DecisionDetail:
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise NotFoundError(f"Decision '{decision_id}' does not exist.")
    if not payload.insight_ids and not payload.evidence_ids:
        raise RuleViolationError("Provide at least one insight or evidence id to link.")

    added = 0
    for insight_id in payload.insight_ids:
        insight = db.get(Insight, insight_id)
        if insight is None:
            raise NotFoundError(f"Insight '{insight_id}' does not exist.")
        exists = db.execute(
            select(DecisionInsight).where(
                DecisionInsight.decision_id == decision.id, DecisionInsight.insight_id == insight.id
            )
        ).scalar_one_or_none()
        if exists:
            raise ConflictError("That insight is already linked to this decision.")
        db.add(DecisionInsight(decision_id=decision.id, insight_id=insight.id))
        added += 1

    for evidence_id in payload.evidence_ids:
        evidence = db.get(Evidence, evidence_id)
        if evidence is None:
            raise NotFoundError(f"Evidence '{evidence_id}' does not exist.")
        exists = db.execute(
            select(DecisionEvidence).where(
                DecisionEvidence.decision_id == decision.id, DecisionEvidence.evidence_id == evidence.id
            )
        ).scalar_one_or_none()
        if exists:
            raise ConflictError("That evidence is already linked to this decision.")
        db.add(
            DecisionEvidence(decision_id=decision.id, evidence_id=evidence.id, role=payload.role.value)
        )
        added += 1

    # A decision that now cites customer sources is no longer an unassessed
    # internal judgement. An explicit False ("we looked and it is not enough")
    # is a judgement, so it is never overwritten by linking.
    if decision.evidence_sufficient is None:
        decision.evidence_sufficient = True

    log_activity(
        db,
        entity_type="decision",
        entity_id=decision.id,
        entity_label=decision.title,
        verb="linked",
        summary=f"{added} source(s) linked to the decision.",
        actor_id=actor.id if actor else None,
        project_id=decision.project_id,
    )
    db.commit()
    db.refresh(decision)
    return decision_detail(db, decision)


@router.delete("/{decision_id}/links/{kind}/{link_id}", response_model=Message)
def unlink_source(
    decision_id: str,
    kind: str,
    link_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> Message:
    if kind not in ("insight", "evidence"):
        raise RuleViolationError("Link type must be 'insight' or 'evidence'.")
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise NotFoundError(f"Decision '{decision_id}' does not exist.")
    model = DecisionInsight if kind == "insight" else DecisionEvidence
    column = "insight_id" if kind == "insight" else "evidence_id"
    link = db.execute(
        select(model).where(model.decision_id == decision_id, getattr(model, column) == link_id)
    ).scalar_one_or_none()
    if link is None:
        raise NotFoundError("That link does not exist on this decision.")
    db.delete(link)
    db.flush()

    # The flag must not survive the evidence: a decision with no remaining source
    # is an internal judgement, whatever it said before.
    remaining = db.execute(
        select(func.count(DecisionInsight.id)).where(DecisionInsight.decision_id == decision.id)
    ).scalar_one() + db.execute(
        select(func.count(DecisionEvidence.id)).where(DecisionEvidence.decision_id == decision.id)
    ).scalar_one()
    if remaining == 0:
        decision.evidence_sufficient = False

    log_activity(
        db,
        entity_type="decision",
        entity_id=decision.id,
        entity_label=decision.title,
        verb="unlinked",
        summary=(
            f"{kind.title()} link removed; the decision now has {remaining} linked source(s)."
            if remaining
            else f"{kind.title()} link removed; the decision has no customer source left and is marked as an internal judgement."
        ),
        actor_id=actor.id if actor else None,
        project_id=decision.project_id,
    )
    db.commit()
    return Message(message=f"{kind.title()} link removed from the decision.")


@router.post("/{decision_id}/actions", response_model=ActionOut, status_code=status.HTTP_201_CREATED)
def create_action(
    decision_id: str,
    payload: ActionCreate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> ActionOut:
    decision = db.get(Decision, decision_id)
    if decision is None:
        raise NotFoundError(f"Decision '{decision_id}' does not exist.")
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
        decision_id=decision.id,
        insight_id=payload.insight_id,
    )
    db.add(action)
    log_activity(
        db,
        entity_type="action",
        entity_id=action.id,
        entity_label=action.title,
        verb="created",
        summary=f"Follow-up action created from decision {decision.code}.",
        actor_id=actor.id if actor else None,
        project_id=decision.project_id,
    )
    db.commit()
    db.refresh(action)
    return action_out(db, action)
