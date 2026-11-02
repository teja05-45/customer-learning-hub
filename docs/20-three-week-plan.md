# Three-week plan

Fifteen working days, one developer, one reviewer available for two 30-minute sessions a week.
The constraint that shaped everything: **a working artifact every Friday**, not a design
document that becomes code in week three.

## Week 1 — Model the truth before drawing screens

**Goal:** a complete, tested data model and API. No UI.

| Day | Work | Done when |
| --- | --- | --- |
| 1 | Read the brief, write the product brief and the entity list. Decide the three-layer separation (evidence / insight / decision) before writing a line of code | `docs/01-product-brief.md`, `docs/05-data-model.md` exist as drafts |
| 2 | SQLAlchemy models (17 tables), enums as strings, Alembic initial migration, config and logging | `alembic upgrade head` creates the schema on an empty file |
| 3 | Pydantic schemas, error envelope, pagination, the `log_activity` helper | Validation failures return the documented shape |
| 4 | Projects, participants, recruitment endpoints with transition rules | Illegal stage jumps rejected with an explanation |
| 5 | Interviews, evidence, insights, decisions, actions, dashboard, analytics, search, exports | `curl` can walk project → decision end to end |

**Friday demo:** the API, through Swagger. Reviewer question that changed the design: *"what
happens when an insight has no evidence?"* → insight validation was made to fail with 400, and
the `evidence_warning` field was added.

**Deliberately deferred:** any styling, and any role-based filtering (there is none — see
[AUTH.md](AUTH.md)).

## Week 2 — Build the loop in the browser

**Goal:** every workflow usable, unstyled-but-structured. Real data, real errors.

| Day | Work | Done when |
| --- | --- | --- |
| 6 | Vite + React + TS scaffold, design tokens, `ui.tsx` primitives, shell with sidebar and search | Navigation between placeholder pages works, no console errors |
| 7 | Seed dataset (~70 rows, dates relative to now), demo reset, demo entry screen | `docker compose up` shows a populated workspace on first boot |
| 8 | Overview, projects list, project detail, project creation from a template | A reviewer can create a study and see it in the list |
| 9 | Participants, recruitment pipeline, interview list and workspace | A participant can be recruited and interviewed |
| 10 | Evidence capture, evidence library, insight drafting with evidence linking | A quote can be captured and linked to an insight in under a minute |

**Friday demo:** the research loop, on a laptop, with data created live. Reviewer question:
*"how do I know this quote is real?"* → provenance became a required visible field with a
three-state status, and the "unverified" filter was added.

**Deliberately deferred:** analytics and decisions list design; both were still JSON in a
`<pre>` at this point.

## Week 3 — The decision layer, the honesty layer, and the wrapping

**Goal:** the reason the product exists, plus everything a stranger needs to run it.

| Day | Work | Done when |
| --- | --- | --- |
| 11 | Decisions list and detail, linking sources, evidence-sufficiency labelling, actions | A decision can be recorded, linked, and labelled internal judgement |
| 12 | Analytics with metric bases and measurement gaps; dashboard learning signals | Every number on screen states what it is based on |
| 13 | Global search, CSV exports, settings, demo reset UI, empty/error/loading states on every screen | No screen can render a blank panel or an unhandled spinner |
| 14 | Test hardening: 21 API tests including a full journey, Playwright smoke across all ten screens, screenshot capture, Docker + nginx | `docker compose up --build` on a clean machine, e2e green against the built app |
| 15 | Documentation, second accessibility pass (contrast, skip link, focus trap), cleanup, ZIP | 21 documents, 18 screenshots, no `TODO` in shipped code |

**Friday demo:** the full loop from a clean Docker volume, plus the analytics screen's
"not measured" rows.

## What actually took longer than planned

| Item | Planned | Actual | Cause |
| --- | --- | --- | --- |
| Dashboard endpoint | half a day | a day | Eleven panels, each with its own query and its own empty state |
| Analytics definitions | half a day | a day | Writing a defensible definition per metric took longer than the SQL |
| Seed dataset | half a day | a day | Names, quotes and dates had to be coherent across seven linked tables |
| Playwright stability | 2 hours | half a day | Selector ambiguity, and a focus/contrast defect it exposed |

## What was cut

| Cut | Why | Where it is recorded |
| --- | --- | --- |
| Authentication | Not the thing being evaluated; faking it would be worse | [AUTH.md](AUTH.md) |
| Audio recording | Media retention and consent is its own project | [17-limitations-and-next-steps.md](17-limitations-and-next-steps.md) |
| Email dispatch | Deliverability and compliance, not research management | [01-product-brief.md](01-product-brief.md) |
| Insight merging | Real need, but not on the critical path | [17-limitations-and-next-steps.md](17-limitations-and-next-steps.md) |
| Automated accessibility checks | Manual pass found real defects; automation is the follow-up | [14-accessibility.md](14-accessibility.md) |

## Definition of done used throughout

A feature was done when all six were true:

1. It works against the real API, not a mock.
2. It has loading, empty, filtered-empty and error states.
3. It writes an activity-log entry (if it mutates).
4. It is reachable from somewhere a user would look, not only by typing a URL.
5. It is covered by a test or a documented manual check.
6. Its numbers and labels are honest — no invented metric, no unlabelled assumption.

## If the three weeks were repeated

- Write the seed dataset on day 2, not day 7. Every screen was designed against placeholder
  JSON and had to be re-checked once real shapes arrived.
- Build the analytics definitions with the reviewer, not alone. The `pending_baseline` decision
  was the most valuable hour of week 3 and it nearly happened on day 14.
- Add `@axe-core/playwright` on day 6; the contrast defect would have been caught in seconds
  instead of while writing the design-system document.
- Keep the Friday demo, every week. Twice it exposed a misunderstanding that would have cost a
  day later.

## The one-week version, if that is the constraint

Skip templates, analytics, search and CSV export; keep the loop: project → participant →
recruitment → interview → evidence → insight → decision. It is 60% of the value and it is the
part a reviewer must be able to touch.
