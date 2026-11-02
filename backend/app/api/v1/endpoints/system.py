"""Dashboard, search, analytics, settings, export and health endpoints."""

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_actor
from app.core.config import settings as app_settings
from app.core.database import get_db
from app.core.errors import RuleViolationError
from app.models import (
    BusinessAction,
    Decision,
    Evidence,
    Insight,
    Interview,
    OrganizationSetting,
    Participant,
    RecruitmentRecord,
    ResearchProject,
    User,
)
from app.schemas.dashboard import (
    AnalyticsResponse,
    DashboardResponse,
    DemoUser,
    HealthResponse,
    OrgSettingsOut,
    OrgSettingsUpdate,
    ResetRequest,
    ResetResponse,
    SearchResponse,
    SessionResponse,
)
from app.seed.demo_data import seed_demo_data
from app.services.activity import log_activity
from app.services.analytics import build_analytics
from app.services.dashboard import build_dashboard
from app.services.search import search

router = APIRouter()

ROLE_DESCRIPTIONS = {
    "ceo": {
        "description": "Organisation-level view of research activity, decisions and outstanding actions.",
        "can_view": ["everything", "no participant contact details exist to expose"],
    },
    "researcher": {
        "description": "Runs projects: recruits participants, conducts interviews, captures evidence and drafts insights.",
        "can_view": ["projects", "participants", "recruitment", "interviews", "evidence", "insights"],
    },
    "business_owner": {
        "description": "Reviews insights, makes decisions and owns follow-up actions.",
        "can_view": ["dashboard", "insights", "decisions", "actions", "projects they own"],
    },
    "cx": {
        "description": "Supports explicitly assigned recruitment or coordination tasks only.",
        "can_view": ["assigned recruitment tasks", "scheduling"],
    },
    "admin": {
        "description": "Manages users, roles, retention settings and demo data.",
        "can_view": ["settings", "users", "exports"],
    },
}


# ---------------------------------------------------------------- dashboard
@router.get("/dashboard", response_model=DashboardResponse, tags=["dashboard"])
def get_dashboard(db: Session = Depends(get_db), months: int = Query(default=6, ge=3, le=12)) -> DashboardResponse:
    return build_dashboard(db, months=months)


# ------------------------------------------------------------------- search
@router.get("/search", response_model=SearchResponse, tags=["search"])
def global_search(
    q: str = Query(min_length=1, max_length=160),
    types: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
) -> SearchResponse:
    return search(db, q, types=types)


# ---------------------------------------------------------------- analytics
@router.get("/analytics", response_model=AnalyticsResponse, tags=["analytics"])
def get_analytics(db: Session = Depends(get_db)) -> AnalyticsResponse:
    return build_analytics(db)


# ------------------------------------------------------------------ session
@router.get("/session", response_model=SessionResponse, tags=["settings"])
def get_session(
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> SessionResponse:
    users = db.execute(select(User).where(User.is_active.is_(True)).order_by(User.name)).scalars().all()
    demo_users = [
        DemoUser(
            id=u.id,
            name=u.name,
            role=u.role,
            job_title=u.job_title,
            initials=u.initials,
            can_view=ROLE_DESCRIPTIONS.get(u.role, {}).get("can_view", []),
            description=ROLE_DESCRIPTIONS.get(u.role, {}).get("description", ""),
        )
        for u in users
    ]
    current = next((u for u in demo_users if actor and u.id == actor.id), None)
    return SessionResponse(
        demo_mode=app_settings.demo_mode,
        current_user=current,
        users=demo_users,
        notice=(
            "Demonstration entry only. Role switching is a UI convenience for reviewers and is not "
            "authentication, authorisation or a security boundary. Every request to this API is served with the "
            "same permissions regardless of the selected role."
        ),
    )


# ----------------------------------------------------------------- settings
@router.get("/settings", response_model=OrgSettingsOut, tags=["settings"])
def get_settings(db: Session = Depends(get_db)) -> OrgSettingsOut:
    org = db.get(OrganizationSetting, "default")
    if org is None:
        org = OrganizationSetting(id="default", name="Everyday Goods")
        db.add(org)
        db.commit()
        db.refresh(org)
    return OrgSettingsOut.model_validate(org)


@router.patch("/settings", response_model=OrgSettingsOut, tags=["settings"])
def update_settings(
    payload: OrgSettingsUpdate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> OrgSettingsOut:
    org = db.get(OrganizationSetting, "default")
    if org is None:
        org = OrganizationSetting(id="default", name="Everyday Goods")
        db.add(org)
        db.flush()
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(org, field, value)
    log_activity(
        db,
        entity_type="settings",
        entity_id=org.id,
        entity_label="Organisation settings",
        verb="updated",
        summary=f"Settings updated: {', '.join(sorted(data.keys())) or 'no changes'}.",
        actor_id=actor.id if actor else None,
    )
    db.commit()
    db.refresh(org)
    return OrgSettingsOut.model_validate(org)


@router.post("/demo/reset", response_model=ResetResponse, tags=["settings"])
def reset_demo_data(
    payload: ResetRequest,
    db: Session = Depends(get_db),
    actor: User | None = Depends(get_actor),
) -> ResetResponse:
    if not payload.confirm or payload.phrase.strip().upper() != "RESET":
        raise RuleViolationError(
            "Type RESET and confirm to restore the demo dataset.",
            details={"field": "phrase"},
        )
    # The wipe removes every user, so the request's actor no longer exists as a
    # foreign key. Record who asked in the summary text instead of the id.
    actor_name = actor.name if actor else "Unknown user"
    counts = seed_demo_data(db, reset=True)
    log_activity(
        db,
        entity_type="settings",
        entity_id="default",
        entity_label="Demo dataset",
        verb="reset",
        summary=f"Demo data reset to the synthetic starting point by {actor_name}.",
        actor_id=None,
    )
    db.commit()
    return ResetResponse(message="Demo data restored.", counts=counts)


# ------------------------------------------------------------------ exports
EXPORT_SPECS = {
    "projects": (
        ResearchProject,
        ["name", "status", "priority", "methodology", "start_date", "deadline", "created_at"],
    ),
    "participants": (
        Participant,
        ["code", "display_name", "segment", "purchase_frequency", "orders_count", "product_category", "eligibility"],
    ),
    "recruitment": (
        RecruitmentRecord,
        ["stage", "next_action", "invited_at", "responded_at", "updated_at"],
    ),
    "interviews": (
        Interview,
        ["code", "title", "status", "scheduled_at", "consent_status", "recording_enabled", "completed_at"],
    ),
    "evidence": (
        Evidence,
        ["code", "evidence_type", "content", "interpretation", "segment", "provenance", "provenance_status", "captured_at"],
    ),
    "insights": (
        Insight,
        ["code", "title", "status", "confidence", "research_question", "limitations", "created_at"],
    ),
    "decisions": (
        Decision,
        ["code", "title", "business_function", "status", "decision_date", "rationale", "limitations"],
    ),
    "actions": (
        BusinessAction,
        ["code", "title", "status", "priority", "due_date", "completed_at"],
    ),
}


def _csv_safe(value):
    """Neutralise spreadsheet formula injection.

    A quote is customer text: if someone says "=HYPERLINK(...)" the exported cell
    must not become a live formula when the CSV is opened in Excel or Sheets.
    Prefixing with an apostrophe is the standard mitigation and leaves the visible
    content unchanged.
    """
    if not isinstance(value, str) or not value:
        return value
    if value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{value}"
    return value


@router.get("/exports/{entity}.csv", tags=["exports"])
def export_csv(entity: str, db: Session = Depends(get_db)) -> Response:
    if entity not in EXPORT_SPECS:
        raise RuleViolationError(
            "Unknown export.", details={"available": sorted(EXPORT_SPECS.keys())}
        )
    model, fields = EXPORT_SPECS[entity]
    rows = db.execute(select(model)).scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([*fields, "is_synthetic", "exported_at"])
    timestamp = datetime.now(timezone.utc).isoformat()
    for row in rows:
        values = []
        for field in fields:
            value = getattr(row, field, "")
            if isinstance(value, datetime):
                value = value.isoformat()
            values.append(_csv_safe(value))
        writer.writerow([*values, "true", timestamp])

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="everyday-goods-{entity}-synthetic.csv"',
            "X-Data-Origin": "synthetic-demo-data",
        },
    )


# ------------------------------------------------------------------- health
@router.get("/health", response_model=HealthResponse, tags=["health"])
def health(db: Session = Depends(get_db)) -> HealthResponse:
    try:
        seeded = db.execute(select(func.count(User.id))).scalar_one() > 0
        database = "ok"
    except Exception:  # pragma: no cover - only on a broken database
        seeded = False
        database = "unavailable"
    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        version=app_settings.app_version,
        environment=app_settings.environment,
        database=database,
        demo_mode=app_settings.demo_mode,
        seeded=seeded,
        checked_at=datetime.now(timezone.utc),
    )
