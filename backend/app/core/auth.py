"""Authentication and role enforcement for the API.

The demo originally trusted a client-supplied user id. That is not a security
boundary, so this middleware now requires a real server-side session for every
API route except the public ones, and applies a coarse write policy by role.

Why middleware rather than a dependency on every endpoint: authentication must
cover all routes by default. A route added later is protected unless it is
explicitly listed as public, which is the safer failure mode.
"""

from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import SESSION_COOKIE, token_digest
from app.models.people import AuthSession, User

PUBLIC_PATHS = {
    f"{settings.api_prefix}/health",
    f"{settings.api_prefix}/session",
    f"{settings.api_prefix}/auth/login",
    f"{settings.api_prefix}/auth/logout",
    f"{settings.api_prefix}/auth/me",
    # First-run registration is public only while the workspace is empty; the
    # endpoint itself refuses once any user exists.
    f"{settings.api_prefix}/auth/register",
    # Demonstration entry is public by design, but the endpoint itself refuses
    # unless DEMO_MODE is on, so it cannot mint a session in production.
    f"{settings.api_prefix}/auth/demo",
}

RESEARCH_WRITE_ROLES = {"researcher", "admin"}
BUSINESS_WRITE_ROLES = {"researcher", "business_owner", "ceo", "admin"}
ADMIN_ROLES = {"admin", "researcher"}
USER_ADMIN_ROLES = {"admin"}
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def resolve_user(db, request: Request) -> User | None:
    """Session cookie authentication.

    Validates the server-side session cookie and returns the associated user.
    Never accepts client-supplied identity headers. This is a strict server-side
    authentication boundary - no demonstration tricks, no role switching.
    """
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        session = (
            db.query(AuthSession)
            .filter(AuthSession.token_hash == token_digest(token))
            .one_or_none()
        )
        if session is not None:
            now = datetime.now(timezone.utc)
            expires_at = session.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at > now:
                session.last_seen_at = now
                db.commit()
                user = db.get(User, session.user_id)
                if user is not None and user.is_active:
                    return user
    return None


def roles_for_write(method: str, path: str) -> set[str] | None:
    """Return the roles allowed to perform this write, or None for reads."""
    if method in SAFE_METHODS:
        return None
    relative = path.removeprefix(settings.api_prefix)
    if relative.startswith("/users"):
        # Account administration is the administrator's job alone; a researcher
        # must not be able to mint an account or change a role.
        return USER_ADMIN_ROLES
    if relative.startswith(("/demo", "/settings")):
        return ADMIN_ROLES
    if relative.startswith(
        (
            "/projects",
            "/participants",
            "/recruitment",
            "/interviews",
            "/evidence",
            "/feedback",
            "/insights",
        )
    ):
        return RESEARCH_WRITE_ROLES
    if relative.startswith(("/decisions", "/actions")):
        return BUSINESS_WRITE_ROLES
    return ADMIN_ROLES


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": None}})


def _allowed_origins(request: Request) -> set[str]:
    allowed = {origin.rstrip("/") for origin in settings.cors_origin_list}
    host = request.headers.get("host")
    if host:
        # Same-origin deployments (the Compose stack serves the app and /api from
        # one host) are allowed without listing themselves in CORS_ORIGINS.
        allowed.add(f"{request.url.scheme}://{host}".rstrip("/"))
    return allowed


def origin_is_trusted(request: Request) -> bool:
    """CSRF defence for state-changing requests.

    A cookie-authenticated write is only cross-site forgeable if the browser
    tells us it came from somewhere else, and modern browsers always send
    ``Origin`` on unsafe methods. Requests that carry an ``Origin`` or
    ``Referer`` outside the configured list are refused; requests with neither
    header are non-browser clients (curl, the test suite, server-to-server),
    which cannot be tricked into riding a user's cookie.
    """
    allowed = _allowed_origins(request)
    for header in ("origin", "referer"):
        value = (request.headers.get(header) or "").rstrip("/")
        if not value:
            continue
        if value == "null":
            return False
        if not any(value == origin or value.startswith(f"{origin}/") for origin in allowed):
            return False
    return True


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith(settings.api_prefix) or request.method == "OPTIONS":
            return await call_next(request)
        if request.method not in SAFE_METHODS and not origin_is_trusted(request):
            return _error(
                403,
                "csrf_origin_rejected",
                "This request came from an origin this API does not trust.",
            )
        if path in PUBLIC_PATHS:
            return await call_next(request)

        db = SessionLocal()
        try:
            user = resolve_user(db, request)
            if user is None:
                return _error(
                    401,
                    "unauthorized",
                    "Sign in to use this workspace. This API requires an authenticated session.",
                )
            allowed = roles_for_write(request.method, path)
            if allowed is not None and user.role not in allowed:
                return _error(
                    403,
                    "forbidden",
                    f"The {user.role.replace('_', ' ')} role cannot perform this action.",
                )
            request.state.user = user
        finally:
            db.close()
        return await call_next(request)
