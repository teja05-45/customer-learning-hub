"""Insight library endpoints.

"Validated for internal use" is a review action, not a claim of statistical
representativeness. The API enforces that at least one evidence item is linked
before an insight can be validated.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_actor
from app.core.database import get_db
from app.core.errors import ConflictError, NotFoundError, RuleViolationError
from app.models import Evidence, Insight, InsightEvidence, ResearchProject, User
from app.models.enums import Confidence
from app.schemas.common import Message
from app.schemas.dashboard import SearchResult
from app.schemas.insight import (
    EvidenceLinkIn,
    EvidenceLinkUpdate,
    InsightCreate,
    InsightDetail,
    InsightListResponse,
    InsightSummary,
    InsightUpdate,
)
from app.schemas.traceability import (
    InsightEvidenceResponse,
    InsightTraceability,
    RelationshipWriteResponse,
)
from app.services.access import (
    assert_entity_read,
    assert_entity_write,
    assert_project_read,
    assert_project_write,
    is_workspace_admin,
    require_actor,
    visible_project_ids,
)
from app.services.activity import log_activity
from app.services.common import next_code
from app.services.search import suggest_related
from app.services.serializers import (
    insight_detail,
    insight_evidence_link_out,
    insight_evidence_response,
    insight_is_reused,
    insight_summary,
    insight_traceability,
    user_map,
)

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=InsightListResponse)
def list_insights(
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
    q: str | None = Query(default=None, max_length=160),
    project_id: str | None = Query(default=None),
    insight_status: list[str] | None = Query(default=None, alias="status"),
    segment: list[str] | None = Query(default=None),
    confidence: list[str] | None = Query(default=None),
    owner_id: str | None = Query(default=None),
    sort: str = Query(default="recent", pattern="^(recent|evidence|confidence|title)$"),
) -> InsightListResponse:
    user = require_actor(actor)
    allowed = visible_project_ids(db, user)
    stmt = select(Insight)
    if allowed is not None:
        if not allowed:
            return InsightListResponse(items=[], total=0, status_counts={})
        stmt = stmt.where(Insight.project_id.in_(allowed))
    if q:
        term = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Insight.title).like(term),
                func.lower(Insight.summary).like(term),
                func.lower(Insight.research_question).like(term),
                func.lower(Insight.code).like(term),
            )
        )
    if project_id:
        assert_project_read(db, user, project_id)
        stmt = stmt.where(Insight.project_id == project_id)
    if insight_status:
        stmt = stmt.where(Insight.status.in_(insight_status))
    if confidence:
        stmt = stmt.where(Insight.confidence.in_(confidence))
    if owner_id:
        stmt = stmt.where(Insight.owner_id == owner_id)

    stmt = stmt.order_by(Insight.created_at.desc())
    rows = db.execute(stmt).scalars().unique().all()
    items = [insight_summary(db, i) for i in rows]
    if segment:
        items = [i for i in items if set(segment) & set(i.segments)]

    if sort == "evidence":
        items.sort(key=lambda i: i.evidence_count, reverse=True)
    elif sort == "title":
        items.sort(key=lambda i: i.title.lower())
    elif sort == "confidence":
        order = {Confidence.LOW: 0, Confidence.MEDIUM: 1, Confidence.HIGH: 2}
        items.sort(key=lambda i: order.get(Confidence(i.confidence), 0), reverse=True)

    # Counts must describe the visible rows, not the whole workspace.
    status_counts: dict[str, int] = {}
    for item in items:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1
    return InsightListResponse(items=items, total=len(items), status_counts=status_counts)


@router.post("", response_model=InsightDetail, status_code=status.HTTP_201_CREATED)
def create_insight(
    payload: InsightCreate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> InsightDetail:
    creator = require_actor(actor)
    if payload.project_id:
        if db.get(ResearchProject, payload.project_id) is None:
            raise NotFoundError("That research project does not exist.")
        assert_project_write(db, creator, payload.project_id)
    elif not is_workspace_admin(creator):
        raise RuleViolationError("An insight must belong to a project you can access.")
    if payload.owner_id and db.get(User, payload.owner_id) is None:
        raise NotFoundError("That insight owner does not exist.")
    if payload.status.value == "validated_internal" and not payload.evidence_ids:
        raise RuleViolationError(
            "An insight cannot be validated without at least one linked evidence item.",
            details={"field": "evidence_ids"},
        )

    insight = Insight(
        code=next_code(db, Insight, "code", "INS"),
        title=payload.title.strip(),
        summary=payload.summary.strip(),
        interpretation=payload.interpretation.strip(),
        research_question=payload.research_question,
        project_id=payload.project_id,
        status=payload.status.value,
        confidence=payload.confidence.value,
        owner_id=payload.owner_id or (actor.id if actor else None),
        limitations=payload.limitations,
        segments=[s.value for s in payload.segments],
        validated_at=datetime.now(timezone.utc) if payload.status.value == "validated_internal" else None,
        validated_by_id=(actor.id if actor else None) if payload.status.value == "validated_internal" else None,
    )
    db.add(insight)
    db.flush()

    for evidence_id in payload.evidence_ids:
        evidence = db.get(Evidence, evidence_id)
        if evidence is None:
            db.rollback()
            raise NotFoundError(f"Evidence '{evidence_id}' does not exist.")
        assert_project_read(db, creator, evidence.project_id)
        if evidence.project_id != payload.project_id and payload.project_id:
            raise RuleViolationError(
                "Evidence from a different research project cannot be linked to this insight.",
                details={"evidence_id": evidence_id},
            )
        db.add(
            InsightEvidence(
                insight_id=insight.id,
                evidence_id=evidence.id,
                role="supporting",
                created_by_id=actor.id if actor else None,
            )
        )

    log_activity(
        db,
        entity_type="insight",
        entity_id=insight.id,
        entity_label=insight.title,
        verb="created",
        summary=f"Insight created with {len(payload.evidence_ids)} linked evidence item(s).",
        actor_id=actor.id if actor else None,
        project_id=insight.project_id,
    )
    db.commit()
    db.refresh(insight)
    return insight_detail(db, insight)


@router.get("/{insight_id}", response_model=InsightDetail)
def get_insight(
    insight_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> InsightDetail:
    insight = db.get(Insight, insight_id)
    if insight is None:
        raise NotFoundError(f"Insight '{insight_id}' does not exist.")
    assert_entity_read(db, actor, insight.project_id)
    return insight_detail(db, insight)


@router.patch("/{insight_id}", response_model=InsightDetail)
def update_insight(
    insight_id: str,
    payload: InsightUpdate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> InsightDetail:
    insight = db.get(Insight, insight_id)
    if insight is None:
        raise NotFoundError(f"Insight '{insight_id}' does not exist.")
    assert_entity_write(db, actor, insight.project_id)

    data = payload.model_dump(exclude_unset=True)
    if data.get("status") == "validated_internal" and insight.status != "validated_internal":
        linked = db.execute(
            select(func.count(InsightEvidence.id)).where(InsightEvidence.insight_id == insight.id)
        ).scalar_one()
        if linked == 0:
            raise RuleViolationError(
                "An insight cannot be validated without at least one linked evidence item.",
                details={"field": "evidence_ids"},
            )
        insight.validated_at = datetime.now(timezone.utc)
        insight.validated_by_id = actor.id if actor else None
        log_activity(
            db,
            entity_type="insight",
            entity_id=insight.id,
            entity_label=insight.title,
            verb="validated",
            summary="Insight reviewed and validated for internal use. This does not imply representativeness.",
            actor_id=actor.id if actor else None,
            project_id=insight.project_id,
        )
    if data.get("status") and data["status"] != "validated_internal":
        insight.validated_at = None
        insight.validated_by_id = None

    for field, value in data.items():
        if field == "segments" and value is not None:
            insight.segments = [v.value if hasattr(v, "value") else v for v in value]
        else:
            setattr(insight, field, value.value if hasattr(value, "value") else value)
    db.commit()
    db.refresh(insight)
    return insight_detail(db, insight)


def _resolve_relationship(db: Session, insight_id: str, identifier: str) -> InsightEvidence:
    """Find one relationship by relationship id, falling back to evidence id.

    A unique constraint allows at most one relationship per insight/evidence
    pair, so the evidence id is a valid natural key too. Accepting both keeps the
    original ``DELETE /insights/{id}/evidence/{evidence_id}`` call sites working
    while the UI moves to relationship ids.
    """
    link = db.execute(
        select(InsightEvidence).where(
            InsightEvidence.insight_id == insight_id, InsightEvidence.id == identifier
        )
    ).scalar_one_or_none()
    if link is None:
        link = db.execute(
            select(InsightEvidence).where(
                InsightEvidence.insight_id == insight_id,
                InsightEvidence.evidence_id == identifier,
            )
        ).scalar_one_or_none()
    if link is None:
        raise NotFoundError("That evidence relationship does not exist on this insight.")
    return link


def _validate_link(db: Session, insight: Insight, evidence: Evidence) -> None:
    """Every rule that decides whether two records may be related."""
    if insight.project_id and evidence.project_id != insight.project_id:
        raise RuleViolationError(
            "Evidence from a different research project cannot be linked to this insight.",
            details={"evidence_id": evidence.id, "evidence_project_id": evidence.project_id},
        )
    if not evidence.content.strip():
        raise RuleViolationError(
            "That evidence has no customer statement, so it cannot support or contradict anything.",
            details={"evidence_id": evidence.id},
        )


@router.post("/{insight_id}/evidence", response_model=InsightDetail, status_code=status.HTTP_201_CREATED)
def link_evidence(
    insight_id: str,
    payload: EvidenceLinkIn,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> InsightDetail:
    insight = db.get(Insight, insight_id)
    if insight is None:
        raise NotFoundError(f"Insight '{insight_id}' does not exist.")
    assert_entity_write(db, actor, insight.project_id)
    evidence = db.get(Evidence, payload.evidence_id)
    if evidence is None:
        raise NotFoundError(f"Evidence '{payload.evidence_id}' does not exist.")
    # A cross-project link would leak one project's evidence into another's
    # insight; both sides must be visible, and they must match.
    assert_entity_read(db, actor, evidence.project_id)
    _validate_link(db, insight, evidence)

    existing = db.execute(
        select(InsightEvidence).where(
            InsightEvidence.insight_id == insight.id, InsightEvidence.evidence_id == evidence.id
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictError(
            "That evidence is already linked to this insight. Update the existing relationship instead.",
            details={"relationship_id": existing.id, "classification": existing.role},
        )

    link = InsightEvidence(
        insight_id=insight.id,
        evidence_id=evidence.id,
        role=payload.role.value,
        note=payload.note,
        rationale=payload.rationale.strip(),
        confidence=payload.confidence.value if payload.confidence else None,
        tags=payload.tags,
        created_by_id=actor.id if actor else None,
    )
    db.add(link)
    log_activity(
        db,
        entity_type="insight",
        entity_id=insight.id,
        entity_label=insight.title,
        verb="linked",
        summary=(
            f"{evidence.code} linked as {payload.role.value} evidence"
            + (f": {payload.rationale.strip()[:160]}" if payload.rationale.strip() else ".")
        ),
        actor_id=actor.id if actor else None,
        project_id=insight.project_id,
    )
    db.commit()
    db.refresh(insight)
    return insight_detail(db, insight)


@router.get("/{insight_id}/evidence", response_model=InsightEvidenceResponse)
def list_insight_evidence(
    insight_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> InsightEvidenceResponse:
    """Evidence grouped by the researcher's own classification."""
    insight = db.get(Insight, insight_id)
    if insight is None:
        raise NotFoundError(f"Insight '{insight_id}' does not exist.")
    assert_entity_read(db, actor, insight.project_id)
    return insight_evidence_response(db, insight)


@router.patch("/{insight_id}/evidence/{relationship_id}", response_model=RelationshipWriteResponse)
def update_evidence_relationship(
    insight_id: str,
    relationship_id: str,
    payload: EvidenceLinkUpdate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> RelationshipWriteResponse:
    """Re-classify or re-explain a relationship.

    Only the relationship changes. The evidence row and the customer statement
    are never touched, so a re-classification cannot rewrite history.
    """
    insight = db.get(Insight, insight_id)
    if insight is None:
        raise NotFoundError(f"Insight '{insight_id}' does not exist.")
    assert_entity_write(db, actor, insight.project_id)
    link = _resolve_relationship(db, insight.id, relationship_id)
    evidence = db.get(Evidence, link.evidence_id)
    if evidence is None:
        raise NotFoundError("The linked evidence no longer exists.")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise RuleViolationError(
            "Provide at least one field to change (classification, rationale, confidence or tags)."
        )

    previous = link.role
    if "role" in data and data["role"] is not None:
        previous = link.role
        link.role = data["role"].value if hasattr(data["role"], "value") else data["role"]
    if "rationale" in data and data["rationale"] is not None:
        link.rationale = data["rationale"].strip()
    if "confidence" in data:
        link.confidence = data["confidence"].value if data["confidence"] else None
    if "tags" in data and data["tags"] is not None:
        link.tags = data["tags"]
    if "note" in data and data["note"] is not None:
        link.note = data["note"]

    log_activity(
        db,
        entity_type="insight",
        entity_id=insight.id,
        entity_label=insight.title,
        verb="relationship_updated",
        summary=(
            f"{evidence.code} re-classified from {previous} to {link.role}."
            if previous != link.role
            else f"Relationship metadata for {evidence.code} updated: {', '.join(sorted(data))}."
        ),
        actor_id=actor.id if actor else None,
        project_id=insight.project_id,
    )
    db.commit()
    db.refresh(link)
    return RelationshipWriteResponse(
        relationship=insight_evidence_link_out(db, link, user_map(db, {link.created_by_id})),
        message="Relationship updated. The customer statement was not changed.",
    )


@router.delete("/{insight_id}/evidence/{relationship_id}", response_model=Message)
def unlink_evidence(
    insight_id: str,
    relationship_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> Message:
    insight = db.get(Insight, insight_id)
    if insight is None:
        raise NotFoundError(f"Insight '{insight_id}' does not exist.")
    assert_entity_write(db, actor, insight.project_id)
    link = _resolve_relationship(db, insight.id, relationship_id)
    evidence = db.get(Evidence, link.evidence_id)
    evidence_code = evidence.code if evidence else "unknown evidence"

    # Written before the delete: the audit entry must survive the relationship.
    log_activity(
        db,
        entity_type="insight",
        entity_id=insight.id,
        entity_label=insight.title,
        verb="unlinked",
        summary=(
            f"{evidence_code} removed as {link.role} evidence. "
            "The evidence record and the original customer statement are unchanged."
        ),
        actor_id=actor.id if actor else None,
        project_id=insight.project_id,
    )
    db.delete(link)
    db.commit()
    return Message(
        message="Evidence unlinked.",
        detail="The relationship was removed and logged. The evidence record itself is unchanged.",
    )


@router.get("/{insight_id}/traceability", response_model=InsightTraceability)
def get_traceability(
    insight_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> InsightTraceability:
    """The complete chain for one insight, including where it was used."""
    insight = db.get(Insight, insight_id)
    if insight is None:
        raise NotFoundError(f"Insight '{insight_id}' does not exist.")
    assert_entity_read(db, actor, insight.project_id)
    return insight_traceability(db, insight)


@router.get("/{insight_id}/related", response_model=list[SearchResult])
def related_research(
    insight_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> list[SearchResult]:
    insight = db.get(Insight, insight_id)
    if insight is None:
        raise NotFoundError(f"Insight '{insight_id}' does not exist.")
    assert_entity_read(db, actor, insight.project_id)
    user = require_actor(actor)
    allowed = visible_project_ids(db, user)
    suggestions, _ = suggest_related(
        db, f"{insight.title} {insight.summary} {' '.join(insight.segments or [])}", limit=5
    )
    return [
        s
        for s in suggestions
        if s.id != insight.id
        and (allowed is None or (s.project_id is not None and s.project_id in allowed))
    ]


@router.get("/{insight_id}/reuse", response_model=dict)
def reuse_status(
    insight_id: str,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> dict:
    insight = db.get(Insight, insight_id)
    if insight is None:
        raise NotFoundError(f"Insight '{insight_id}' does not exist.")
    assert_entity_read(db, actor, insight.project_id)
    return {
        "insight_id": insight.id,
        "reused": insight_is_reused(db, insight),
        "definition": (
            "Reused means linked to two or more decisions, or linked to a decision at least 14 days after the "
            "insight was created."
        ),
    }
