# Security and Data Protection

## Scope

This is a portfolio application built for the Everyday Goods customer-learning exercise. The
demo deployment holds **synthetic data only**, connects to no customer system, sends no email,
captures no audio and stores no contact details. Authentication and server-side role enforcement
are implemented; TLS termination, rate limiting and CSRF tokens are not.

## Authentication and access control

- Passwords are hashed with PBKDF2-HMAC-SHA256 (260,000 iterations, per-user salt). Plaintext is
  never stored or logged.
- Sessions are server-side rows; the cookie holds a random token and only its SHA-256 digest is
  persisted. Cookie flags: `HttpOnly`, `SameSite=Lax`, `Secure` when `COOKIE_SECURE=true`.
- `AuthMiddleware` protects every `/api/v1` route by default. Only `health`, `session`,
  `auth/login`, `auth/logout`, `auth/me`, `auth/register` (empty workspace only) and `auth/demo`
  (demo mode only) are public.
- Writes are authorised by role server-side; the browser cannot assert a role. See `auth.md` for
  the matrix.
- Logout deletes the session; a password change deletes all other sessions for that user.
- Failed logins return the same message and status for an unknown email and a wrong password.
- Failed sign-ins are throttled per client address and per account (`LOGIN_MAX_FAILURES`, default
  8, inside `LOGIN_WINDOW_SECONDS`, default 300). A throttled request answers `429 rate_limited`
  with `Retry-After` and issues no cookie; a successful sign-in clears the counter. The counters
  live in the API process, so several replicas would each allow their own quota — a shared store
  is required before the limit can be relied on across replicas.
- State-changing requests are refused with `403 csrf_origin_rejected` when the browser reports an
  `Origin` or `Referer` outside `CORS_ORIGINS` and the request's own host, or an opaque
  `Origin: null`. Requests with neither header (curl, the test suite, server-to-server) pass,
  because they cannot be made to carry a victim's cookie.
- `TRUST_PROXY_HEADERS` is off by default; only enable it behind a proxy that overwrites
  `X-Forwarded-For`, otherwise the address a limit is keyed on can be spoofed.

## Data minimisation

- The participant schema accepts no email, phone or address. Extra fields sent to the API are
  ignored by Pydantic, not stored, and therefore cannot leak through search or export.
- `contact_route` describes *how* a controlled Ops process would reach someone, never the value.
- Interviews store notes and a summary, not audio or transcript files.
- Recording is disabled by default and cannot be enabled without a granted `recording` consent
  record (enforced server-side).
- Exports list only approved columns; `users`, `contact_route`, `notes` and session tables are
  never exported.

## Consent

`consent_records` stores participation, recording, quoting and internal-sharing decisions with
status, actor, timestamp and note. Consent is append-only: changing a decision adds a record
rather than rewriting history. The interview's derived `consent_status` reflects participation.

## Validation and integrity

- All input is validated by Pydantic: lengths, enums, bounded integers and dates.
- Business rules are enforced server-side: transition maps, insight validation requiring
  evidence, cross-project evidence rejection, recording consent gate, deadline-after-start-date,
  duplicate link protection.
- Database foreign keys are enabled on SQLite; cascades and `SET NULL` are explicit.
- One transaction per request; failures roll back.

## Output safety

- CSV exports neutralise spreadsheet formula injection by prefixing cells beginning with `=`,
  `+`, `-`, `@`, tab or carriage return, and label every row with `data_origin`.
- Exports are UTF-8 with a BOM so Excel does not mangle non-Latin text.
- JSON responses are typed; React escapes user content.
- Error messages do not include stack traces or SQL.

## Audit trail

`activity_logs` records business actions (create, update, link, unlink, export, settings change,
registration) with actor, entity, summary and timestamp. It is not tamper-evident: a database
administrator can edit or delete rows. Retention is not automated.

## Configuration and secrets

- Configuration is environment-driven (`app/core/config.py`) with safe defaults; `DEMO_MODE`
  defaults to **false** and seeding to **false**.
- No API keys exist in the repository or the frontend bundle. There is no LLM or email provider
  integration.
- `.env` files are gitignored and excluded from the Docker build context; `.env.example`
  documents variable names only.
- `.dockerignore` excludes local databases and secrets.

## Threats considered

| Threat | Mitigation | Residual risk |
| --- | --- | --- |
| Anonymous access to workspace data | Cookie session required on all data routes | A leaked cookie works until expiry (8h) |
| Role escalation from the browser | Role read from the session user row, never the request body | Compromised admin account |
| Presenting synthetic data as real research | Demo banner, seed-only records, `data_origin`/`is_synthetic` labels | Reviewer could screenshot without context |
| Claiming statistical representativeness | No representativeness metric; small-sample warnings; validation is explicitly internal | A human can still overstate in a slide |
| Unattributed claim becoming "evidence" | Missing provenance forces flagged status and low confidence | A user can type a false provenance string |
| Deleting contradictory evidence | UI warns; deletion is explicit and confirmed; insight counts drop visibly | No immutable audit trail |
| PII entering the system | Contact fields rejected by the schema | Free-text notes could contain names typed by a user |
| CSV formula injection | Cell prefixing | Other export formats not implemented |
| Session theft via XSS | `HttpOnly` cookie; React escaping | No CSP header is set by nginx |
| Cross-site request forgery | `SameSite=Lax`; unsafe requests with a foreign `Origin`/`Referer` or `Origin: null` are refused | Header-less clients are trusted by design; no double-submit token |
| Credential stuffing | Per-address and per-account failure counters with `429` and `Retry-After` | Counters are per process; no CAPTCHA or distributed store |

## Production prerequisites

1. TLS termination (`COOKIE_SECURE=true` behind HTTPS) and HSTS.
2. A shared rate-limit store if the API runs more than one process or replica.
3. A CSRF token if the API is ever served to a third-party client that sends no `Origin`.
4. Managed secrets, encrypted storage and tested backups (`backup_recovery.md`).
5. Automated retention/deletion aligned with `retention_months`.
6. Immutable audit logging for evidence deletion and decision changes.
7. Privacy review of free-text fields and a classification policy.
8. An identity provider if SSO is required (`auth.md`).

See `auth.md`, `13-security-and-privacy.md` and `risks.md`.
