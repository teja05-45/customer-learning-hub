"""Activity trail helper.

The log deliberately stores the *label* of an entity plus a short human summary
so the dashboards can render without joining every table, and so nothing
sensitive has to be duplicated here.
"""

from sqlalchemy.orm import Session

from app.models import ActivityLog


def log_activity(
    db: Session,
    *,
    entity_type: str,
    entity_id: str | None,
    entity_label: str,
    verb: str,
    summary: str,
    actor_id: str | None = None,
    project_id: str | None = None,
) -> ActivityLog:
    entry = ActivityLog(
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=entity_label[:200],
        verb=verb,
        summary=summary[:320],
        actor_id=actor_id,
        project_id=project_id,
    )
    db.add(entry)
    return entry
