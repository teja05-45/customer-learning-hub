# Database

SQLite by default (`backend/data/clh.db`, or `/app/data/clh.db` in Docker). The schema is
PostgreSQL-compatible: portable column types, string enums, explicit foreign keys and indexes.
Schema creation uses `Base.metadata.create_all` at startup; Alembic is available for managed
migrations.

## Entity relationships

```
User 1───* ResearchProject 1───* ResearchQuestion
              │
              ├──* RecruitmentRecord *───1 Participant
              │        └──* RecruitmentEvent
              ├──* Interview 1───* InterviewGuideQuestion
              │        ├──* ConsentRecord
              │        └──* Evidence
              ├──* FeedbackRecord *───1 Participant (optional)
              │        └── optional link to Interview
              ├──* Insight 1──* InsightEvidence *──1 Evidence
              └──* Decision 1──* DecisionInsight *──1 Insight
                       │        └──* DecisionEvidence *──1 Evidence
                       └──* BusinessAction

ActivityLog ──soft reference by entity_type/entity_id──▶ any entity
OrganizationSetting (single row, id = "default")
```

## Tables

| Table | Important columns | Notes |
| --- | --- | --- |
| `users` | name, email (unique), role, job_title, initials, is_active | Demonstration identities; no password or token |
| `research_projects` | name, objective, status, priority, owner_id, business_functions (JSON), target_segments (JSON), start_date, deadline, archived_at | `ix_projects_status_deadline` |
| `research_questions` | project_id, text, order_index, is_resolved, resolution_note | Cascade with project |
| `participants` | code (unique), display_name, segment, purchase_frequency, orders_count, last_purchase_at, product_category, eligibility, contact_route, contact_consent, is_synthetic | **No contact values** are stored |
| `recruitment_records` | project_id, participant_id, stage, next_action, invited_at, responded_at, scheduled_at | One record per participant per project |
| `recruitment_events` | recruitment_id, from_stage, to_stage, note, actor_id, created_at | Append-only history |
| `interviews` | code (unique), project_id, participant_id, recruitment_id, status, scheduled_at, consent_status, recording_enabled, notes, summary, follow_up_questions (JSON) | `ix_interviews_project_status` |
| `interview_guide_questions` | interview_id, text, purpose, order_index, is_leading | Cascade with interview |
| `consent_records` | interview_id, participant_id, consent_type, status, recorded_by_id, recorded_at, note | Auditable per consent type |
| `evidence` | code (unique), interview_id, feedback_record_id, project_id, participant_id, evidence_type, content, interpretation, customer_context, segment, provenance, provenance_status, confidence, review_status, captured_at, source_type, collection_method, research_depth, source_reference, verification_state, collected_at | The core record. Provenance snapshot columns are filled when evidence is derived from a feedback source; interview evidence derives the same values from the live interview |
| `feedback_records` | code (unique), project_id, participant_id (nullable), interview_id (nullable), source_type, collection_method, source_reference, collected_at, contributor, content, interpretation, context, verification_status, created_by_id | Unified collection source; unattributed records allowed. `ix_feedback_project_source` |
| `insights` | code (unique), title, summary, interpretation, research_question, project_id, status, confidence, owner_id, limitations, segments (JSON), validated_at | `validated_internal` is a review state |
| `insight_evidence` | insight_id, evidence_id, role, note, rationale, confidence, tags (JSON), created_by_id, created_at, updated_at | `uq_insight_evidence`; `ix_insight_evidence_insight_role`. The classification belongs to the relationship, not the evidence |
| `decisions` | code (unique), title, business_function, problem_statement, description, rationale, limitations, project_id, owner_id, decision_date, status, evidence_sufficient | Nullable sufficiency = not assessed |
| `decision_insights` | decision_id, insight_id | `uq_decision_insight` |
| `decision_evidence` | decision_id, evidence_id, role, note | `uq_decision_evidence` |
| `actions` | code (unique), title, description, owner_id, due_date, priority, status, decision_id, insight_id, completed_at | Overdue is computed, never stored |
| `activity_logs` | entity_type, entity_id, entity_label, verb, summary, actor_id, project_id, created_at | Audit trail for timelines |
| `organization_settings` | id, name, research_lead_id, recording_default, retention_months, show_demo_banner | Single row |

## Constraints and referential integrity

- SQLite foreign keys are enabled for every connection (`PRAGMA foreign_keys=ON`).
- Deleting a project cascades to questions, recruitment records, interviews and evidence.
- Deleting a user sets ownership/actor columns to `NULL` (`ondelete="SET NULL"`).
- Deleting an insight or evidence cascades its link rows; the other side is preserved so the
  loss of support is visible. Unlinking through the API removes only the relationship and writes
  an audit entry first.
- `evidence.feedback_record_id` is `ON DELETE SET NULL`: removing a feedback source leaves the
  derived evidence and the customer statement in place, with its provenance snapshot intact.
- Deleting an interview cascades its guide, consent records and evidence; feedback records keep
  their statement but their interview link is set to `NULL`. The participant and project remain.
- Deleting a feedback source removes its statement and links; the project, participant and
  interview survive. Deletion is written to `activity_logs` before the row is removed.
- Unique constraints prevent duplicate evidence links on both insights and decisions.

## Indexes

Status, deadline, project, participant, stage and capture-date columns are indexed where lists
and metrics filter on them. Composite indexes cover the two hottest list filters:
`(status, deadline)` for projects and `(project_id, status)` for interviews.

## Migrations

```bash
cd backend
.venv/Scripts/python.exe -m alembic upgrade head     # apply
.venv/Scripts/python.exe -m alembic revision --autogenerate -m "describe change"
```

The initial revision is `alembic/versions/fb86ec9b6cc0_initial_schema.py`; the feedback table is
added by `e5f6a7b8c9d0_feedback_sources.py`; evidence provenance and relationship metadata are
added by `b7d2f4a91c03_evidence_insight_traceability.py`. Startup table
creation is a convenience for the demo; a production deployment should run migrations before
accepting traffic.

### Two hazards this schema has to survive

1. **Rebuilding `evidence` cascades.** Adding a foreign key on SQLite forces a table rebuild. With
   `PRAGMA foreign_keys=ON`, SQLite's implicit delete during `DROP TABLE` cascades into
   `insight_evidence` and `decision_evidence`. Revision `b7d2f4a91c03` copies both child tables to
   temporary backups and restores them afterwards, in both directions; the migration test proves
   the rows and their statements survive upgrade → downgrade → upgrade.
2. **`create_all` cannot add columns.** A Docker volume created by an earlier build keeps its old
   shape. `ensure_sqlite_columns()` in `app/core/database.py` adds the columns the current code
   needs (nullable, plus a backfill of `updated_at` from `created_at`) without touching existing
   rows. It does not add foreign keys — SQLite cannot do that with `ALTER TABLE` — so the managed
   Alembic path remains the complete migration. `tests/test_schema_upgrade.py` covers the guard.

## Seeding

`app/seed/demo_data.py` creates the synthetic Everyday Goods dataset: users, projects with
questions, participants across four segments, recruitment history, interviews with guides and
consent, evidence with and without provenance, feedback sources spanning interviews, surveys,
support, reviews and imports, insights with supporting and contradictory links, decisions,
actions and activity entries. Seeding is idempotent: it is skipped when users
exist, and `POST /demo/reset` rebuilds it inside one transaction. `SEED_ON_STARTUP=true` with
`SEED_DEMO_DATA=true` seeds on application startup; without that hook a fresh Docker volume came
up empty and demonstration entry had no user to sign in as.

**All rows are synthetic.** No real customer data is present, and no contact details exist in
the schema.

See `05-data-model.md` and `10-data-dictionary.md` for the field-level rationale.
