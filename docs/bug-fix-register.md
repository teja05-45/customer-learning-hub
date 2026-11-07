# Bug-fix register

Severity: **Critical** blocks a core promise or exposes data · **High** breaks an important workflow
or delivers a false claim · **Medium** degrades usability or performance · **Low** cosmetic or
defensive.

| ID | Severity | Defect | Status |
| --- | --- | --- | --- |
| QA-01 | Critical | Consent withdrawal had no effect | Fixed |
| QA-02 | High | Outcome measurement did not exist | Fixed |
| QA-03 | High | Customer profile omitted feedback history | Fixed |
| QA-04 | High | Learning-journey board and timeline missing | Fixed |
| QA-05 | High | Approved palette was never implemented despite the delivery claim | Fixed |
| QA-06 | High | Seeded outcome windows were reversed, blocking every result update | Fixed |
| QA-07 | Medium | Past timeline milestones were labelled "Upcoming" | Fixed |
| QA-08 | Medium | 1 MB entry chunk | Fixed |
| QA-09 | Medium | Section landmarks unnamed; new palette failed contrast | Fixed |
| QA-10 | Critical | No project-level authorization boundary | **Fixed — 16 adversarial tests** |
| QA-11 | Low | Leading-wildcard search cannot use an index | **Open — measured** |
| QA-12 | Environment | Playwright browser binary missing | Fixed (installed Chromium) |

---

## QA-01 — Consent withdrawal recorded nothing meaningful

**Reproduction (before fix)**

1. Sign in as Priya Menon.
2. Open a scheduled interview → Consent → Record.
3. Choose **Withdrawn** and save.
4. A consent row appears, but the session remains scheduled, the participant can still be booked, and
   no downstream action changes.

**Root cause:** the consent endpoint appended a record but had no lifecycle rules. It did not inspect
the decision, cancel future sessions, update the participant's contact flag, or write audit events.

**Fix:** `backend/app/api/v1/endpoints/interviews.py` now:

- keeps the previous grant and appends the withdrawal (scope, actor, timestamp, note);
- cancels an uncompleted session and any other future session for that participant in the project;
- sets `participant.contact_consent = "withdrawn"`;
- blocks new bookings for withdrawn or declined participants with a 400;
- writes interview and participant audit events;
- preserves existing evidence and feedback.

**Regression test:** `backend/tests/test_consent_withdrawal.py` (4 tests) and
`frontend/e2e/workflows.spec.ts` → "consent withdrawal is recorded and stops future contact".

**Verification:** passed in the final backend run and in the 24-test Playwright run against Docker.

---

## QA-02 — Outcome measurement absent

**Reproduction:** open any decision and look for a way to record whether the expected change
happened. No model, endpoint, UI or test existed.

**Fix:** new `Outcome` model, enum values, schemas, endpoints, migration `c8e3a1d5f204`, seed data,
`/outcomes` page, journey "Outcomes" column, nav entry and types. Status is server-derived from
actual/target/direction; a measured status without a result is refused.

**Regression test:** `backend/tests/test_outcomes.py` (9 tests) + `workflows.spec.ts`.

**Verification:** planned, recorded, derived achieved/inconclusive and permission paths passed.

---

## QA-03 — Customer profile had no feedback history

**Reproduction:** open `/participants/{id}`. Only interviews and recruitment were shown; feedback
sources were not connected to the person.

**Fix:** `GET /participants/{id}` now returns `feedback_history` (project, source type, depth,
verification, quote, interpretation, collected date) and a derived `insight_count` per interview.
The profile renders a Feedback history section and an Insights column.

**Regression test:** `test_journey_view.py::test_profile_includes_feedback_history_and_insight_counts`
compares the count with a join rather than trusting a hard-coded value; `workflows.spec.ts` reads the
section in the browser.

**Verification:** passed.

---

## QA-04 — Learning-journey views absent

**Reproduction:** project detail had tabs for questions, recruitment, interviews, evidence, insights
and decisions, but no board or timeline.

**Fix:** `app/services/journey.py` derives nine stages and a chronological timeline from real records.
`JourneyBoard.tsx` renders Board and Timeline; cards link to their record. No drag-and-drop is offered
because status changes must go through the record's validated endpoint.

**Regression test:** `test_journey_view.py`, `workflows.spec.ts`.

**Verification:** board cards resolve to real API records; timeline is date-ordered; responsive
layout does not overflow the page.

---

## QA-05 — The approved palette was never implemented

**Reproduction:** the delivery report and briefing describe a white/`#F7F7F5` Notion-style workspace
with Inter, `#347A69` and `#7565B5`. The repository actually rendered a cream `#F7F5EF` canvas, dark
green `#103F32` chrome and serif page titles. `git log` contains no redesign commit.

**Fix:** `frontend/src/styles/notion.css` is loaded last and defines the approved tokens and the
overrides for the shell, tables, forms, pills, notices, evidence interpretation blocks, login and
journey surfaces. Serif titles were replaced with Inter. Emerald CSS remains in the tree as history.

**Verification:** screenshots were regenerated from the production Docker build. Axe passes after
adjusting the secondary text token for contrast (see QA-09).

**Note:** this is recorded as a delivery/documentation defect as well as a visual one. The previous
report claimed work that did not exist.

---

## QA-06 — Reversed seeded outcome windows blocked result recording

**Reproduction**

1. Sign in as a business owner.
2. Open `/outcomes`.
3. Record an actual result for "Second purchase within 60 days of the trial".
4. The API returns `400 rule_violation: The measurement end date cannot be before the start date.`

**Root cause:** `_seed_outcomes` passed `-30, 30` to `_d(days_ago)`, producing start = today + 30
days and end = today − 30 days. The update endpoint correctly rejected the invalid window before
writing, so the product looked broken from the UI.

**Fix:** seed rows now pass `30, -30` and `-7, -45`. A regression test asserts every seeded window is
chronological.

**Verification:** `PATCH /outcomes/{id}` returns 200 with status `achieved`; the browser test records
30 % against a 28 % target; the record survives reload and is confirmed through the API.

---

## QA-07 — Past milestones labelled "Upcoming"

**Reproduction:** project → Learning journey → Timeline. OUT-001 "measurement starts 7 Oct 2026" was
tagged **Upcoming** on 6 Nov 2026. The project deadline was always tagged Upcoming, even in the past.

**Root cause:** `journey.py` hard-coded `"upcoming"` for project deadline, action due dates and
outcome start/end, instead of comparing with `today`.

**Fix:** state is derived: `overdue` for an unmeasured outcome or incomplete action past its due date,
`upcoming` only for future dates, otherwise `past`.

**Regression test:** `test_journey_view.py` fails if any timeline item dated before today is
`upcoming`.

**Verification:** passed; regenerated timeline screenshot shows the measurement start as Past.

---

## QA-08 — 1 MB entry chunk

**Baseline:** `index-*.js` 1,011.67 kB; Vite warned about chunks over 500 kB.

**Fix:** route-level `React.lazy` for every screen except the shell/dashboard, with a Suspense
fallback. No feature was removed.

**Result:** entry 261.65 kB (81.70 kB gzip); largest chunk is Recharts' categorical chart module at
382.81 kB (105.76 kB gzip); no >500 kB advisory. The dashboard and charts still load normally.

**Verification:** `npm run build` and the full Playwright suite against the container build.

---

## QA-09 — Accessibility regressions found during the palette change

**Reproduction:** the first axe run against the new palette reported serious `color-contrast`
violations on `.brand-sub`, nav section labels, `.kbd` and table headers. `SectionCard` also rendered
unnamed `<section>` elements, so tests could not address "Consent", "Feedback history" or
"Participation history" as regions.

**Root cause:** the approved `#787774` is 4.48:1 on white and ≈4.2:1 on `#F7F7F5`; small labels need
4.5:1. Section cards never exposed a label.

**Fix:** secondary text token is `#6f6e6a` (≈4.9:1 on white, ≈4.5:1 on the rail); `SectionCard`
accepts an `aria-label` from a string title.

**Verification:** axe passes all 13 primary screens plus the traceability/dialog cases; the new
workflow tests use the named regions.

---

## QA-10 — Project-scoped authorization (FIXED, P0)

> **Resolved 7 November 2026.** `ProjectMembership` and `ProjectRole` were added with migration
> `d4e8f1a2c7b9`, a least-privilege backfill and a central `services/access.py`. Every project-scoped
> read and write now checks membership; lists, dashboard, analytics, search and exports are scoped.
> `backend/tests/test_project_authorization.py` adds 16 adversarial HTTP tests. The historical
> analysis below is retained to show why a superficial fix was rejected. The authoritative current
> register is [`final-debug-register.md`](final-debug-register.md).

**Original reproduction:** sign in as any role. Every project ID returned by `/projects` can be read, and
records in any project can be listed, because authorization is workspace-wide role-based. There is no
membership table between users and projects.

**Why it was not implemented in this pass:** a safe implementation needs a membership model, an
invitation/administration flow, backfill for existing projects, read and write filters in every list
and detail endpoint, service-layer checks, migration and adversarial tests. Adding a superficial
frontend guard would create a false sense of security and would break existing seeded workflows
without a membership assignment UI.

**Decision at the time:** documented as an unresolved P0 rather than pretending it was complete. It
was subsequently implemented in the release pass (see the resolution note above). Multi-tenant
isolation above the workspace is still not provided.

**Required next work:** `project_memberships(user_id, project_id, role)`; filter every query by
membership; 403 on non-member reads; admin membership management; migration/backfill; adversarial
tests for list, detail, search, export and relationship endpoints.

---

## QA-11 — Leading-wildcard search (OPEN, measured)

**Implementation:** `lower(column) LIKE '%term%'` for participants, projects, evidence and other
lists, plus the global search service.

**Measured:** a synthetic SQLite table of 50,000 rows, five-run median on this machine:

| Approach | Median | Query plan |
| --- | --- | --- |
| Current `LIKE '%abc%'` | 17.91 ms | `SCAN participants` |
| FTS5 trigram match | 0.036 ms (index lookup only) | `SCAN participants_fts VIRTUAL TABLE INDEX 0:M2` |

At the demo's 10 participants the scan is sub-millisecond, so no index was added in this pass: a
B-tree on `display_name` cannot serve a leading wildcard and would be dead weight. The limitation is
real at scale. The defensible next step is an FTS5 trigram index (with sync triggers and a fallback
for queries shorter than three characters) or PostgreSQL `pg_trgm`, benchmarked with the join and
pagination included. Until then, search is correct but unindexed.

---

## QA-12 — Playwright could not launch

**Reproduction:** `npx playwright test` failed all 20 tests with
`Executable doesn't exist at ...chrome-headless-shell.exe`.

**Root cause:** the browser binary was never installed in this environment; this was not an
application failure.

**Fix:** `npx playwright install chromium` (118.1 MiB). The suite then passed 20/20 before the new
tests and 24/24 after.

---

## Checks that were not turned into passes

- No test was skipped, weakened or deleted to obtain the final result.
- The Docker check used the real Compose build and a named volume; the volume was not deleted.
- Deployment to a hosted environment was not performed, so hosted readiness is not claimed.
- Full WCAG 2.2 AA conformance is not claimed from axe alone; keyboard paths and the command palette
  were also exercised, but a manual screen-reader audit remains outstanding.
