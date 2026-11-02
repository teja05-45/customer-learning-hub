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
| `evidence` | code (unique), interview_id, project_id, participant_id, evidence_type, content, interpretation, customer_context, segment, provenance, provenance_status, confidence, review_status, captured_at | The core record |
| `insights` | code (unique), title, summary, interpretation, research_question, project_id, status, confidence, owner_id, limitations, segments (JSON), validated_at | `validated_internal` is a review state |
| `insight_evidence` | insight_id, evidence_id, role, note | `uq_insight_evidence` |
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
  loss of support is visible.
- Deleting an interview cascades its guide, consent records and evidence; the participant and
  project remain.
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

The initial revision is `alembic/versions/fb86ec9b6cc0_initial_schema.py`. Startup table
creation is a convenience for the demo; a production deployment should run migrations before
accepting traffic.

## Seeding

`app/seed/demo_data.py` creates the synthetic Everyday Goods dataset: users, projects with
questions, participants across four segments, recruitment history, interviews with guides and
consent, evidence with and without provenance, insights with supporting and contradictory
links, decisions, actions and activity entries. Seeding is idempotent: it is skipped when users
exist, and `POST /demo/reset` rebuilds it inside one transaction.

**All rows are synthetic.** No real customer data is present, and no contact details exist in
the schema.

See `05-data-model.md` and `10-data-dictionary.md` for the field-level rationale.
