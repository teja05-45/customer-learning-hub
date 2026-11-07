# Business workflows

The product is one chain, not a set of screens:

```
Research project → Customer discovery → Recruitment → Consent → Session / async feedback
→ Evidence → Insights → Decisions → Actions → Outcome measurement
```

Nine workflows are defined below. Each states the trigger, the records that change, the
authorization rule, and the evidence that it was executed. Detailed row-by-row status, including the
permissions column, is in [`workflow-validation-matrix.md`](workflow-validation-matrix.md); the
security model is in [`authorization-and-permissions.md`](authorization-and-permissions.md).

## 1. Create a research project and its questions

**Trigger:** a business question needs customer evidence.

1. A researcher (or admin) opens `/projects/new` and picks a template or starts blank.
2. Required: name, objective, at least one business function. Optional: methodology, priority,
   target segments, owner, dates, questions.
3. `POST /projects` validates and creates the project plus its questions, grants the creator
   `project_owner`, and writes an activity event.
4. The project appears in the sidebar switcher for everyone with a grant; the owner can add members.

**Records:** `research_projects`, `project_questions`, `project_memberships`, `activity`.
**Authorization:** workspace `researcher`/`admin` may create. Creation is the only project operation
that does not require an existing membership.
**Evidence:** `test_project_authorization.py` (creation grants owner, tested indirectly);
`journey.spec.ts` creates a project and question through the API; `smoke.spec.ts` renders the screen.
**Failure handling:** missing business function → `422`; deadline before start → `400`; duplicate or
invalid ids → `404`.

## 2. Discover customers and read their history

**Trigger:** the team needs a cohort.

1. `/participants` searches and filters the synthetic directory by segment, eligibility, purchase
   context and sort order.
2. `/participants/:id` shows participation history, per-interview evidence and insight counts,
   feedback sources with depth/verification, and recruitment records.
3. Participants are workspace-level people; visibility is derived from the projects they appear in.
4. There are no email addresses, phone numbers or addresses in the model, so there is nothing to leak.

**Records:** `participants`, plus joins to recruitment, interviews, evidence, feedback, insights.
**Authorization:** read if the user can read any project the participant appears in; edit requires
editor standing on one of those projects.
**Evidence:** `test_unauthorized_project_cannot_be_read`, `test_nested_customer_records_do_not_leak`;
`workflows.spec.ts` "a customer profile shows cross-project feedback history".
**Failure handling:** a customer outside every visible project returns `403`, not an empty profile.

## 3. Recruit a participant

**Trigger:** a shortlisted customer for a study.

1. Select a participant for the project (`selected`).
2. Move through the pipeline: `invited → responded → scheduled → completed`, or
   `declined`/`no_response`.
3. Every stage change appends to stage history with actor and timestamp; the current stage is derived.
4. Response rate uses a defined denominator (contacted records), shown with its basis.

**Records:** `recruitment_records`, append-only `recruitment_stage_history`, activity.
**Authorization:** project editor (and workspace researcher/admin).
**Evidence:** `journey.spec.ts` select → invite → respond; `smoke.spec.ts` screen load.
**Failure handling:** a contact-consent-withdrawn participant cannot be booked into a new session.

## 4. Record and withdraw consent

**Trigger:** a session is being arranged, or a participant changes their mind.

1. Consent is requested, then granted/denied/withdrawn. Records are **append-only**; withdrawal adds a
   new row, it does not edit the grant.
2. A session cannot enable recording without a recorded grant.
3. **Withdrawal consequences:** the interview is cancelled if it had not happened; other future
   sessions for that participant in the project are cancelled; `contact_consent` becomes `withdrawn`;
   new bookings are rejected; interview and participant activity events are written.
4. Previously captured evidence and feedback are retained, because withdrawal stops future contact; it
   does not retroactively erase lawfully collected research. A production retention/deletion policy is
   still required and is explicitly out of scope.

**Records:** `consent_records` (append-only), `interviews`, `participants.contact_consent`, `activity`.
**Authorization:** project editor (workspace researcher/admin).
**Evidence:** `test_consent_withdrawal.py` (4 tests); `workflows.spec.ts` "consent withdrawal is
recorded and stops future contact"; screenshot `25-consent-withdrawal.png`.
**Failure handling:** booking a withdrawn participant → `400` with a rule message.

## 5. Run a session or capture asynchronous feedback

**Trigger:** a scheduled interview, or a survey/support/review/import that already exists.

- **Session:** schedule, reschedule, cancel, complete. The guide is neutral; notes and summary are
  captured; consent is a precondition for recording. Status transitions are validated.
- **Async feedback:** one register for interviews, written feedback, forms, surveys, support, reviews
  and imports. Each source carries a depth label (an interview is deeper than a survey) and a
  verification state.

**Records:** `interviews`, `interview_questions`, `feedback_records`; promoting feedback creates an
evidence row.
**Authorization:** project editor; read-only members can read.
**Evidence:** `journey.spec.ts` schedules/completes; `feedback.spec.ts` create → verify → delete;
`traceability.spec.ts` survey → evidence without an interview.
**Failure handling:** completing an interview before its scheduled state, or verifying feedback
without a source reference, is rejected.

## 6. Capture, review and correct evidence

**Trigger:** something a customer said or did that may matter.

1. Capture one of five evidence types, linked to a project and optionally a participant/interview.
2. A provenance snapshot records where it came from; edits are audited.
3. Review marks it reviewed/rejected with a reviewer and note; correction preserves the trail.
4. Evidence can be supporting, contradictory or contextual for an insight. Contradictory evidence is a
   first-class outcome, not hidden.

**Records:** `evidence`, provenance fields, review fields, audit/activity.
**Authorization:** project editor for writes; project reader for reads.
**Evidence:** `journey.spec.ts` quote + contradictory evidence, review and provenance correction;
`traceability.spec.ts`; backend relationship-integrity tests.
**Failure handling:** linking evidence from another project is refused; a contextual-only insight
cannot be presented as supported.

## 7. Turn evidence into a reviewed insight

**Trigger:** a pattern worth acting on.

1. Create an insight with statement, confidence, limitations and segments.
2. Link evidence with a role (supporting/contradictory/contextual) and a rationale.
3. Unlinking is audited; the insight keeps its limitations and sample-size disclosure.
4. Review state distinguishes draft from reviewed.

**Records:** `insights`, `insight_evidence` (role + rationale), activity.
**Authorization:** project editor to create/edit; reader to read.
**Evidence:** `journey.spec.ts` edit and reload; `traceability.spec.ts` grouped evidence and unlink
audit; `test_feedback_evidence_insights_from_another_project_are_denied`.
**Failure handling:** evidence from an inaccessible project → `403`; empty statement → `422`.

## 8. Decide, assign actions and own them

**Trigger:** the team chooses a response.

1. A business owner/CEO/admin records a decision: problem, rationale, limitations, status.
2. Link the insight(s) and evidence it rests on. Without linked customer evidence the decision is
   labelled **internal judgement** rather than presented as research-led.
3. Add actions with a named owner, due date and priority; overdue is derived from the due date, not
   stored as a status.
4. A decision may start without a project; linking project evidence/insight adopts that project, and
   cross-project links are rejected.

**Records:** `decisions`, `decision_insights`, `business_actions`, activity.
**Authorization:** workspace `business_owner`/`ceo`/`admin` **and** project editor/owner. A viewer
cannot write even with a business role.
**Evidence:** `journey.spec.ts` creates a decision as business owner and adds an action;
`test_viewer_cannot_write`, `test_cross_project_decision_link_is_rejected`.
**Failure handling:** unevidenced decisions are allowed but labelled; orphan decisions are visible
only to their owner/admin until attached.

## 9. Measure the outcome and close the loop

**Trigger:** the action has had time to produce a result.

1. Plan an outcome: metric, baseline, target, direction, measurement window, owner, data source.
2. Record the actual result. Status is **derived**:
   - no result → measurement pending;
   - result present → achieved / not achieved / inconclusive from actual, target and direction;
   - a measured status submitted without a result is rejected.
3. `/outcomes`, the project journey and analytics show measurement gaps. The dashboard asks whether
   anything reached a decision and whether it worked.
4. Every status change writes an audit event.

**Records:** `outcomes`, audit/activity.
**Authorization:** workspace `business_owner`/`ceo`/`admin` and project editor/owner; researcher and
CX can read.
**Evidence:** `test_outcomes.py` (9 tests); `workflows.spec.ts` plan → record → derived status;
`test_decisions_and_outcomes_from_another_project_are_denied`.
**Failure handling:** result without a target → `inconclusive`; measured status without result →
`400`; reversed seed window → regression test.

## Cross-cutting: journey, search, analytics, exports

- **Learning journey** (`/projects/:id/journey`) derives nine stages and a timeline from real records.
  It is read-only by design: actions happen on the entity's own page under its own rules.
- **Search** covers seven entity types and is scoped to visible projects.
- **Analytics** labels every metric with its basis and sample size; it never presents a small sample as
  significant.
- **Exports** are CSV with correct headers, Unicode, formula-injection safety and audit logging, and
  contain only records from projects the caller can read.

## Demo path (about eight minutes)

1. Sign in as **Priya Menon** (researcher) and open the shampoo project: questions, recruitment,
   sessions, evidence.
2. Capture a contradictory piece of evidence, then link it to an insight and note the limitation.
3. Switch to **Rohan** (business owner) and record a decision and an action from that insight.
4. Record the outcome result; show achieved/not achieved is derived.
5. Switch to **Asha** (CEO, viewer everywhere) to show read-only access.
6. Switch to **Vikram** (CX, editor on the shampoo study only) and open a project he has no grant on to
   show the API's `403` and the access-denied screen.
7. As Priya, open Project → Members and revoke Vikram's access; reload as Vikram to show it is gone.
