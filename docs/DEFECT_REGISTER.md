# Defect Register

Only defects with observed evidence are listed as confirmed. The four symptoms named in the
brief were investigated directly; where they could not be reproduced, that is stated rather
than invented.

## Confirmed and fixed

### D-001 — Recruitment timeline always empty

- **Feature:** Recruitment pipeline → "View timeline".
- **Observed:** Every record returned `events: []`; the modal always showed "No history
  recorded yet." Confirmed with `GET /api/v1/recruitment` (first item events = 0).
- **Expected:** The list carries the stage history for each record.
- **Root cause:** `list_recruitment` called `recruitment_out(...)` without
  `include_events=True`. The serializer also resolved actors only from `updated_by_id`, so even
  single-event payloads would have shown no actor.
- **Severity:** High (the pipeline's audit trail was invisible).
- **Fix:** Return events from the list; build the actor map from the record editor and every
  event actor.
- **Verification:** `test_recruitment_history_survives_list_view`,
  `test_scheduling_and_completing_an_interview_writes_history`.

### D-002 — Interview lifecycle bypassed recruitment history

- **Feature:** Interview scheduling/completion → recruitment stage.
- **Observed:** The stage moved to `scheduled` and `completed`, but the history contained only
  the earlier board transitions (confirmed by assertion on the event set).
- **Expected:** Every stage change is recorded, including side effects.
- **Root cause:** `interviews.py` assigned `recruitment.stage` directly instead of using the
  transition service.
- **Severity:** High (silent data loss in the audit trail).
- **Fix:** `services/pipeline.advance_stage` owns the change and appends an event; interview
  flows call it, with `force=True` for legitimate jumps.
- **Verification:** Journey test stage-set assertion; pipeline history test.

### D-003 — Cross-project evidence could be linked to an insight

- **Feature:** Insight evidence linking.
- **Observed:** `POST /insights/{id}/evidence` accepted evidence belonging to another project.
  The create endpoint rejected it, so the rule was inconsistent.
- **Expected:** Evidence is only meaningful inside the project that produced it.
- **Root cause:** Missing project check in `link_evidence`.
- **Severity:** High (undermines traceability).
- **Fix:** Reject with `rule_violation` and `details.evidence_id`.
- **Verification:** `test_insight_rejects_evidence_from_another_project`.

### D-004 — Project total wrong when filtering by business function

- **Feature:** `GET /projects?business_function=`.
- **Observed:** `total` counted all projects while `items` was filtered in memory afterwards.
- **Expected:** Total matches the filtered rows.
- **Root cause:** Total computed before the in-memory JSON filter.
- **Severity:** Medium.
- **Fix:** Filter before pagination and derive the total from the filtered list.
- **Verification:** API behaviour checked during review; covered by the project list tests.

### D-005 — Terminal recruitment stages invisible

- **Feature:** Recruitment summary cards and "every status represented".
- **Observed:** Declines, no-responses, cancellations and withdrawals had counts in the API but
  no card; only six active stages were rendered, so visible counts did not reconcile with the
  records and a stage filter could not be selected from a card.
- **Expected:** All ten stages visible, including negative outcomes.
- **Root cause:** `PIPELINE_STAGES` in `utils/format.ts` listed six stages.
- **Severity:** Medium (misleading pipeline view).
- **Fix:** Include all ten stages with an explanatory comment.
- **Verification:** Pipeline stage-count/filter test; UI inspection.

### D-006 — Interview summary stored but never shown

- **Feature:** Interview workspace.
- **Observed:** `summary` was set by the API and absent from the detail screen.
- **Expected:** A completed conversation's summary is readable, and clearly separated from
  customer evidence.
- **Root cause:** No UI block rendered `data.summary`.
- **Severity:** Medium (captured work invisible).
- **Fix:** Added an editable "Conversation summary" card with explicit wording.
- **Verification:** Playwright journey asserts the summary is visible; typecheck/build.

### D-007 — Segment chart inaccessible

- **Feature:** Overview segment chart.
- **Observed:** axe reported `svg-img-alt` on named pie paths (serious).
- **Expected:** No serious/critical accessibility violations on primary screens.
- **Root cause:** Recharts SVG had named paths without an image role or accessible name.
- **Severity:** Medium.
- **Fix:** Role and accessible label on the chart; avoids `aria-hidden` because the SVG
  contains focusable nodes (which triggered `aria-hidden-focus` on the first attempt).
- **Verification:** `e2e/a11y.spec.ts` passes.

### D-008 — Local secrets could enter the Docker build context

- **Feature:** Backend image build.
- **Observed:** `backend/.dockerignore` did not exclude `.env`; a developer's local file would
  be copied into the image.
- **Expected:** Secret files never included.
- **Severity:** High (potential secret exposure).
- **Fix:** Exclude `.env`, `.env.*` (except the example), coverage and caches.
- **Verification:** `.dockerignore` reviewed; image built successfully afterwards.

## Confirmed product gaps, now implemented

- **G-001 Insight editing.** Only status changes existed; title, summary, interpretation,
  limitations and confidence were immutable after creation. Implemented in the detail view.
- **G-002 Evidence review.** `review_status` could be set at creation but not changed in the UI,
  and provenance could not be corrected. Implemented with explicit re-flagging on clearing.

## Investigated, not reproduced

These were reported from screenshots. Each was exercised against the running implementation
(API and browser) and did not fail; the loading states do resolve and the error states are
present. They are recorded so the investigation is auditable, not asserted as fixes.

| ID | Symptom | What was checked | Finding |
| --- | --- | --- | --- |
| N-001 | Projects page stuck on skeletons / "Refreshing…" | Endpoint 200 with 5.5 kB payload; Playwright projects screen; Vitest N/A | Renders records; loading resolves. Likely captured mid-request or against an unseeded API. |
| N-002 | Recruitment page shows zero counts | Endpoint returns 14 records and stage counts; UI cards render | Counts non-zero. The genuine related issue was D-001/D-005 (history and terminal stages). |
| N-003 | Interviews indefinite loading | Endpoint 200 (19 kB); Playwright interviews screen | Renders; error state available if the request fails. |
| N-004 | Analytics indefinite loading | Endpoint 200 (9.5 kB); Playwright analytics screen | Renders metrics, charts and empty states. |

## Suspected, not changed

- **S-001** `unverified_only` treats `provenance_status != "recorded"` as unverified. The
  `partial` status exists in the enum but is never produced, so behaviour is correct today; a
  future partial-provenance flow must define whether it counts as verified.
- **S-002** `participants_contacted` includes participants whose recruitment record was
  withdrawn. This is intentional (they were contacted) but should be documented in product
  language before leadership reads it.
- **S-003** Decision `evidence_sufficient = null` means "not assessed" even when links exist.
  Deliberate per `test_integrity.py`; the UI must not treat null as "no evidence".

## Remaining known limitations

No authentication/authorisation; SQLite single-writer; lists load unpaginated in several
screens; deletion is permanent rather than tombstoned; no automated visual regression. See
`RISKS.md`, `ROADMAP.md`, `TASKS.md`.
