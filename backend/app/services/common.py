"""Small helpers shared by several services."""

from datetime import datetime, timezone
from typing import Any, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.errors import NotFoundError
from app.models import User
from app.schemas.common import Ref

ModelT = TypeVar("ModelT", bound=Base)


def get_or_404(db: Session, model: type[ModelT], entity_id: str | None, label: str) -> ModelT:
    if not entity_id:
        raise NotFoundError(f"{label} was not found.")
    obj = db.get(model, entity_id)
    if obj is None:
        raise NotFoundError(f"{label} with id '{entity_id}' does not exist.")
    return obj


def user_ref(db: Session, user_id: str | None) -> Ref | None:
    if not user_id:
        return None
    user = db.get(User, user_id)
    if user is None:
        return None
    return Ref(id=user.id, label=user.name, sublabel=user.job_title or user.role)


def require_user(db: Session, user_id: str | None, label: str = "Owner") -> User:
    return get_or_404(db, User, user_id, label)


def as_aware(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; normalise before comparing."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def month_key(value: datetime) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def month_sequence(count: int, end: datetime | None = None) -> list[tuple[str, str]]:
    """Return the last ``count`` (key, label) month pairs, oldest first."""
    cursor = end or datetime.now(timezone.utc)
    year, month = cursor.year, cursor.month
    pairs: list[tuple[str, str]] = []
    for _ in range(count):
        pairs.append((f"{year:04d}-{month:02d}", datetime(year, month, 1).strftime("%b %Y")))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(pairs))


def next_code(db: Session, model: type[Any], column_name: str, prefix: str, width: int = 4) -> str:
    """Generate a short human reference such as ``PRJ-0042``.

    Safe enough for a single-instance prototype; a real deployment would move
    this to a database sequence or a dedicated counter table.
    """
    column = getattr(model, column_name)
    rows = db.execute(select(column).where(column.like(f"{prefix}-%"))).scalars().all()
    highest = 0
    for value in rows:
        try:
            highest = max(highest, int(str(value).split("-")[-1]))
        except (TypeError, ValueError):
            continue
    return f"{prefix}-{highest + 1:0{width}d}"


def paginate(stmt, db: Session, page: int, page_size: int):
    total = db.execute(select(func.count()).select_from(stmt.order_by(None).subquery())).scalar_one()
    items = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars().unique().all()
    pages = (total + page_size - 1) // page_size if total else 0
    return items, total, pages
