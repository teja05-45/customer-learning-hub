# Core workflows

Five workflows carry the product. Each one names the screens, the API calls, the rules the
system enforces, and the failure it is designed to prevent.

---

## 1. Plan a study

**Screens:** Research projects → New project → Project detail

1. Choose a template (repeat purchase, product experience, campaign perception, customer
   journey) or start blank.
2. Set the objective, the business functions that will use it, target segments, priority and
   deadline.
3. Add research questions. Questions are first-class rows, each with an open/resolved state
   and a resolution note — a study can end with a question deliberately unanswered.

**API:** `GET /projects/templates`, `POST /projects`, `POST /projects/{id}/questions`,
`PATCH /projects/{id}/questions/{qid}`, `DELETE .../questions/{qid}`.

**Rules enforced:** a project always has a status on the lifecycle
`draft → planning → recruiting → in_progress → analysis → completed` plus `archived`; archiving
sets `archived_at` and removes the project from active counts but keeps every record.

**Failure prevented:** research that starts from "we should talk to some customers" with no
question that could ever be answered.

---

## 2. Recruit a participant

**Screens:** Participants → Project detail → Recruitment pipeline

1. Add or pick a synthetic participant: segment, purchase frequency, order count, product
   category, eligibility and an eligibility note.
2. Assign them to a project, which creates a recruitment record at `identified`.
3. Move them through the pipeline: identified → selected → invited → responded → scheduled →
   completed, with `declined`, `no_response`, `cancelled` and `withdrawn` as side exits.
4. Every stage change writes a `recruitment_events` row (from stage, to stage, note, actor).

**API:** `GET/POST /participants`, `POST /participants/{id}/assign`, `GET/POST/PATCH/DELETE
/recruitment`.

**Rules enforced:** `RECRUITMENT_TRANSITIONS` rejects illegal jumps (for example
`identified → completed`) with a 422 and an explanatory message. Terminal states can be
explicitly re-opened, because participants do change their minds. Declined and no-response
records are kept — a pipeline that quietly deletes non-responders cannot report a true
response rate.

**Failure prevented:** "we invited about ten people" — the number nobody can reconstruct.

---

## 3. Run an interview

**Screens:** Interviews → Interview detail (workspace)

1. Schedule the interview with date, duration, interviewer and channel. The default
   interview-guide questions seed the workspace.
2. Record consent per type: participation, recording, quoting, sharing internally. Each
   decision is a `consent_records` row with who recorded it and when.
3. The workspace shows the objective, the guide with each question's purpose, a note field,
   and a running list of evidence captured in this session.
4. Mark the interview complete and set a summary plus follow-up questions.

**API:** `GET /interviews/guide/default`, `POST /interviews`, `PATCH /interviews/{id}`,
`POST /interviews/{id}/consent`, `POST /interviews/{id}/recording`.

**Rules enforced:** consent status is derived from the consent records, not typed in by hand.
`recording_enabled` defaults to false and the org setting `recording_default` controls the
default for new interviews. Recording is a flag and a note — **no audio is captured**.

**Failure prevented:** a quote that appears in a deck with no record of whether the person
agreed to be quoted.

---

## 4. Turn conversations into insight

**Screens:** Interview detail → Evidence library → Insight detail

1. Capture evidence as one of five types: `verbatim_quote`, `observation`,
   `researcher_interpretation`, `contradictory_evidence`, `open_question`.
2. Each evidence row carries content, a separate interpretation field, customer context, the
   segment, provenance text and a provenance status of `recorded`, `partial` or `missing`,
   plus confidence and review status.
3. Draft an insight with a summary, an interpretation, the research question it answers,
   confidence, limitations and the segments it applies to.
4. Link evidence to the insight many-to-many, marking each link `supporting` or
   `contradictory`.
5. Move the insight through `draft → under_review → validated_internal`, or send it back with
   `needs_more_research`, or archive it.

**API:** `GET/POST/PATCH/DELETE /evidence`, `GET /evidence/stats`, `GET/POST/PATCH
/insights`, `POST /insights/{id}/evidence`, `DELETE /insights/{id}/evidence/{eid}`,
`GET /insights/{id}/related`, `GET /insights/{id}/reuse`.

**Rules enforced:** the customer's words (`content`) and the researcher's reading
(`interpretation`) are separate columns and are never merged in the UI. Contradictory evidence
is a first-class link role, so a finding that survived a counter-example says so. An insight
with no evidence is allowed but is surfaced as unsupported rather than hidden.

**Failure prevented:** the single paragraph that mixes a quote with an interpretation, so
readers cannot tell which is which.

---

## 5. Decide and follow up

**Screens:** Decisions → Decision detail → Actions → Overview

1. Register a decision: title, business function, problem statement, rationale, limitations,
   owner, date and status (`proposed → under_review → accepted`, or `rejected` / `deferred`).
2. Link the sources: insights and evidence, each with a role and a note. `evidence_sufficient`
   records whether the decision rests on customer research or on internal judgement.
3. Create follow-up actions from the decision with owner, due date, priority and status.
4. The overview and analytics screens report decisions with evidence, decisions without, and
   overdue actions.

**API:** `GET/POST/PATCH /decisions`, `POST /decisions/{id}/links`,
`DELETE /decisions/{id}/links/{kind}/{link_id}`, `POST /decisions/{id}/actions`,
`GET/POST/PATCH/DELETE /actions`.

**Rules enforced:** a decision may be recorded with `evidence_sufficient = false` — the
register is designed to expose that state, not to forbid it. Unlinking the last source resets
`evidence_sufficient` to false so the flag cannot go stale.

**Failure prevented:** the retrofit citation, where an insight is attached to a decision after
the fact to make it look researched.

---

## Cross-cutting behaviours

| Behaviour | Where it applies |
| --- | --- |
| Every create/update writes an `activity_logs` row | Projects, recruitment, interviews, evidence, insights, decisions, actions, settings |
| Every mutating response returns the updated resource | So the UI never has to guess the server's state |
| Every failure returns `{ error: { code, message, details } }` | All endpoints, including validation failures and rule violations |
| Every list endpoint supports filters and returns `items` + `total` | Consistent pagination shape across resources |
| Synthetic-data labelling is always visible | Demo banner in the shell, footer note, CSV `is_synthetic` column |
