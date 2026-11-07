# Page-by-page QA

Every route registered in `frontend/src/app/App.tsx` is listed. There is **no separate Customers or
Reports route**: customers are `participants`, and reporting is the Analytics screen plus the CSV
exports in Settings. No screenshot was invented for a page that does not exist.

Screenshots were captured from the production build in Docker at 1440×960 unless stated. All
screenshots live under `docs/screenshots/`.

## Summary

| Route | Page | Data source | Final status | Screenshot |
| --- | --- | --- | --- | --- |
| `/` | Sign in / demo entry | session API | Verified | `01-demo-entry.png` |
| `/overview` | Overview | dashboard API | Verified | `02-overview.png` |
| `/projects` | Research projects | projects API | Verified | `03-projects.png` |
| `/projects/new` | New project | projects API | Partially verified | — |
| `/projects/:projectId` | Project detail | project, journey, questions, recruitment, interviews, evidence, insights, decisions | Verified | `04-project-detail.png`, `22-project-journey-board.png`, `23-project-journey-timeline.png`, `05-project-evidence.png` |
| `/participants` | Participant directory | participants API | Verified | `06-participants.png` |
| `/participants/:participantId` | Participant profile | participant detail API | Verified | `24-participant-profile.png` |
| `/recruitment` | Recruitment pipeline | recruitment API | Verified | `07-recruitment.png` |
| `/interviews` | Interviews | interviews API | Verified | `08-interviews.png` |
| `/interviews/:interviewId` | Interview workspace | interview detail API | Verified | `09-interview-workspace.png`, `25-consent-withdrawal.png` |
| `/evidence` | Evidence library | evidence API | Verified | `20-evidence.png` |
| `/evidence/:evidenceId` | Evidence detail | evidence detail API | Verified | — (exercised in `journey.spec.ts`) |
| `/feedback` | Feedback sources | feedback API | Verified | `19-feedback-sources.png` |
| `/insights` | Insights library | insights API | Verified | `10-insights-library.png` |
| `/insights/:insightId` | Insight traceability | insight detail API | Verified | `11-insight-traceability.png` |
| `/decisions` | Decisions & actions | decisions API | Verified | `12-decision-register.png` |
| `/decisions/:decisionId` | Decision detail | decision detail API | Verified | `13-decision-detail.png` |
| `/actions` | Actions | actions API | Verified | `14-actions.png` |
| `/outcomes` | Outcome measurement | outcomes API | Verified | `21-outcomes.png`, `27-mobile-outcomes.png` |
| `/analytics` | Analytics | analytics API | Verified | `15-analytics.png` |
| `/settings` | Settings | settings, users, demo, export APIs | Verified | `16-settings.png` |
| `*` | Not found | none | Verified | — (asserted in `smoke.spec.ts`) |

Global overlays are covered too: `17-global-search.png` (command palette), `18-mobile-overview.png`
(375 px), `26-tablet-projects.png` (768 px) and `25-consent-withdrawal.png` (dialog).

## Login — `/`

- **Purpose:** create a real server session, either with email/password or, when demo mode is on, by
  choosing a demonstration role.
- **Components:** login shell, value points, password form, role cards, demo notice.
- **API:** `GET /session`, `POST /auth/demo`, `POST /auth/login`, `POST /auth/logout`.
- **Interactions tested:** role entry for Priya Menon and Asha Menon, keyboard form, small-viewport
  layout, session persistence across navigation.
- **Defects:** none in behaviour. The demo role picker is explicitly labelled as not a security
  boundary; the server ignores a forged role header on writes.
- **Status:** Verified.

## Overview — `/overview`

- **Purpose:** answer "what is the team investigating, what has it learned, and did any of it reach a
  decision?" without inflating activity into success.
- **API:** dashboard metric, segment, activity and follow-up endpoints.
- **Interactions tested:** load with seeded data, links into projects/insights/decisions/actions,
  global search shortcut, responsive collapse to one column.
- **Defects fixed:** none specific to this page; the shared section container now exposes an
  accessible name (`aria-label`), so regions such as "Recent insights" are navigable landmarks.
- **Evidence:** `smoke.spec.ts`, `a11y.spec.ts`, `responsive.spec.ts`, screenshot `02`.
- **Status:** Verified.

## Research projects — `/projects`

- **Purpose:** the project register, with owner, status, priority, business function and segments.
- **Interactions tested:** load, search/filter controls, open project, return navigation.
- **Defects:** none found. Empty and error states are present; the list is server-filtered.
- **Evidence:** `smoke.spec.ts`, screenshot `03`.
- **Status:** Verified.

## New project — `/projects/new`

- **Purpose:** create a project with an objective, methodology, functions and target segments.
- **API:** `POST /projects`; template and question support.
- **Interactions tested:** the create contract is exercised through the public API in
  `journey.spec.ts`; the visible form was inspected but not driven end-to-end in this pass.
- **Defect / limitation:** the form has client-side validation and server errors are surfaced, but a
  full UI-create → reload assertion is not automated. This is a coverage gap, not a known failure.
- **Status:** Partially verified.

## Project detail — `/projects/:projectId`

- **Purpose:** the project home: questions, target segments, recruitment, sessions, evidence,
  insights, decisions and the learning journey.
- **Components:** header, tabs, journey board/timeline, evidence-depth panel, quick actions.
- **API:** project detail, `/projects/{id}/journey`, and the related list endpoints.
- **Interactions tested:** open from list; every tab; journey cards link to real records; Board ↔
  Timeline; responsive layout; empty/loading states.
- **Defects fixed:** the timeline labelled past milestones "Upcoming" because state was hard-coded;
  it now compares dates with today. The Board is horizontally scrollable by design, while the page
  itself does not overflow.
- **Evidence:** `workflows.spec.ts`, `test_journey_view.py`, screenshots `04`, `05`, `22`, `23`.
- **Status:** Verified.

## Participant directory — `/participants`

- **Purpose:** synthetic customer directory with segment, purchase context and eligibility. No email,
  phone or address is accepted by the schema.
- **Interactions tested:** search, filters, sort, pagination/bulk controls where present, row click,
  add participant dialog reachable, empty state.
- **Defects:** none found in this pass. Bulk eligibility/assignment rules are enforced by the API.
- **Evidence:** `smoke.spec.ts`, `responsive.spec.ts`, screenshot `06`.
- **Status:** Verified.

## Participant profile — `/participants/:participantId`

- **Purpose:** a coherent research history for one customer.
- **Sections:** participation history with per-interview evidence and insight counts, feedback
  history, recruitment records, profile facts, contact handling.
- **API:** `GET /participants/{id}` now returns `feedback_history` and derived `insight_count`.
- **Interactions tested:** open from the row, read a real feedback quote and its researcher
  interpretation, depth and verification labels, cross-project source labels.
- **Defects fixed:** feedback history did not exist; insight counts were not derived.
- **Evidence:** `workflows.spec.ts`, `test_journey_view.py`, screenshot `24`.
- **Status:** Verified.

## Recruitment pipeline — `/recruitment`

- **Purpose:** show who was selected, invited, responded and scheduled, with segment coverage.
- **Interactions tested:** load, stage filters, project filter, stage transition through the API,
  response-rate denominator explanation.
- **Defects:** none found. The append-only stage history is preserved.
- **Evidence:** `journey.spec.ts`, screenshot `07`.
- **Status:** Verified.

## Interviews — `/interviews`

- **Purpose:** session register with status and project context.
- **Interactions tested:** load, filter, open a session, schedule through the API, status change.
- **Defects:** none found. Consent state is visible in the register and on detail.
- **Evidence:** `journey.spec.ts`, `smoke.spec.ts`, screenshot `08`.
- **Status:** Verified.

## Interview workspace — `/interviews/:interviewId`

- **Purpose:** one session: consent, guide, notes, summary, evidence capture, follow-up questions.
- **Interactions tested:** complete a session, record consent, withdraw consent, observe cancelled
  status and consent banner, open the consent dialog at mobile/desktop.
- **Defects fixed:** withdrawal previously had no consequences. Now it cancels future sessions,
  writes participant/interview audit events, sets `contact_consent=withdrawn`, blocks re-booking and
  preserves historical evidence.
- **Evidence:** `workflows.spec.ts`, `test_consent_withdrawal.py`, screenshots `09`, `25`.
- **Status:** Verified.

## Evidence library and detail — `/evidence`, `/evidence/:evidenceId`

- **Purpose:** preserve every quote, observation, interpretation and open question with provenance.
- **Interactions tested:** load, filter by type/interview, open detail, mark reviewed, correct
  provenance to empty, confirm "Unverified source", create evidence from feedback.
- **Defects:** none found in the evidence layer. The interpretation block uses the AI accent and is
  explicitly labelled as not the customer's words.
- **Evidence:** `journey.spec.ts`, `traceability.spec.ts`, screenshot `20`.
- **Status:** Verified.

## Feedback sources — `/feedback`

- **Purpose:** one provenance-preserving register for interviews, surveys, support, reviews and
  imports.
- **Interactions tested:** create a survey source, see depth and verification labels, verify, delete
  with confirmation, promote to evidence.
- **Defects:** none found. Verification is refused without a source reference by the API.
- **Evidence:** `feedback.spec.ts`, `traceability.spec.ts`, screenshot `19`.
- **Status:** Verified.

## Insights library and detail — `/insights`, `/insights/:insightId`

- **Purpose:** reviewed findings with confidence, limitations, segments, owner and grouped evidence.
- **Interactions tested:** load, open, edit title/limitations, save, reload and confirm persistence;
  supporting/contradictory/contextual groups; link and unlink audit; contextual-only insight warning.
- **Defects fixed:** none in this pass beyond the shared landmark improvement.
- **Evidence:** `journey.spec.ts`, `traceability.spec.ts`, screenshots `10`, `11`.
- **Status:** Verified.

## Decisions and actions — `/decisions`, `/decisions/:decisionId`, `/actions`

- **Purpose:** connect a business decision to evidence, an owner and a dated follow-up.
- **Interactions tested:** create a decision as business owner, link an insight, create an action,
  see it in the register and on the dashboard, observe overdue derivation.
- **Defects:** none found. Unevidenced decisions are labelled rather than hidden.
- **Evidence:** `journey.spec.ts`, screenshots `12`, `13`, `14`.
- **Status:** Verified.

## Outcome measurement — `/outcomes`

- **Purpose:** close the loop between a decision and the change it was expected to produce.
- **Interactions tested:** load seeded planned/pending outcomes, open "Record result", enter an
  actual value, see derived status and toast, reload, verify server value; plan a new outcome with a
  decision, metric, target and unit; status filter.
- **Defects fixed:** the page is new. During verification, the seeded measurement windows were found
  reversed (end before start), which made every `PATCH` fail with HTTP 400; the seed was corrected
  and a regression test now asserts chronological windows.
- **Evidence:** `workflows.spec.ts`, `test_outcomes.py` (9 tests), screenshot `21`, mobile `27`.
- **Status:** Verified.

## Analytics — `/analytics`

- **Purpose:** basis-labelled metrics, segment coverage, unresolved questions and measurement gaps.
- **Interactions tested:** load with real data, resize, navigate between charts and tables.
- **Defects:** none found. The page deliberately labels small samples and missing baselines.
- **Evidence:** `smoke.spec.ts`, `responsive.spec.ts`, screenshot `15`.
- **Status:** Verified.

## Settings — `/settings`

- **Purpose:** organisation name, research lead, recording default, retention, user administration,
  CSV exports and demo reset.
- **Interactions tested:** load, download every CSV, admin-only controls, reset confirmation.
- **Defects:** none found. Export filenames/headers are absolute dates, not ambiguous local strings.
- **Evidence:** `exports.spec.ts`, screenshot `16`.
- **Status:** Verified.

## Not found — `*`

- **Purpose:** explain an unknown route and offer a way back.
- **Interactions tested:** deep link to an unknown route in `smoke.spec.ts`.
- **Status:** Verified.

## Cross-page findings

1. **Design system:** the approved palette had never been implemented. `frontend/src/styles/notion.css`
   now applies it after the legacy sheets. Page titles use Inter, the rail is `#F7F7F5`, hover is
   `#F1F1EF`, primary is `#347A69`, and interpretation surfaces use `#7565B5`.
2. **Contrast:** the approved secondary `#787774` measures 4.48:1 on white and about 4.2:1 on the
   rail, below AA for the 11–13 px labels used here. The text token is `#6f6e6a`, which keeps the
   same warm grey at ≈4.9:1 on white; this is documented in the stylesheet and design note.
3. **Accessibility landmarks:** `SectionCard` now exposes a name when its title is a string, so
   sections appear as regions to assistive technology and to the test suite.
4. **No fake board:** the journey board does not offer drag-and-drop. Every status change goes through
   the entity's own validated endpoint.
5. **No fake outcomes:** a result cannot be marked achieved without an actual value, and a result
   without a target is `inconclusive`.
