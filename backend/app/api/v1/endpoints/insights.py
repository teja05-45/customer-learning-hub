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
    InsightCreate,
    InsightDetail,
    InsightListResponse,
    InsightSummary,
    InsightUpdate,
)
from app.services.activity import log_activity
from app.services.common import next_code
from app.services.search import suggest_related
from app.services.serializers import insight_detail, insight_is_reused, insight_summary

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=InsightListResponse)
def list_insights(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=160),
    project_id: str | None = Query(default=None),
    insight_status: list[str] | None = Query(default=None, alias="status"),
    segment: list[str] | None = Query(default=None),
    confidence: list[str] | None = Query(default=None),
    owner_id: str | None = Query(default=None),
    sort: str = Query(default="recent", pattern="^(recent|evidence|confidence|title)$"),
) -> InsightListResponse:
    stmt = select(Insight)
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

    status_counts = dict(
        db.execute(select(Insight.status, func.count(Insight.id)).group_by(Insight.status)).all()
    )
    return InsightListResponse(items=items, total=len(items), status_counts=status_counts)


@router.post("", response_model=InsightDetail, status_code=status.HTTP_201_CREATED)
def create_insight(
    payload: InsightCreate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> InsightDetail:
    if payload.project_id and db.get(ResearchProject, payload.project_id) is None:
        raise NotFoundError("That research project does not exist.")
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
        if evidence.project_id != payload.project_id and payload.project_id:
            raise RuleViolationError(
                "Evidence from a different research project cannot be linked to this insight.",
                details={"evidence_id": evidence_id},
            )
        db.add(
            InsightEvidence(insight_id=insight.id, evidence_id=evidence.id, role="supporting")
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
def get_insight(insight_id: str, db: Session = Depends(get_db)) -> InsightDetail:
    insight = db.get(Insight, insight_id)
    if insight is None:
        raise NotFoundError(f"Insight '{insight_id}' does not exist.")
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
    evidence = db.get(Evidence, payload.evidence_id)
    if evidence is None:
        raise NotFoundError(f"Evidence '{payload.evidence_id}' does not exist.")
    if insight.project_id and evidence.project_id != insight.project_id:
        raise RuleViolationError(
            "Evidence from a different research project cannot be linked to this insight.",
            details={"evidence_id": evidence.id},
        )

    existing = db.execute(
        select(InsightEvidence).where(
            InsightEvidence.insight_id == insight.id, InsightEvidence.evidence_id == evidence.id
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictError("That evidence is already linked to this insight.")

    db.add(
        InsightEvidence(
            insight_id=insight.id,
            evidence_id=evidence.id,
            role=payload.role.value,
            note=payload.note,
        )
    )
    log_activity(
        db,
        entity_type="insight",
        entity_id=insight.id,
        entity_label=insight.title,
        verb="linked",
        summary=f"{evidence.code} linked as {payload.role.value} evidence.",
        actor_id=actor.id if actor else None,
        project_id=insight.project_id,
    )
    db.commit()
    db.refresh(insight)
    return insight_detail(db, insight)


@router.delete("/{insight_id}/evidence/{evidence_id}", response_model=Message)
def unlink_evidence(insight_id: str, evidence_id: str, db: Session = Depends(get_db)) -> Message:
    link = db.execute(
        select(InsightEvidence).where(
            InsightEvidence.insight_id == insight_id, InsightEvidence.evidence_id == evidence_id
        )
    ).scalar_one_or_none()
    if link is None:
        raise NotFoundError("That evidence is not linked to this insight.")
    db.delete(link)
    db.commit()
    return Message(message="Evidence unlinked.", detail="The evidence record itself is unchanged.")


@router.get("/{insight_id}/related", response_model=list[SearchResult])
def related_research(insight_id: str, db: Session = Depends(get_db)) -> list[SearchResult]:
    insight = db.get(Insight, insight_id)
    if insight is None:
        raise NotFoundError(f"Insight '{insight_id}' does not exist.")
    suggestions, _ = suggest_related(
        db, f"{insight.title} {insight.summary} {' '.join(insight.segments or [])}", limit=5
    )
    return [s for s in suggestions if s.id != insight.id]


@router.get("/{insight_id}/reuse", response_model=dict)
def reuse_status(insight_id: str, db: Session = Depends(get_db)) -> dict:
    insight = db.get(Insight, insight_id)
    if insight is None:
        raise NotFoundError(f"Insight '{insight_id}' does not exist.")
    return {
        "insight_id": insight.id,
        "reused": insight_is_reused(db, insight),
        "definition": (
            "Reused means linked to two or more decisions, or linked to a decision at least 14 days after the "
            "insight was created."
        ),
    }
