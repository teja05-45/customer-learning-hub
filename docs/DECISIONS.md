# Decisions

Each entry records the decision, the context, and what was traded away.

## ADR-001 — Modular monolith, not microservices

**Context:** One FDE, a three-week prototype, one customer workflow.
**Decision:** A single FastAPI service and a single React SPA.
**Consequence:** Simple local run and debugging; no independent scaling. Boundaries are kept by
module (`api`, `services`, `models`, `schemas`) so a later split is possible.

## ADR-002 — SQLite by default, PostgreSQL-compatible design

**Context:** Reviewers must run the demo with no infrastructure.
**Decision:** SQLite file with a named Docker volume; portable column types, explicit foreign
keys and Alembic migrations.
**Consequence:** Single-writer limitation; production requires PostgreSQL and a driver.

## ADR-003 — Warnings are server-produced

**Context:** Every screen must show the same caveat about thin evidence or missing provenance.
**Decision:** Serializers attach `evidence_warning`, `provenance_warning`, sample warnings and
segment-gap flags.
**Consequence:** Larger payloads; one source of truth for honesty.

## ADR-004 — Do not block unevidenced decisions

**Context:** Businesses make judgement calls. Blocking them pushes the decision out of the tool.
**Decision:** Allow the decision, label it as internal judgement, and surface the count.
**Consequence:** Requires discipline in leadership reporting, mitigated by the warning and the
dashboard split between evidenced and unevidenced decisions.

## ADR-005 — "Validated for internal use" is a review state

**Context:** A small sample cannot support statistical claims.
**Decision:** Validation requires one linked evidence item; the label explicitly means reviewed
by a person. No representativeness percentage is produced.
**Consequence:** The tool cannot answer "how confident are we statistically?" — by design.

## ADR-006 — One transition service for recruitment

**Context:** Stage changes came from the pipeline board and from interview scheduling; the
latter bypassed history.
**Decision:** `advance_stage()` owns validation, timestamps, participant contact time and the
history event. Interview flows call it, with `force=True` only for legitimate workflow jumps.
**Consequence:** History is complete; a forced move can skip intermediate stages but is recorded
with an explanatory note.

## ADR-007 — Deterministic keyword search

**Context:** A prototype does not need embeddings, and reviewers must be able to explain results.
**Decision:** All meaningful words must appear across searchable columns; stop words are removed;
related research uses keyword overlap.
**Consequence:** No semantic recall. Queries must share vocabulary with the record.

## ADR-008 — Demo identity is not authentication

**Context:** A real auth flow would consume the prototype budget without demonstrating the
product.
**Decision:** A role picker writes a user id to local storage and sends it as a header; the API
attributes activity but enforces no permissions. The absence is documented and asserted in a
test.
**Consequence:** Not safe to host publicly; authentication is the first production task.

## ADR-009 — No contact details in the participant model

**Context:** The prototype must not become a store of personal data.
**Decision:** The schema accepts no email/phone/address; `contact_route` describes a controlled
process. Extra fields are ignored by validation.
**Consequence:** The tool cannot contact anyone, which is the intended boundary.

## ADR-010 — Reuse definition is explicit

**Context:** "Reuse" could mean many things.
**Decision:** An insight is reused when linked to two or more decisions, or linked at least 14
days after creation. The definition is returned with the metric.
**Consequence:** Immediate single use is not counted as reuse; the threshold is visible and
changeable in one place (`REUSE_WINDOW_DAYS`).

## ADR-011 — CSV export neutralises formula injection

**Context:** Customer quotes are free text and may begin with `=`.
**Decision:** Prefix dangerous leading characters and label every row `is_synthetic`.
**Consequence:** Exported cells can show a leading apostrophe; safety over cosmetics.

## ADR-012 — Docker publishes the web app on 8081

**Context:** 8080 is commonly occupied on developer machines.
**Decision:** Container listens on 8080; host mapping is 8081.
**Consequence:** Documentation and Compose must agree; one line to change.

## ADR-013 — Sessions use an HTTP-only cookie, not a token in JavaScript

**Context:** A research workspace holds customer quotes and free-text notes. Storing a bearer
token in `localStorage` makes any XSS a full account takeover.
**Decision:** Issue a random 256-bit token in an HTTP-only, `SameSite=Lax` cookie; persist only
its SHA-256 digest server-side with an 8-hour absolute expiry.
**Consequence:** The browser cannot read the credential, logout is a server-side delete, and a
password change revokes every other session. Same-origin deployment is required, and CSRF
protection beyond `SameSite` still needs a token.

## ADR-014 — Exports are reads, not an administrator privilege

**Context:** Restricting CSV downloads to `admin` broke the demo for every reviewer and produced
the reported "Export failed".
**Decision:** Any authenticated member may export records they can already read; the endpoint
re-checks the actor, excludes sensitive columns by construction, and writes an audit row.
**Consequence:** The permission model matches the read model. Organisation-wide export is still
visible in the audit trail, so bulk extraction is attributable.
