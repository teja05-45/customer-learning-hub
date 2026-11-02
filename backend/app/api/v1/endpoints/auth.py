"""Session authentication endpoints.

Identity is a server-side session referenced by an HTTP-only cookie. Demo entry
issues a real session only while DEMO_MODE is on. Password login and first-run
registration work regardless, so a fresh production database can be claimed by
its first administrator. SSO is not implemented: no identity provider is
configured for this delivery. See docs/auth.md.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
)
from app.core.ratelimit import FailureLimiter
from app.core.security import (
    SESSION_COOKIE,
    SESSION_HOURS,
    hash_password,
    new_session_token,
    token_digest,
    verify_password,
)
from app.models.people import AuthSession, User
from app.schemas.auth import (
    AuthMessage,
    AuthUser,
    DemoLoginRequest,
    LoginRequest,
    PasswordChangeRequest,
    RegisterRequest,
)
from app.services.activity import log_activity

router = APIRouter(prefix="/auth", tags=["auth"])

INVALID_CREDENTIALS = "Email or password is incorrect."

# Failed sign-ins are counted per client address and per account, so neither a
# single noisy client nor a distributed attack on one account can run unbounded.
login_limiter = FailureLimiter(settings.login_max_failures, settings.login_window_seconds)


def _client_address(request: Request) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip() or "unknown"
    return request.client.host if request.client else "unknown"


def _throttle_keys(request: Request, email: str) -> list[str]:
    return [f"ip:{_client_address(request)}", f"email:{email}"]


def _initials(name: str) -> str:
    parts = [part for part in name.replace(".", " ").split() if part]
    return "".join(part[0].upper() for part in parts[:2]) or "U"


def _auth_user(user: User) -> AuthUser:
    return AuthUser(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        job_title=user.job_title,
        initials=user.initials,
    )


def _issue_session(db: Session, user: User, request: Request, response: Response) -> AuthUser:
    token = new_session_token()
    now = datetime.now(timezone.utc)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=token_digest(token),
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(hours=SESSION_HOURS),
            user_agent=(request.headers.get("user-agent") or "")[:200],
        )
    )
    db.commit()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return AuthUser(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        job_title=user.job_title,
        initials=user.initials,
    )


@router.post("/register", response_model=AuthUser, status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthUser:
    """Claim an empty workspace.

    Only the first account can be created without authentication; it becomes the
    administrator of the organisation. Once any user exists this endpoint is
    closed, and further accounts are created by an administrator. That is the
    controlled-invitation model: it cannot be used to join a live workspace.
    """
    existing = db.execute(select(func.count(User.id))).scalar_one()
    if existing:
        raise ForbiddenError(
            "This workspace already has an administrator. Ask them to create your account.",
            code="registration_closed",
        )
    email = payload.email.strip().lower()
    name = payload.name.strip()
    user = User(
        name=name,
        email=email,
        role="admin",
        job_title="Workspace administrator",
        initials=_initials(name),
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    from app.models import OrganizationSetting

    org = db.get(OrganizationSetting, "default")
    if org is None:
        db.add(OrganizationSetting(id="default", name=payload.organisation_name.strip()))
    else:
        org.name = payload.organisation_name.strip()
    log_activity(
        db,
        entity_type="user",
        entity_id=user.id,
        entity_label=user.name,
        verb="registered",
        summary=f"First administrator {user.name} registered {payload.organisation_name.strip()}.",
        actor_id=user.id,
    )
    db.commit()
    return _issue_session(db, user, request, response)


@router.post("/demo", response_model=AuthUser)
def demo_login(
    payload: DemoLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthUser:
    """Demonstration entry. Disabled unless DEMO_MODE is explicitly on."""
    if not settings.demo_mode:
        raise ForbiddenError(
            "Demonstration entry is disabled. Sign in with your email and password.",
            code="demo_disabled",
        )
    user = db.get(User, payload.user_id)
    if user is None or not user.is_active:
        raise NotFoundError("That user does not exist.")
    return _issue_session(db, user, request, response)


@router.post("/login", response_model=AuthUser)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthUser:
    keys = _throttle_keys(request, payload.email)
    waits = [login_limiter.retry_after(key) for key in keys] if settings.login_max_failures > 0 else []
    if any(waits):
        raise RateLimitedError(
            "Too many failed sign-in attempts. Wait a few minutes, then try again.",
            retry_after=max(waits),
        )

    user = db.query(User).filter(User.email == payload.email.lower()).one_or_none()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        # Same message and status for unknown email and wrong password.
        if settings.login_max_failures > 0:
            for key in keys:
                login_limiter.record_failure(key)
        raise UnauthorizedError(INVALID_CREDENTIALS)

    for key in keys:
        login_limiter.clear(key)
    return _issue_session(db, user, request, response)


@router.post("/logout", response_model=AuthMessage)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> AuthMessage:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        db.query(AuthSession).filter(AuthSession.token_hash == token_digest(token)).delete()
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return AuthMessage(message="Signed out.")


@router.get("/me", response_model=AuthUser)
def me(request: Request, db: Session = Depends(get_db)) -> AuthUser:
    from app.core.auth import resolve_user

    user = resolve_user(db, request)
    if user is None:
        raise UnauthorizedError("Sign in to continue.")
    return _auth_user(user)


@router.post("/password", response_model=AuthMessage)
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> AuthMessage:
    """Change your own password; every other session for this user is revoked."""
    from app.core.auth import resolve_user

    user = resolve_user(db, request)
    if user is None:
        raise UnauthorizedError("Sign in to continue.")
    if not verify_password(payload.current_password, user.password_hash):
        raise UnauthorizedError("The current password is incorrect.")
    if payload.current_password == payload.new_password:
        raise ConflictError("Choose a password you have not used here before.")
    user.password_hash = hash_password(payload.new_password)
    token = request.cookies.get(SESSION_COOKIE)
    db.query(AuthSession).filter(AuthSession.user_id == user.id).filter(
        AuthSession.token_hash != token_digest(token or "")
    ).delete(synchronize_session=False)
    log_activity(
        db,
        entity_type="user",
        entity_id=user.id,
        entity_label=user.name,
        verb="updated",
        summary=f"{user.name} changed their password; other sessions were revoked.",
        actor_id=user.id,
    )
    db.commit()
    return AuthMessage(message="Password updated. Other sessions were signed out.")

