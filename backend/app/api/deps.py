"""Shared dependencies.

The prototype identifies the acting user with the ``X-Demo-User-Id`` header.
That is a *demonstration* mechanism only: it is not authentication and it grants
no security. See docs/AUTH.md for the production plan.
"""

from fastapi import Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models import User


def get_actor(
    x_demo_user_id: str | None = Header(default=None, alias="X-Demo-User-Id"),
    db: Session = Depends(get_db),
) -> User | None:
    if not x_demo_user_id:
        return db.query(User).filter(User.role == "researcher").first()
    user = db.get(User, x_demo_user_id)
    if user is None:
        raise NotFoundError("Demo user not found. Pick a user from the demonstration entry screen.")
    return user


class Pagination:
    def __init__(
        self,
        page: int = Query(default=1, ge=1, le=10_000),
        page_size: int = Query(default=20, ge=1, le=100),
    ) -> None:
        self.page = page
        self.page_size = page_size


def demo_mode_label() -> str:
    return "demo" if settings.demo_mode else "live"
