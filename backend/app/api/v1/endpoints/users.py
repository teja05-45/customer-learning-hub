"""Administrator account management.

First-run registration claims an empty workspace; from then on an administrator
creates the remaining accounts, sets roles, deactivates people who leave and
resets passwords. No email provider is configured, so an initial or reset
password is handed over out of band -- the API never pretends to have sent a
message. See docs/auth.md.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_actor
from app.core.database import get_db
from app.core.errors import ConflictError, ForbiddenError, NotFoundError, RuleViolationError
from app.core.security import hash_password
from app.models.people import AuthSession, User
from app.schemas.auth import (
    AdminPasswordReset,
    AuthMessage,
    MemberCreate,
    MemberOut,
    MemberUpdate,
)
from app.services.activity import log_activity

router = APIRouter(prefix="/users", tags=["users"])

ACTIVE_ADMIN = (User.role == "admin") & User.is_active.is_(True)


def require_admin(actor: User | None = Depends(get_actor)) -> User:
    """Account administration is limited to the administrator role.

    The middleware already gates writes to ``/users``; this dependency covers
    reads too, so the member directory (names and email addresses) is not
    exposed to every signed-in member.
    """
    if actor is None:
        raise ForbiddenError("Sign in to manage users.")
    if actor.role != "admin":
        raise ForbiddenError(
            "Only an administrator can manage accounts.", code="forbidden"
        )
    return actor


def _initials(name: str) -> str:
    parts = [part for part in name.replace(".", " ").split() if part]
    return "".join(part[0].upper() for part in parts[:2]) or "U"


def _member(user: User) -> MemberOut:
    return MemberOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        job_title=user.job_title,
        initials=user.initials,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def _active_admin_count(db: Session, excluding: str | None = None) -> int:
    statement = select(func.count(User.id)).where(ACTIVE_ADMIN)
    if excluding:
        statement = statement.where(User.id != excluding)
    return db.execute(statement).scalar_one()


@router.get("", response_model=list[MemberOut])
def list_members(db: Session = Depends(get_db), actor: User = Depends(require_admin)) -> list[MemberOut]:
    users = db.execute(select(User).order_by(User.name)).scalars().all()
    return [_member(user) for user in users]


@router.post("", response_model=MemberOut, status_code=201)
def create_member(
    payload: MemberCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> MemberOut:
    existing = db.query(User).filter(User.email == payload.email).one_or_none()
    if existing is not None:
        raise ConflictError(
            "An account with that email address already exists.",
            details={"field": "email"},
        )
    user = User(
        name=payload.name.strip(),
        email=payload.email,
        role=payload.role,
        job_title=payload.job_title.strip(),
        initials=_initials(payload.name),
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    log_activity(
        db,
        entity_type="user",
        entity_id=user.id,
        entity_label=user.name,
        verb="created",
        summary=f"{actor.name} created the account for {user.name} ({user.role}).",
        actor_id=actor.id,
    )
    db.commit()
    db.refresh(user)
    return _member(user)


@router.patch("/{user_id}", response_model=MemberOut)
def update_member(
    user_id: str,
    payload: MemberUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> MemberOut:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("That account does not exist.")

    data = payload.model_dump(exclude_unset=True)
    demoting = data.get("role") not in (None, "admin") and user.role == "admin"
    deactivating = data.get("is_active") is False and user.is_active
    if demoting or deactivating:
        if _active_admin_count(db, excluding=user.id) == 0:
            raise RuleViolationError(
                "This is the last active administrator. Promote someone else first.",
                details={"field": "role" if demoting else "is_active"},
            )

    for field in ("name", "job_title"):
        if data.get(field) is not None:
            setattr(user, field, data[field].strip())
    if data.get("role") is not None:
        user.role = data["role"]
    if data.get("is_active") is not None:
        user.is_active = data["is_active"]
        if not user.is_active:
            # A deactivated account must not keep a working session.
            db.query(AuthSession).filter(AuthSession.user_id == user.id).delete(
                synchronize_session=False
            )
    log_activity(
        db,
        entity_type="user",
        entity_id=user.id,
        entity_label=user.name,
        verb="updated",
        summary=(
            f"{actor.name} updated the account for {user.name} "
            f"({', '.join(sorted(data.keys())) or 'no changes'})."
        ),
        actor_id=actor.id,
    )
    db.commit()
    db.refresh(user)
    return _member(user)


@router.post("/{user_id}/password", response_model=AuthMessage)
def reset_member_password(
    user_id: str,
    payload: AdminPasswordReset,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> AuthMessage:
    """Set a new password for someone else and revoke their existing sessions.

    There is no email provider, so the administrator passes the new password to
    the person directly; the response deliberately does not claim an email was
    sent.
    """
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("That account does not exist.")
    user.password_hash = hash_password(payload.new_password)
    db.query(AuthSession).filter(AuthSession.user_id == user.id).delete(
        synchronize_session=False
    )
    log_activity(
        db,
        entity_type="user",
        entity_id=user.id,
        entity_label=user.name,
        verb="updated",
        summary=f"{actor.name} reset the password for {user.name}; their sessions were revoked.",
        actor_id=actor.id,
    )
    db.commit()
    return AuthMessage(
        message=(
            "Password reset. All of that person's sessions are signed out. "
            "There is no email provider, so pass the new password on directly."
        )
    )
