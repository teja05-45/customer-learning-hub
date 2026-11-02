# Authentication and Authorisation

Status: **implemented**. The earlier prototype trusted a client-supplied user id. That is gone:
identity now comes from a server-side session referenced by an HTTP-only cookie, and the API
checks the signed-in user's role on every write.

## Model

| Concern | Implementation |
| --- | --- |
| Credential | Email + password |
| Password storage | PBKDF2-HMAC-SHA256, 260,000 iterations, 16-byte random salt (`app/core/security.py`) |
| Session | Random 32-byte token in the `clh_session` cookie; only its SHA-256 digest is stored |
| Cookie flags | `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` when `COOKIE_SECURE=true` |
| Lifetime | 8 hours; `last_seen_at` is refreshed on use, `expires_at` is absolute |
| Revocation | Logout deletes the row; changing a password deletes every other session for that user |
| Transport | Same-origin `/api` behind nginx in the Docker build; Vite proxy locally |

The browser never stores a user id, token or role in `localStorage`. `GET /auth/me` is the only
source of identity in the UI, and it is answered from the cookie.

## Endpoints

| Method | Path | Auth required | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/register` | No, only while zero users exist | Claim an empty workspace; the first account becomes `admin` |
| POST | `/auth/login` | No | Email + password → session cookie |
| POST | `/auth/logout` | No (idempotent) | Delete the session row and the cookie |
| GET | `/auth/me` | Session | The signed-in user |
| POST | `/auth/password` | Session | Change own password, revoke other sessions |
| POST | `/auth/demo` | No, **only when `DEMO_MODE=true`** | Demonstration entry: issue a session for a seeded synthetic user |

`POST /auth/register` is public only because a fresh database has no administrator; it refuses
with `403 registration_closed` as soon as one user exists. Further accounts are an administrator
task in this release (see "Known gaps").

## Enforcement

`app/core/auth.py` installs `AuthMiddleware`, which runs before every `/api/v1` route:

1. Public paths (`health`, `session`, `auth/*`) pass through.
2. Every other route resolves the cookie to an active user; otherwise `401 unauthorized`.
3. For non-`GET` requests, the path selects an allowed role set; otherwise `403 forbidden`.

Covering all routes by default means a newly added endpoint is protected unless it is explicitly
listed as public — the safe failure mode.

| Role | Write access |
| --- | --- |
| `researcher` | Projects, participants, recruitment, interviews, evidence, insights; decisions and actions |
| `admin` | Everything above, plus settings, demo reset and user administration |
| `business_owner`, `ceo` | Decisions and actions (plus all reads) |
| `cx` | No writes through this API; read access for coordination |

Exports are reads: any active member may download records they can already see. The endpoint
still re-checks the actor, and every download is written to the audit trail.

## Why cookie sessions rather than tokens in JavaScript

A research workspace holds customer quotes. A bearer token readable by JavaScript is one XSS
away from exfiltration; an `HttpOnly` cookie is not readable by scripts. Same-origin delivery
keeps the configuration simple, and `SameSite=Lax` blocks cross-site form submissions.

## Known gaps

- **No SSO / identity provider.** Email + password only. An OIDC provider is the natural next
  step; the `password_hash` column is nullable so SSO-only users can exist.
- **No email-based password reset.** A user who forgets a password needs an administrator. The
  self-service change flow requires the current password.
- **Account management, not invitations.** An administrator creates accounts in Settings (or at
  `POST /users`), changes roles, deactivates leavers and resets passwords. There is no emailed
  invitation or self-service "forgot password" link, because no email provider is configured;
  the administrator hands the initial or reset password over directly.
- **Single organisation.** `OrganizationSetting` is a singleton and every record belongs to it,
  so cross-organisation isolation cannot be violated — but multi-tenancy is not implemented.
- **CSRF defence is origin-based, not token-based.** `SameSite=Lax` plus a check that refuses
  unsafe requests whose browser-reported `Origin`/`Referer` is outside `CORS_ORIGINS` and the
  request's own host. Header-less clients are trusted, so a double-submit token remains the
  stricter option if third-party clients ever call the API directly.
- **Throttling is in-process.** Failed sign-ins are limited per address and per account (8 per
  5 minutes by default). A multi-replica deployment needs a shared counter store.

## Tests

`backend/tests/test_auth.py` covers: anonymous rejection on data routes, password login and
logout, cookie flags, role enforcement (researcher allowed, owner limited, CX read-only),
demonstration entry disabled outside demo mode, client-supplied header rejected, first-run
registration and its closure, and password change revoking other sessions.
