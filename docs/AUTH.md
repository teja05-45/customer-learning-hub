# Authentication: what exists, and what it would take

## Short version

**There is no authentication in this prototype.** What looks like a login is a role picker
that writes a user id to `localStorage`. Every API endpoint is served to anyone who can reach
it, with full permissions. This document exists so that nobody mistakes the demonstration for
security, and so the real implementation has a plan.

## What actually happens

1. `GET /api/v1/session` returns the seven seeded people and a `notice` field stating this is a
   demonstration.
2. The entry screen renders one button per person. Clicking one calls
   `setDemoUserId(id)` → `localStorage.clh.demoUserId`.
3. `api.ts` attaches `X-Demo-User-Id: <id>` to requests.
4. `get_actor()` in `backend/app/api/deps.py` looks that id up and returns the `User`, **or
   returns `None`** if the header is missing or unknown.
5. The actor is used for one thing: writing `actor_id` on activity-log rows and
   `captured_by_id` / `updated_by_id` fields.

Nothing is filtered by role. No endpoint returns 403. Sending no header at all works. Sending
another person's id attributes your action to them.

## Why it is built this way

A three-week prototype that needed real auth would have spent its budget on password resets
and session tables instead of on the research workflow, which is the thing being evaluated.
Faking auth — a "login" that accepts any password, or a role check enforced only in the UI —
would have been worse: reviewers would assume protection that does not exist.

So the choice was to make the absence explicit in four places: the entry screen, the API
description, this document, and the security document. The test
`test_session_is_labelled_as_demo_not_authentication` fails if the label is ever removed.

## What production would need

### Identity

- **Email + password** for a ten-person internal tool, or **SSO** (Google Workspace / Microsoft
  Entra) if Everyday Goods already has one. SSO is the better default: no password storage, no
  reset flow, and joiner/leaver handling comes from the directory.
- Sessions: HTTP-only, `Secure`, `SameSite=Lax` cookies with server-side sessions, not JWTs in
  `localStorage` — a research tool holds customer quotes, and a token readable by JavaScript
  is one XSS away from exfiltration.
- Short idle timeout (8 hours) and a 30-day absolute limit.

### Authorisation

Roles already exist as data (`ceo`, `researcher`, `business_owner`, `cx`, `admin`). The
minimal policy that matches how the team works:

| Capability | researcher | business_owner | cx | ceo | admin |
| --- | --- | --- | --- | --- | --- |
| Read projects, insights, decisions | ✓ | ✓ | ✓ | ✓ | ✓ |
| Create/edit projects, interviews, evidence | ✓ | — | — | — | — |
| Validate an insight | ✓ | — | — | — | — |
| Create a decision | ✓ | ✓ | ✓ | ✓ | — |
| Change organisation settings, reset demo | — | — | — | — | ✓ |
| Export CSVs | ✓ | ✓ | ✓ | ✓ | ✓ |
| See participant records | ✓ | limited (no notes) | limited | aggregate only | ✓ |

Enforcement belongs in a FastAPI dependency per router (`require_role(...)`), not in the React
app. The UI may hide what a role cannot do, but the API must refuse it independently.

### Things this data model makes easy, and hard

- **Easy:** every mutation already records an actor, so an audit trail exists the moment actors
  are real.
- **Easy:** there is no contact data to protect, which removes the hardest part of the privacy
  surface.
- **Hard:** four tables denormalise `project_id` for filtering (evidence, insights, decisions,
  actions). Row-level authorisation ("only project members see this project") would need a
  membership table and a check on every one of those paths. For ten people, workspace-wide read
  access is simpler and honest.

### Migration path

1. Add `auth_users` (or extend `users`) with `external_id`, `password_hash` (nullable when SSO),
   `last_login_at`, `failed_attempts`.
2. Add `sessions` (id, user_id, issued_at, expires_at, ip, user_agent) and cookie middleware.
3. Replace `get_actor()` with `get_current_user()` that raises 401 when there is no session,
   and keep an `X-Demo-User-Id` path only when `DEMO_MODE=true` and `ENVIRONMENT != production`.
4. Add `require_role()` to mutating routers.
5. Delete the role picker from the UI; keep a "signed in as" menu with real sign-out.
6. Add CSRF protection for cookie-authenticated mutations.
7. Add tests: 401 without a session, 403 for a role that may not validate, 200 for one that may.

Steps 3–5 are one sprint for one developer; steps 1–2 are a day with an identity provider that
already exists.

## Interim mitigations for a hosted demo

If this prototype is put on a public URL before auth exists:

- Put it behind HTTP basic auth at the proxy (nginx `auth_basic`) — crude, but it stops casual
  access.
- Set `DEMO_MODE=false` and `SEED_DEMO_DATA=false` on any instance that should not create
  data.
- Keep the database non-persistent, so a reset is free.
- Do not put real customer notes in it. The schema has no contact fields, but the free-text
  fields will happily accept anything typed into them.
