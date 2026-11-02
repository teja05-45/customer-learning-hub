# Changelog

Format: what changed and why it matters. No claim is made for a change that was not executed.

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
