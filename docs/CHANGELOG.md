# Changelog

Format: what changed and why it matters. No claim is made for a change that was not executed.

## 1.2.0 — Authentication and export correctness

### Added

- Server-side sessions in an HTTP-only cookie, with PBKDF2-HMAC-SHA256 password hashing, an
  `auth_sessions` table and an Alembic revision.
- `auth/register`: claims an empty workspace and creates the first administrator. Closed as soon
  as a user exists.
- `auth/password`: self-service password change that revokes other sessions.
- API-enforced role policy covering every non-public route, not a per-endpoint opt-in.
- Export audit rows, `X-Row-Count`, a UTF-8 BOM for Excel and a `data_origin` column.
- `tests/test_auth.py`, `tests/test_exports.py`; documentation for backup, performance,
  accessibility, troubleshooting, integration and requirement traceability.

### Fixed

- **"Export failed" on every download.** Only the `admin` role could export while demo entry
  signed reviewers in as a researcher, and the client replaced the server message with a generic
  one. Exports are now available to any signed-in member, the real error is surfaced, an empty
  body is treated as a failure, and success is reported only after the file is created.
- **Demonstration entry could mint a session in production.** `auth/demo` now refuses unless
  `DEMO_MODE=true`.
- **Participant records created through the API were labelled synthetic.** They are real records
  and are now stored with `is_synthetic=false`; only the seed sets it true.
- **Demo entry returned 401 instead of working**, because the route was not in the public path
  list. It is public by design and remains gated by demo mode.

### Changed

- Documentation filenames are now the canonical lowercase set required by the brief; the
  numbered discovery set is retained and annotated where it describes the pre-auth prototype.


## 1.1.0 — Prototype hardening

### Fixed

- **Recruitment history was invisible.** The list endpoint returned records without their
  timeline events and resolved actors only from the last editor, so "View timeline" always
  showed "No history recorded yet". The list now returns events and maps every event actor.
- **Interview-driven stage changes left no audit trail.** Scheduling or completing an interview
  changed the recruitment stage directly, skipping the history event. All stage changes now go
  through one service that appends a `RecruitmentEvent`, including `force` paths.
- **Cross-project evidence could be linked after creation.** The create endpoint enforced the
  rule but the link endpoint did not. Linking now rejects evidence from another project with a
  rule-violation error.
- **Project totals were wrong when filtering by business function.** The total was calculated
  before the in-memory JSON filter. Filtering now happens before pagination.
- **Empty interview summary.** The summary was stored and never rendered. The workspace now
  shows and edits it, clearly separated from notes and from customer evidence.
- **Pie chart was inaccessible.** SVG paths exposed names without an image role, failing
  `svg-img-alt`. The chart now has an accessible name and image role.
- **Terminal recruitment stages had no summary card.** Declines, no-responses, cancellations
  and withdrawals are now visible alongside active stages instead of being hidden.

### Added

- Insight editing (title, summary, interpretation, limitations, confidence) from the detail view.
- Evidence review controls and provenance correction with an explicit "clearing a source never
  strengthens the claim" rule.
- Full journey integration test (`backend/tests/test_journey.py`) covering four segments,
  provenance, contradiction, validation, decisions, actions, search and metric agreement.
- Pipeline metric tests and dashboard/analytics agreement tests.
- Browser journey test that verifies the workflow through the real screens.
- `.dockerignore` excludes `.env` files and caches from the build context.

### Verified

- Backend: 42 passed.
- Frontend: typecheck and build clean.
- Browser: 7 passed, including axe accessibility scan.
- Docker: both images build; API and web healthy; nginx proxy returns 200.

## 1.0.0 — Initial prototype

- Evidence-first research workflow, synthetic seed, FastAPI + React stack, Compose stack,
  initial documentation set and browser smoke tests.
