# Workflow validation matrix

The application is one chain, not a set of screens:

```
Research project → Customer discovery → Recruitment → Consent → Sessions / async feedback
→ Evidence → Insights → Decisions → Actions → Outcome measurement
```

Every row below was exercised through the real API and, where a screen exists, through Playwright.
The "Database" column names the records that change; "Permissions" names the API-enforced rule, not
the hidden UI control.

| Workflow | UI | API | Database | Permissions | End-to-end test | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Demo sign-in / session | Login page, role cards, password form | `POST /auth/demo`, `POST /auth/login`, `GET /session`, `POST /auth/logout` | `sessions`, `users.last_seen_at` | Demo entry only when `DEMO_MODE=true`; every other route requires a session | `smoke.spec.ts`, all suites call `enterAs` | Verified |
| Project creation & discovery questions | `/projects`, `/projects/new`, project detail "Questions & context" | `POST/PATCH /projects`, question endpoints | `research_projects`, `project_questions` | Researcher/admin write | `journey.spec.ts` creates a project and question through the public API; screen load in `smoke.spec.ts` | Verified |
| Customer directory search/filter/sort | `/participants` | `GET /participants?q=&segment=&eligibility=&sort=` | reads `participants` | Authenticated read | `smoke.spec.ts`, existing participants tests | Verified |
| Customer profile history | `/participants/:id` | `GET /participants/{id}` returns participation, feedback and insight counts | joins interviews, feedback, evidence, insight links | Authenticated read; no contact fields exist | `workflows.spec.ts` → "a customer profile shows cross-project feedback history" | Verified |
| Recruitment pipeline | `/recruitment`, project detail "Recruitment" | `POST /recruitment`, `PATCH /recruitment/{id}` | `recruitment_records`, append-only stage history | Researcher/admin write | `journey.spec.ts` select → invite → respond; `smoke.spec.ts` load | Verified |
| Consent grant | Interview consent section, consent dialog | `POST /interviews/{id}/consent` | `consent_records` (append-only), interview status | Researcher/admin; recording cannot enable without recorded consent | `journey.spec.ts` grants participation consent | Verified |
| Consent withdrawal | Same dialog, decision = Withdrawn | `POST /interviews/{id}/consent` | new `consent_records` row; interview `cancelled`; participant `contact_consent=withdrawn`; audit events | Researcher/admin. Future sessions cancelled; future bookings rejected with 400; evidence retained | `workflows.spec.ts` → "consent withdrawal is recorded and stops future contact"; `test_consent_withdrawal.py` (4 tests) | Verified |
| Session scheduling and completion | `/interviews`, `/interviews/:id` | `POST/PATCH /interviews` | `interviews`, guide questions | Researcher/admin write | `journey.spec.ts` schedules and completes; `smoke.spec.ts` load | Verified |
| Asynchronous feedback | `/feedback` | `GET/POST/PATCH/DELETE /feedback` | `feedback_sources`, evidence row on promotion | Researcher/admin write; verification requires a source reference | `feedback.spec.ts` create → verify → delete; `traceability.spec.ts` survey → evidence | Verified |
| Evidence capture and review | `/evidence`, `/evidence/:id`, add-evidence dialog | `POST/PATCH /evidence`, review and provenance endpoints | `evidence`, provenance snapshot, review fields; audit | Researcher/admin write | `journey.spec.ts` quote + contradictory evidence, review and provenance correction; `traceability.spec.ts` | Verified |
| Insight creation and evidence links | `/insights`, `/insights/:id` | `POST/PATCH /insights`, `POST /insights/{id}/evidence` | `insights`, `insight_evidence` with role + rationale | Researcher/admin write | `journey.spec.ts` edit and reload; `traceability.spec.ts` grouped evidence and unlink audit | Verified |
| Decision with linked insight | `/decisions`, `/decisions/:id` | `POST /decisions` | `decisions`, `decision_insights` | Business owner/CEO/admin write | `journey.spec.ts` creates decision as business owner | Verified |
| Action ownership and due date | `/actions`, decision detail | `POST /decisions/{id}/actions`, `PATCH /actions/{id}` | `business_actions` | Business owner/CEO/admin write | `journey.spec.ts` adds an action; dashboard shows overdue actions | Verified |
| Outcome measurement | `/outcomes`; project journey "Outcomes" | `GET/POST/PATCH /outcomes` | `outcomes`, audit event on every status change | Business owner/CEO/admin write; researcher and CX can read | `workflows.spec.ts` plan → record → derived status; `test_outcomes.py` (9 tests) | Verified |
| Learning-journey board/timeline | Project detail → "Learning journey" | `GET /projects/{id}/journey` | derived only; no writes | Authenticated read; record edits happen on the record's own page | `workflows.spec.ts` board + timeline; `test_journey_view.py` | Verified |
| CSV exports | `/settings` | export endpoints | read-only; export audit event | Admin for full exports | `exports.spec.ts` (all downloads parse, labelled, injection-safe) | Verified |
| Workspace role permissions | UI hides some actions, API is authoritative | role middleware on unsafe methods | no role change from browser | Workspace-level roles **and** project membership | `test_project_authorization.py` (16 tests), `test_outcomes.py` permission test | Verified |
| Project-level data isolation | Project switcher lists only accessible projects; access-denied screen on `403` | every project/record endpoint checks membership; lists, dashboard, analytics, search and exports are scoped | `project_memberships` (viewer/editor/project_owner); admins implicit owners | project membership at the requested level; workspace role must also allow the action | `test_project_authorization.py`: reads, nested records, aggregates, exports, search, cross-project links, viewer write, owner-only membership, revocation | Verified |
| Global search | command palette, list filters | `/search`, list `q` params | reads seven entity types | authenticated read | `journey.spec.ts` search; `smoke.spec.ts` keyboard search | Partially verified — correct results, unindexed scans |

## Stage detail

### 1. Project and discovery

Entry point is `/projects/new`, which requires a name, objective and at least one business function;
the API repeats the validation. A project owns questions, target segments, recruitment records and
everything downstream. Deletion is not exposed; archiving preserves history. Creating a project grants its creator
`project_owner`; other users need an explicit membership grant. Workspace administrators are implicit
owners of every project.

### 2. Recruitment and consent

Recruitment moves through `selected → invited → responded → scheduled → completed` (or
`declined`/`no_response`). Consent is append-only: granting twice does not delete the first record,
and withdrawal adds a new record rather than mutating the old one. Withdrawal now has consequences:

- `consent_records` keeps the original grant and the new withdrawal with actor, timestamp, scope and note;
- the interview is cancelled if it had not happened;
- any other future session for that participant in the same project is cancelled;
- the participant's `contact_consent` becomes `withdrawn`;
- new interview bookings for that participant are rejected by the API;
- previously captured evidence and feedback remain, because withdrawal stops future contact and does
  not retrospectively erase research that was lawfully collected. A production retention/deletion
  policy still has to be configured; the prototype does not claim to implement one.

Audit events are written for the interview and the participant. Tests: `test_consent_withdrawal.py`,
`workflows.spec.ts`.

### 3. Sessions and feedback

A session can be scheduled, rescheduled, cancelled or completed. Consent is a precondition for
recording; the prototype stores no audio. Asynchronous feedback is a first-class source with a depth
label (`deep`, `medium`, `limited`, `context`) so a survey is never presented as an interview. A
feedback source can be promoted to evidence, preserving its reference and collection date.

### 4. Evidence and insights

Evidence keeps the customer's words and the researcher's interpretation separate. Five evidence
types are supported, including contradictory evidence. Insights link evidence with a role
(`supporting`, `contradictory`, `contextual`); an insight with only contextual evidence is not shown
as supported. Unlinking is audited and does not delete the underlying records.

### 5. Decisions and actions

A decision records problem, rationale and limitations, and links insights. A decision without linked
customer evidence is labelled "internal judgement". Actions have an owner, due date, priority and
status; overdue is derived from the due date, not stored as a separate flag.

### 6. Outcomes

An outcome belongs to a decision and optionally to one of its actions. It records metric, baseline,
target, unit, direction, measurement window, owner, data source and actual result.

Calculation rules:

- no actual result → `planned` before the window opens, `measurement_pending` once it has started;
- actual result without a target → `inconclusive` (never "achieved");
- increase: `actual >= target` → `achieved`, otherwise `not_achieved`;
- decrease: `actual <= target` → `achieved`, otherwise `not_achieved`;
- an explicit measured status without an actual result is rejected with HTTP 400;
- `recorded_at` is set by the server when a result is recorded and cleared if the result is removed.

This prevents the common demo trick of typing "achieved" without data. Tests: `test_outcomes.py`,
`workflows.spec.ts`.

### 7. Journey views

The board and timeline are **derived** from the records above, not stored separately. Nine columns
map to the workflow stages; each card links to the real record. The timeline includes project start
and deadline, recruitment responses, sessions, feedback, evidence, insights, decisions, actions and
outcome windows, with past/upcoming/overdue states calculated against today. There is no drag-and-drop
because status is owned by the entity's own validated endpoint; the screen states this instead of
offering a decorative interaction that would bypass validation.

## End-to-end test evidence

| Spec | Covers |
| --- | --- |
| `smoke.spec.ts` | every primary screen renders; deep links; 404; API error state; skip link and keyboard search |
| `journey.spec.ts` | project → participant → recruitment → consent → session → evidence (including contradictory) → insight edit → decision → action → search |
| `traceability.spec.ts` | survey → evidence without interview; evidence → insight → decision; cross-project link refusal; unlink audit; contextual-only insight |
| `feedback.spec.ts` | feedback create, depth/provenance labels, verify, delete |
| `exports.spec.ts` | every Settings CSV download |
| `workflows.spec.ts` | journey board/timeline, profile feedback history, outcome lifecycle, consent withdrawal |
| `a11y.spec.ts` | 13 primary screens, traceability screens, add-evidence dialog, command palette |
| `responsive.spec.ts` | 375/768/1024/1440 px, navigation shape, authentication screen |

Final run against the Docker build: **24 passed**.
