# Evidence Traceability

Every insight must be traceable to the customer feedback behind it, and a
reviewer must be able to walk from a business action back to the words a customer
actually used. This document describes how the product guarantees that.

```
Feedback source → Evidence → Insight → Decision → Action
                       ↕
              relationship classification
```

## 1. Data model

The association is an explicit table, not a JSON column, because each link
carries its own assessment and its own author.

### `evidence`

An evidence row holds the customer's statement and its provenance.

| Column | Purpose |
| --- | --- |
| `content` | The original customer words. Never rewritten by any other operation. |
| `interpretation` | The researcher's reading, stored separately. |
| `interview_id` | Set for interview evidence (nullable). |
| `feedback_record_id` | Set when the item was derived from a feedback source. |
| `source_type` | Snapshot: `interview`, `short_survey`, `customer_support`, … |
| `collection_method` | Snapshot: `video_interview`, `short_survey`, … |
| `research_depth` | Snapshot: `deep`, `medium`, `limited` or `context`. |
| `source_reference` | Snapshot: ticket id, survey wave, transcript timestamp. |
| `verification_state` | Snapshot: `verified`, `needs_review`, `unverified`. |
| `collected_at` | When the source was collected. |
| `provenance`, `provenance_status` | The existing free-text source note and whether one exists. |

Interview evidence derives the same values from the live interview row: the
interview's channel maps to a collection method where the channel is recognisable,
and an unrecognised channel is reported as "not recorded" rather than guessed.
Feedback-derived evidence uses the snapshot written at derivation time, so
correcting the source record later cannot silently change how the customer's
words are presented.

### `insight_evidence`

| Column | Purpose |
| --- | --- |
| `insight_id`, `evidence_id` | Foreign keys, `ON DELETE CASCADE`. |
| `role` | `supporting`, `contradictory` or `contextual`. |
| `rationale` | Why the researcher chose that classification. |
| `confidence` | Optional researcher judgement: `low`, `medium`, `high`. |
| `tags` | Optional short labels (JSON array, max 8). |
| `note` | Legacy 240-character note, preserved and shown when `rationale` is empty. |
| `created_by_id` | The researcher who made the judgement. |
| `created_at`, `updated_at` | When the link was made and last changed. |
| unique | `(insight_id, evidence_id)` — one relationship per pair. |
| index | `(insight_id, role)` for grouped reads. |

An evidence item may serve several insights. Because the pair is unique, the
evidence id is also a valid natural key for a relationship inside one insight;
the PATCH and DELETE endpoints accept either the relationship id or the evidence
id and document the fallback.

### Project consistency

Linking is refused when the insight has a project and the evidence belongs to a
different one. An insight with **no** project may draw on any project's evidence;
that is the explicit cross-project workflow, and it is the only way to combine
evidence across studies. Every other mismatch returns
`400 rule_violation` with `details.evidence_project_id`.

## 2. Relationship lifecycle

```
capture feedback
      │  POST /feedback/{id}/evidence   (copies the statement verbatim)
      ▼
   evidence ──link──▶ insight    POST /insights/{id}/evidence
      │                            role + rationale + optional confidence/tags
      │
      ├── re-classify             PATCH /insights/{id}/evidence/{relationship}
      │                            role/rationale/confidence/tags only
      │
      └── remove                  DELETE /insights/{id}/evidence/{relationship}
                                   audited; evidence and statement are kept
```

Duplicate creation returns `409` with the existing relationship id and
classification, so the UI can send the researcher to the edit dialog instead of
silently creating a second link.

Deletion is never cascaded by the product surface: removing a relationship
removes only the relationship. The evidence row, the feedback record and the
customer statement survive, and the removal is written to `activity_logs`
before the row is deleted.

## 3. Supporting versus contradictory versus contextual

* **Supporting** — the researcher judges that this item is evidence *for* the
  finding.
* **Contradictory** — the item pushes against the finding. It is kept visible on
  every screen that shows the insight, and it is escalated into the decision's
  traceability view.
* **Contextual** — the item explains the setting (where, when, under what
  constraint) without confirming or denying the finding. Recording context as
  supporting would inflate the evidence base; discarding it would lose the
  setting.

Classification is never inferred. Nothing is supporting by default: `role` is a
required field on the create payload, and the UI requires a rationale before the
link can be saved.

## 4. Evidence provenance preservation

Guarantees, each covered by a test:

1. Deriving evidence from feedback copies `content` exactly as stored.
2. Classifying, re-classifying or removing a link never writes to `evidence` or
   `feedback_records`.
3. Editing the feedback interpretation later does not change the evidence
   snapshot already derived from it.
4. Unverified or unattributed sources are labelled as such everywhere, including
   the traceability export (`attribution = unattributed`, verification state
   carried through).
5. Deleting evidence is a separate, confirmed, audited action; it is not a side
   effect of unlinking.

## 5. Validation rules (server-side)

| Rule | Failure |
| --- | --- |
| Insight exists | `404 not_found` |
| Evidence exists | `404` |
| Relationship exists on that insight | `404` |
| Same project (unless insight has none) | `400 rule_violation` |
| Classification is one of the three values | `422 validation_error` |
| Duplicate pair | `409 conflict` with existing relationship |
| Evidence has a non-empty statement | `400 rule_violation` |
| Writer holds `researcher` or `admin` | `403 forbidden` (middleware) |
| Anonymous request | `401 unauthorized` (middleware) |
| At least one field on PATCH | `400 rule_violation` |
| Insight validation requires evidence | `400 rule_violation` (pre-existing rule) |

Frontend validation mirrors these rules for usability; it is not the security
boundary.

## 6. API usage

```http
POST /api/v1/feedback/{feedback_id}/evidence
```
Creates evidence from any feedback source (survey, support, review, manual entry,
import). Response `201 EvidenceOut` with the provenance snapshot.

```http
GET /api/v1/feedback/{feedback_id}/evidence
```
Lists evidence derived from that source.

```http
POST /api/v1/insights/{insight_id}/evidence
{"evidence_id": "...", "role": "supporting",
 "rationale": "Repeats across three segments.",
 "confidence": "medium", "tags": ["packaging"]}
```
Returns `201 InsightDetail` for compatibility with the original client. The
grouped relationship view is available from the read endpoints below.

```http
GET /api/v1/insights/{insight_id}/evidence
```
`{supporting: {items, count}, contradictory: {...}, contextual: {...}, total}`.
Each item carries `relationship_id`, classification, rationale, confidence,
tags, author, timestamps and the full evidence object.

```http
PATCH /api/v1/insights/{insight_id}/evidence/{relationship_id}
{"role": "contradictory", "rationale": "On review this is a counter-example."}
```
Returns `{relationship, message}`. Evidence is untouched.

```http
DELETE /api/v1/insights/{insight_id}/evidence/{relationship_id}
```
Returns `{message, detail}`. Audited.

```http
GET /api/v1/insights/{insight_id}/traceability
```
The complete record: insight summary, grouped evidence, quality counts, decisions
that used it (with their actions), warnings, and the chain note. `quality`
contains `total`, `supporting`, `contradictory`, `contextual`, `verified`,
`unverified`, `distinct_source_types`, `unattributed`, `unsubstantiated`,
`has_conflict` — counts, not a verdict. There is deliberately no "validated"
flag.

```http
GET /api/v1/evidence/{evidence_id}/insights
```
Reverse view, grouped by classification, with the same relationship metadata.

```http
GET /api/v1/decisions/{decision_id}/traceability
```
Decision → insights → evidence, plus direct evidence, actions, contradictions
carried through from linked insights, `gaps` and an ordered `chain` of labels.

## 7. UI workflow

1. Record a feedback source on **Feedback sources** (interview, written, form,
   survey, support, review, manual or CSV import).
2. Press **Create evidence** on that source. The statement is copied unchanged.
3. Open an insight and press **Add evidence**.
4. Search, filter by source type and verification, preview each statement, select
   one or more items.
5. Choose supporting, contradictory or contextual; enter a rationale; optionally
   record confidence and tags.
6. Save. The three groups and the quality indicators update immediately.
7. Edit a relationship to re-classify it, or remove it. Both actions are logged.
8. On the evidence detail page, see every insight the item is used in and why.
9. On the decision page, read the reasoning chain back to the statements.

Quality indicators show quantity separately from quality. An insight with no
evidence is labelled **unsubstantiated**; one with contradictory evidence shows
the conflict; context-only evidence never reads as support.

## 8. Export format

`GET /api/v1/exports/traceability.csv` — one row per relationship.

| Column | Notes |
| --- | --- |
| `project` | Project name, empty for a project-less insight |
| `insight_code`, `insight`, `insight_description` | |
| `evidence_code` | The stable `EV-…` reference |
| `customer_statement` | Copied exactly; escaped by the CSV writer |
| `researcher_interpretation` | Separate column, never merged |
| `source_type`, `collection_method`, `research_depth` | Provenance snapshot or interview derivation |
| `verification_state` | `verified`, `needs_review`, `unverified` |
| `attribution` | Participant code or the literal `unattributed` |
| `relationship_classification` | supporting / contradictory / contextual |
| `researcher_rationale` | |
| `confidence` | Empty when not assessed |
| `created_by`, `created_at` | Author and timestamp |
| `data_origin`, `exported_at` | Existing export convention |

UTF-8 BOM preserved, `Cache-Control: no-store`, `X-Row-Count` header, formula
injection neutralised, no email addresses or internal notes. An empty dataset
returns a header-only file. The download is written to the audit trail.

## 9. Test coverage

| Requirement | Test |
| --- | --- |
| Derive evidence from feedback, verbatim | `test_feedback_derives_verbatim_evidence_with_provenance` |
| Unverified / unattributed labelling | `test_unverified_and_unattributed_feedback_is_labelled` |
| Three classifications and grouped reads | `test_link_evidence_with_three_classifications_and_read_groups` |
| One evidence → several insights | `test_one_evidence_can_serve_several_insights` |
| Re-classify without touching the statement | `test_relationship_can_be_reclassified_without_touching_the_statement` |
| Feedback edits do not rewrite derived evidence | `test_editing_feedback_does_not_rewrite_derived_evidence` |
| Duplicate and invalid relationships | `test_duplicate_and_invalid_relationships_are_refused` |
| Missing records | `test_missing_records_return_clear_errors` |
| Cross-project rejection, explicit cross-project workflow | `test_cross_project_relationship_is_rejected` |
| Audited unlink, records survive, legacy id | `test_unlink_is_audited_and_keeps_the_evidence` |
| Quality counts, unsubstantiated | `test_traceability_reports_quality_without_claiming_validation` |
| Decision → evidence chain | `test_decision_traceability_reaches_the_customer_words` |
| Export provenance and uniqueness | `test_traceability_export_preserves_provenance` |
| Role enforcement | `test_relationship_writes_require_a_research_role` |
| Atomic insight creation | `test_creating_an_insight_with_a_bad_evidence_id_is_atomic` |
| Migration upgrade/downgrade with data | `test_traceability_migration_upgrades_and_downgrades` |

Browser coverage lives in `frontend/e2e/traceability.spec.ts` (five journeys:
survey → evidence → insight; evidence ↔ insight ↔ decision; cross-project and
role refusal; export and audited removal at four widths; context-only insight),
with axe scans of the insight page, evidence page and add-evidence dialog in
`frontend/e2e/a11y.spec.ts`.

## 10. Migration note

Revision `b7d2f4a91c03` adds the columns. On SQLite, adding a foreign key forces
a table rebuild, and with `PRAGMA foreign_keys=ON` the rebuild's implicit delete
cascades into `insight_evidence` and `decision_evidence`. The migration therefore
copies both child tables to temporary backups before the rebuild and restores
them afterwards, in both directions. Without that guard an upgrade would have
silently erased every evidence-to-insight and evidence-to-decision link; the
migration test asserts the rows survive a full upgrade → downgrade → upgrade
cycle.
