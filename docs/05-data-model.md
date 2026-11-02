# Data model

17 tables, all with string UUID primary keys and timezone-aware timestamps. Enums are stored
as strings so adding a value never requires a destructive migration and the same schema works
on SQLite and PostgreSQL.

## Shape of the model

```
users ─┬─< research_projects ─┬─< research_questions
       │                      ├─< recruitment_records >─ participants
       │                      ├─< interviews >── participants
       │                      │      ├─< interview_guide_questions
       │                      │      ├─< consent_records
       │                      │      └─< evidence >── participants
       │                      ├─< insights ──< insight_evidence >── evidence
       │                      └─< decisions ──< decision_evidence >── evidence
       │                             │      └─< decision_insights >── insights
       │                             └─< actions
       └─< activity_logs (polymorphic: entity_type + entity_id)
```

## Core principle: three layers, never merged

| Layer | Table | Holds |
| --- | --- | --- |
| What was said | `evidence.content` | The customer's words, or a neutral observation |
| What we read into it | `evidence.interpretation`, `insights.summary` | The researcher's interpretation, in its own field |
| What we decided | `decisions.*` | The business call, with links to the layers above |

The prototype enforces this in the schema, not by convention: there is no field that holds
"quote — and what it means" as one string.

## Tables

### Identity and settings

**`users`** — name, email, role (`ceo`, `researcher`, `business_owner`, `cx`, `admin`),
job_title, initials, is_active. Seven seeded people; no password, no session token.

**`organization_settings`** — single row, id `default`: name, research_lead_id,
recording_default, retention_months, show_demo_banner. Exposed through `/settings` so the
prototype can show where policy would live.

### Research planning

**`research_projects`** — name, objective, description, status, priority, methodology,
owner_id, business_functions (JSON array), target_segments (JSON array), start_date, deadline,
archived_at, completed_at.

Status lifecycle: `draft → planning → recruiting → in_progress → analysis → completed`, plus
`archived`. Archiving is non-destructive: every child record stays addressable.

**`research_questions`** — project_id, text, order_index, is_resolved, resolution_note. A
question can close as "answered", or close as "we chose not to answer this" — the resolution
note makes the difference visible.

### People and recruitment

**`participants`** — code (`PART-000x`), display_name, segment, purchase_frequency,
orders_count, last_purchase_at, product_category, eligibility, eligibility_note, contact_route,
contact_consent, notes, is_synthetic, last_research_contact_at.

Deliberately **no email, phone or address**. `contact_route` is a made-up channel label
(`support ticket`, `marketplace message`) and `contact_consent` is a boolean, so the
recruitment workflow can be described without storing anything that identifies a person.

**`recruitment_records`** — project_id, participant_id, stage, next_action, notes, invited_at,
responded_at, scheduled_at, updated_by_id. Unique per (project, participant).

Stages: `identified`, `selected`, `invited`, `responded`, `scheduled`, `completed`,
`declined`, `no_response`, `cancelled`, `withdrawn`. Allowed transitions live in
`RECRUITMENT_TRANSITIONS` and are enforced in the endpoint, not only in the UI.

**`recruitment_events`** — recruitment_id, from_stage, to_stage, note, actor_id, created_at.
The append-only history behind each pipeline card.

### Conversations

**`interviews`** — code (`INT-000x`), project_id, participant_id, recruitment_id, title,
objective, scheduled_at, duration_minutes, interviewer_id, status, channel, consent_status,
recording_enabled, notes, summary, follow_up_questions (JSON), completed_at.

**`interview_guide_questions`** — interview_id, text, purpose, order_index, is_leading. The
purpose field exists so a researcher can see *why* a question is asked, and `is_leading`
records a question's bias risk rather than hiding it.

**`consent_records`** — interview_id, participant_id, consent_type (`participation`,
`recording`, `quoting`, `sharing_internal`), status (`pending`, `granted`, `declined`,
`withdrawn`), recorded_by_id, recorded_at, note.

**`evidence`** — code (`EV-000x`), interview_id, project_id, participant_id, evidence_type,
content, interpretation, customer_context, segment, provenance, provenance_status, confidence,
review_status, captured_by_id, captured_at.

Five evidence types: `verbatim_quote`, `observation`, `researcher_interpretation`,
`contradictory_evidence`, `open_question`. Typing evidence is the cheapest possible defence
against a summary being read as a quote.

### Synthesis

**`insights`** — code (`INS-000x`), title, summary, interpretation, research_question,
project_id, status, confidence, owner_id, limitations, segments (JSON), validated_at,
validated_by_id.

Statuses: `draft`, `under_review`, `validated_internal`, `needs_more_research`, `archived`.
`validated_internal` is deliberately not "validated" — the prototype never claims external
validation.

**`insight_evidence`** — insight_id, evidence_id, role (`supporting` | `contradictory`), note,
created_at.

Contradictory evidence is a link role, not a separate table, so an insight can carry the
counter-example that nearly killed it. That is the difference between a synthesis tool and a
highlight reel.

### Decisions and delivery

**`decisions`** — code (`DEC-000x`), title, business_function, problem_statement, description,
rationale, limitations, project_id, owner_id, decision_date, status, evidence_sufficient.

Statuses: `proposed`, `under_review`, `accepted`, `rejected`, `deferred`.
`evidence_sufficient` is nullable on purpose: null means "not assessed", false means "this was
internal judgement", true means "customer research supports it".

**`decision_evidence`** and **`decision_insights`** — join tables with role and note, so a
decision can lean on an insight and the evidence under it separately.

**`actions`** — code (`ACT-000x`), title, description, owner_id, due_date, priority, status,
decision_id, insight_id, completed_at. Statuses: `not_started`, `in_progress`, `completed`,
`blocked`.

### Audit

**`activity_logs`** — entity_type, entity_id, entity_label, verb, summary, actor_id,
project_id, created_at. A polymorphic trail rather than a per-table audit table: it powers the
"Recent research activity" panel and the per-record history without seventeen extra tables.

## Integrity rules

| Rule | Enforced in |
| --- | --- |
| Deleting a project is not exposed; archive only | API surface |
| Deleting an evidence row removes its insight links | Foreign keys with cascade + explicit cleanup |
| Unlinking the last decision source resets `evidence_sufficient` | Decision endpoint |
| Evidence cannot reference an interview and a different project | Create/update validation |
| Recruitment stage jumps are rejected | `RECRUITMENT_TRANSITIONS` |
| Consent status is derived from consent records | Consent endpoint |
| Every mutation writes an activity row | `log_activity()` helper used by every mutating endpoint |

## Portability

- SQLite by default (`backend/data/clh.db`), PostgreSQL by changing `DATABASE_URL` to
  `postgresql+psycopg://…` and installing `psycopg`.
- JSON columns for arrays that are read whole: `business_functions`, `target_segments`,
  `segments`, `follow_up_questions`.
- Alembic migration `0001_initial` creates the full schema; `Base.metadata.create_all` is used
  only for tests and first-run convenience.
