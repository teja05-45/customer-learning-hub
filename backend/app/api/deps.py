"""Shared dependencies.

The prototype identifies the acting user with the ``X-Demo-User-Id`` header.
That is a *demonstration* mechanism only: it is not authentication and it grants
no security. See docs/AUTH.md for the production plan.
"""

from fastapi import Depends, Header, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import resolve_user
from app.core.config import settings
from app.core.database import get_db
from app.models import User


def get_actor(
    request: Request,
    x_demo_user_id: str | None = Header(default=None, alias="X-Demo-User-Id"),
    db: Session = Depends(get_db),
) -> User | None:
    """The authenticated actor for this request.

    The authentication middleware has already resolved and authorised the
    request; this dependency reuses its result. The fallback exists for public
    routes (for example the session directory) and for tests that call the
    resolver directly. There is no anonymous default user.
    """
    user = getattr(request.state, "user", None)
    if user is not None:
        return user
    return resolve_user(db, request)


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
