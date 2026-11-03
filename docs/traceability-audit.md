# Evidence-to-Insight Traceability Audit

Date: 2026-11-03
Scope: the checkout at the start of this work, before any traceability code was written.
Baseline command results are recorded exactly as executed, not as previously reported.

## 1. Baseline verification (executed)

| Command | Result |
| --- | --- |
| `cd backend && python -m pytest -q` | **91 passed** in 51.63s |
| `cd frontend && npm run typecheck` | run after the model changes; recorded in `final-delivery-report.md` |
| `cd frontend && npx playwright test` | requires a running stack; recorded in `final-delivery-report.md` |

The reported "91 backend tests" is accurate for this checkout. The remaining
reported results (TypeScript, Vite, Playwright, nine CSV exports, responsive
widths) are re-executed as part of this work; see the delivery report.

## 2. Existing architecture

```
React 18 + TypeScript (Vite)  ──/api/v1──▶  FastAPI (routers → services → models)
TanStack Query, React Router                 SQLAlchemy 2 + Alembic, SQLite/PostgreSQL
                                             one error envelope: {error:{code,message,details}}
```

* Backend records: `research_projects`, `participants`, `recruitment_records`,
  `interviews`, `evidence`, `feedback_records`, `insights`, `decisions`, `actions`.
* Authentication: server-side sessions in an HTTP-only cookie, PBKDF2 hashes
  (`app/core/security.py`).
* Authorisation: `AuthMiddleware` (`app/core/auth.py`) protects every `/api/v1`
  route by default and applies a coarse role policy per path prefix. `/insights`,
  `/evidence` and `/feedback` writes require `researcher` or `admin`.
* Audit: `activity_logs` plus `log_activity()`; append-only, no foreign key to
  the deleted entity (intentional so history survives deletion).

## 3. Current feedback-to-evidence relationship

**None.** `FeedbackRecord` (`app/models/research.py`) stores `content`,
`interpretation`, `context`, `source_type`, `collection_method`,
`source_reference`, `collected_at` and `verification_status`. `Evidence` stores
its own `content`, `interpretation`, `provenance` and `provenance_status`.

`EvidenceCreate` requires `interview_id`, and `create_evidence` rejects the
request when the interview does not exist:

```python
interview = db.get(Interview, payload.interview_id)
if interview is None:
    raise NotFoundError("Evidence must be attached to an existing interview.")
```

Consequence: a short survey, a support ticket, a product review, a written
feedback entry or a CSV import **cannot become evidence at all**. The feedback
module can record those sources, but they never reach an insight. This is the
single largest gap against the original business problem ("customers must be
able to contribute without attending an interview").

## 4. Current evidence-to-insight relationship

`InsightEvidence` already exists as an explicit association entity:

| Column | Notes |
| --- | --- |
| `insight_id` | FK `insights.id`, `ON DELETE CASCADE` |
| `evidence_id` | FK `evidence.id`, `ON DELETE CASCADE` |
| `role` | string, default `supporting`; validated to `supporting` \| `contradictory` |
| `note` | 240 chars |
| `created_at` | timestamp |
| unique | `uq_insight_evidence (insight_id, evidence_id)` |

This is the right shape and must be extended, not duplicated. Gaps:

1. **No `contextual` classification.** Context-only feedback must currently be
   recorded as supporting (inflating the evidence base) or not recorded at all.
2. **No author on the relationship.** The `activity_logs` entry names the actor,
   but the relationship row itself cannot say who judged it.
3. **No rationale.** `note` is 240 characters and is not used by any screen; a
   classification with no stated reason cannot be reviewed later.
4. **No confidence judgement and no tags.**
5. **No `updated_at`.** Re-classifying requires delete + re-create, which loses
   the original timestamp.
6. **Delete is unlogged.** `DELETE /insights/{id}/evidence/{evidence_id}` removes
   the link without writing an audit entry, so a contradiction can be removed
   silently.
7. **No reverse read.** `EvidenceOut.insight_links` exists, but there is no
   endpoint that lists an evidence item's insights with the relationship
   rationale.

Cross-project validation already exists in both create paths and is correct:
`if insight.project_id and evidence.project_id != insight.project_id: raise
RuleViolationError(...)`. `test_journey`/`test_integrity` cover part of it. The
validation is absent when the insight has **no** project (`project_id` is
nullable), which is an explicit product decision rather than a defect: a
project-less insight may draw on any project's evidence. Documented, not hidden.

## 5. Existing database constraints

* Foreign keys are enabled on SQLite via `PRAGMA foreign_keys=ON`
  (`app/core/database.py`), so constraints are enforced in tests.
* `evidence.project_id` and `evidence.interview_id` are `ON DELETE CASCADE`;
  `participant_id` and `captured_by_id` are `SET NULL`.
* `insight_evidence` cascades from both sides.
* Insight validation is blocked without at least one link
  (`app/api/v1/endpoints/insights.py`), which is a real business rule, not a UI hint.

## 6. Identified gaps

| # | Gap | Business impact | Severity |
| --- | --- | --- | --- |
| G1 | Non-interview feedback cannot become evidence | The product's core promise fails for most customers | Critical |
| G2 | No contextual classification | Evidence counts overstate support | High |
| G3 | No rationale / author / confidence on a relationship | A reviewer cannot tell why a quote was used | High |
| G4 | Unlink is not audited | Contradictory evidence can disappear silently | High |
| G5 | No reverse endpoint for evidence → insights | The chain only works one way | Medium |
| G6 | No traceability export | The chain cannot leave the app for a review pack | Medium |
| G7 | Evidence provenance is not snapshotted | Depth/verification can drift from how it was collected | Medium |
| G8 | Duplicate link returns 409 (fine), but there is no update path | Re-classification loses history | Medium |
| G9 | No decision → evidence chain endpoint | A manager cannot walk back from an action to the words | Medium |
| G10 | `InsightEvidence.role` is only validated by Pydantic | Raw writes cannot create invalid roles, but there is no DB check | Low |

## 7. Proposed implementation

**Extend, do not duplicate.**

1. `insight_evidence` gains `rationale`, `confidence`, `tags`, `created_by_id`
   and `updated_at`; `role` accepts `contextual`. The unique constraint stays.
2. `evidence` gains `feedback_record_id` plus a provenance snapshot
   (`source_type`, `collection_method`, `research_depth`, `source_reference`,
   `verification_state`, `collected_at`). The snapshot is written when evidence
   is derived from a feedback record so the customer's words keep the depth they
   were collected with.
3. New endpoint `POST /feedback/{id}/evidence` copies the customer statement
   **verbatim** into a new evidence row. It never edits the feedback record.
4. New grouped reads: `GET /insights/{id}/evidence`,
   `GET /evidence/{id}/insights`, `GET /insights/{id}/traceability`,
   `GET /decisions/{id}/traceability`.
5. `PATCH`/`DELETE /insights/{id}/evidence/{relationship_id}` carry auth, audit
   and idempotent duplicate handling. Because one insight/evidence pair can have
   at most one relationship, the identifier accepts the relationship id or the
   evidence id (documented).
6. New export `GET /exports/traceability.csv`, one row per relationship, UTF-8
   BOM, formula-injection safe, no personal contact fields.
7. UI: three clearly separated groups, provenance per item, rationale/confidence
   capture, quality indicators that distinguish quantity from quality, and an
   explicit "unsubstantiated" state.

## 8. Risks and trade-offs

| Risk | Mitigation |
| --- | --- |
| SQLite cannot add NOT NULL columns without defaults | Alembic batch mode with server defaults; upgrade and downgrade tested on an isolated database |
| Duplicating `feedback_records` content into `evidence.content` | The copy is intentional and one-way; the evidence row records `feedback_record_id`. Neither record is ever rewritten by a link operation |
| Making `interview_id` effectively optional | It already is nullable in the model; the create endpoint keeps requiring an interview for the interview path, and adds an explicit feedback path |
| Classification remains free text at the DB level | Pydantic enforces the enum on every write path; a raw SQL write is out of the product's threat model, and adding a CHECK constraint would need another table rebuild on SQLite |
| Aggregate counts could be read as validation | The UI states quantity ≠ quality, the API exposes `unsubstantiated`/`has_conflict` rather than a score, and no field is called `validated_by_evidence` |
| Existing `POST /insights/{id}/evidence` response shape | Kept as `InsightDetail` so the existing journey tests and clients continue to work; new metadata is exposed through the grouped read |

## 9. Out of scope for this change

* AI-assisted evidence suggestion. The repository has **no** provider abstraction
  and **no** Groq/Gemini client, so adding one would introduce a paid external
  dependency that the task explicitly forbids without justification. The
  deterministic manual workflow is complete without it, and the API shape is
  ready for a suggestion layer that only proposes.
* Real authentication provider (SSO). Unchanged; the existing session model is
  enforced server-side.
* Deleting or rewriting existing research history. No existing row is modified by
  the migration beyond additive columns.
