# Data Dictionary

Generated from the SQLAlchemy metadata in `backend/app/models/` at this revision, so it
cannot drift from the schema that `alembic upgrade head` builds. Types are shown as
declared; SQLite stores them with its usual affinity.

## `participants`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `code` | `VARCHAR(16)` | no | unique, indexed |
| `display_name` | `VARCHAR(120)` | no | — |
| `segment` | `VARCHAR(32)` | no | indexed |
| `purchase_frequency` | `VARCHAR(64)` | no | — |
| `orders_count` | `INTEGER` | no | default `1` |
| `last_purchase_at` | `DATE` | yes | — |
| `product_category` | `VARCHAR(64)` | no | — |
| `eligibility` | `VARCHAR(24)` | no | indexed, default `eligible` |
| `eligibility_note` | `VARCHAR(240)` | no | — |
| `contact_route` | `VARCHAR(160)` | yes | — |
| `contact_consent` | `VARCHAR(24)` | no | default `pending` |
| `notes` | `TEXT` | no | — |
| `is_synthetic` | `BOOLEAN` | no | default `True` |
| `last_research_contact_at` | `DATETIME` | yes | — |
| `id` | `VARCHAR(36)` | no | primary key |
| `created_at` | `DATETIME` | no | — |
| `updated_at` | `DATETIME` | no | — |


## `users`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `name` | `VARCHAR(120)` | no | — |
| `email` | `VARCHAR(160)` | no | unique |
| `role` | `VARCHAR(32)` | no | indexed |
| `job_title` | `VARCHAR(120)` | no | — |
| `initials` | `VARCHAR(4)` | no | — |
| `is_active` | `BOOLEAN` | no | default `True` |
| `password_hash` | `VARCHAR(255)` | yes | — |
| `id` | `VARCHAR(36)` | no | primary key |
| `created_at` | `DATETIME` | no | — |
| `updated_at` | `DATETIME` | no | — |


## `activity_logs`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `entity_type` | `VARCHAR(32)` | no | indexed |
| `entity_id` | `VARCHAR(36)` | yes | indexed |
| `entity_label` | `VARCHAR(200)` | no | — |
| `verb` | `VARCHAR(32)` | no | — |
| `summary` | `VARCHAR(320)` | no | — |
| `actor_id` | `VARCHAR(36)` | yes | FK → users.id |
| `project_id` | `VARCHAR(36)` | yes | indexed |
| `created_at` | `DATETIME` | no | indexed |
| `id` | `VARCHAR(36)` | no | primary key |


## `auth_sessions`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `id` | `VARCHAR(36)` | no | primary key |
| `user_id` | `VARCHAR(36)` | no | FK → users.id, indexed |
| `token_hash` | `VARCHAR(64)` | no | unique, indexed |
| `created_at` | `DATETIME` | no | — |
| `last_seen_at` | `DATETIME` | no | — |
| `expires_at` | `DATETIME` | no | indexed |
| `user_agent` | `VARCHAR(200)` | no | — |


## `organization_settings`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `id` | `VARCHAR(36)` | no | primary key, default `default` |
| `name` | `VARCHAR(160)` | no | default `Everyday Goods` |
| `research_lead_id` | `VARCHAR(36)` | yes | FK → users.id |
| `recording_default` | `BOOLEAN` | no | default `False` |
| `retention_months` | `INTEGER` | no | default `12` |
| `show_demo_banner` | `BOOLEAN` | no | default `True` |
| `updated_at` | `DATETIME` | no | — |


## `research_projects`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `name` | `VARCHAR(200)` | no | — |
| `objective` | `TEXT` | no | — |
| `description` | `TEXT` | no | — |
| `status` | `VARCHAR(24)` | no | indexed, default `draft` |
| `priority` | `VARCHAR(16)` | no | indexed, default `medium` |
| `methodology` | `VARCHAR(80)` | no | — |
| `owner_id` | `VARCHAR(36)` | yes | FK → users.id |
| `business_functions` | `JSON` | no | — |
| `target_segments` | `JSON` | no | — |
| `start_date` | `DATE` | yes | — |
| `deadline` | `DATE` | yes | indexed |
| `archived_at` | `DATETIME` | yes | — |
| `completed_at` | `DATETIME` | yes | — |
| `id` | `VARCHAR(36)` | no | primary key |
| `created_at` | `DATETIME` | no | — |
| `updated_at` | `DATETIME` | no | — |


## `decisions`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `code` | `VARCHAR(16)` | no | unique, indexed |
| `title` | `VARCHAR(240)` | no | — |
| `business_function` | `VARCHAR(40)` | no | indexed |
| `problem_statement` | `TEXT` | no | — |
| `description` | `TEXT` | no | — |
| `rationale` | `TEXT` | no | — |
| `limitations` | `TEXT` | no | — |
| `project_id` | `VARCHAR(36)` | yes | FK → research_projects.id, indexed |
| `owner_id` | `VARCHAR(36)` | yes | FK → users.id |
| `decision_date` | `DATE` | yes | — |
| `status` | `VARCHAR(24)` | no | indexed, default `proposed` |
| `evidence_sufficient` | `BOOLEAN` | yes | — |
| `id` | `VARCHAR(36)` | no | primary key |
| `created_at` | `DATETIME` | no | — |
| `updated_at` | `DATETIME` | no | — |


## `insights`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `code` | `VARCHAR(16)` | no | unique, indexed |
| `title` | `VARCHAR(240)` | no | — |
| `summary` | `TEXT` | no | — |
| `interpretation` | `TEXT` | no | — |
| `research_question` | `VARCHAR(400)` | no | — |
| `project_id` | `VARCHAR(36)` | yes | FK → research_projects.id, indexed |
| `status` | `VARCHAR(32)` | no | indexed, default `draft` |
| `confidence` | `VARCHAR(16)` | no | default `low` |
| `owner_id` | `VARCHAR(36)` | yes | FK → users.id |
| `limitations` | `TEXT` | no | — |
| `segments` | `JSON` | no | — |
| `validated_at` | `DATETIME` | yes | — |
| `validated_by_id` | `VARCHAR(36)` | yes | FK → users.id |
| `id` | `VARCHAR(36)` | no | primary key |
| `created_at` | `DATETIME` | no | — |
| `updated_at` | `DATETIME` | no | — |


## `recruitment_records`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `project_id` | `VARCHAR(36)` | no | FK → research_projects.id, indexed |
| `participant_id` | `VARCHAR(36)` | no | FK → participants.id, indexed |
| `stage` | `VARCHAR(24)` | no | indexed, default `identified` |
| `next_action` | `VARCHAR(240)` | no | — |
| `notes` | `TEXT` | no | — |
| `invited_at` | `DATETIME` | yes | — |
| `responded_at` | `DATETIME` | yes | — |
| `scheduled_at` | `DATETIME` | yes | — |
| `updated_by_id` | `VARCHAR(36)` | yes | FK → users.id |
| `id` | `VARCHAR(36)` | no | primary key |
| `created_at` | `DATETIME` | no | — |
| `updated_at` | `DATETIME` | no | — |


## `research_questions`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `project_id` | `VARCHAR(36)` | no | FK → research_projects.id, indexed |
| `text` | `VARCHAR(400)` | no | — |
| `order_index` | `INTEGER` | no | default `0` |
| `is_resolved` | `BOOLEAN` | no | default `False` |
| `resolution_note` | `VARCHAR(400)` | no | — |
| `created_at` | `DATETIME` | no | — |
| `id` | `VARCHAR(36)` | no | primary key |


## `actions`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `code` | `VARCHAR(16)` | no | unique, indexed |
| `title` | `VARCHAR(240)` | no | — |
| `description` | `TEXT` | no | — |
| `owner_id` | `VARCHAR(36)` | yes | FK → users.id |
| `due_date` | `DATE` | yes | indexed |
| `priority` | `VARCHAR(16)` | no | indexed, default `medium` |
| `status` | `VARCHAR(24)` | no | indexed, default `not_started` |
| `decision_id` | `VARCHAR(36)` | yes | FK → decisions.id, indexed |
| `insight_id` | `VARCHAR(36)` | yes | FK → insights.id, indexed |
| `completed_at` | `DATETIME` | yes | — |
| `id` | `VARCHAR(36)` | no | primary key |
| `created_at` | `DATETIME` | no | — |
| `updated_at` | `DATETIME` | no | — |


## `decision_insights`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `decision_id` | `VARCHAR(36)` | no | FK → decisions.id, indexed |
| `insight_id` | `VARCHAR(36)` | no | FK → insights.id, indexed |
| `created_at` | `DATETIME` | no | — |
| `id` | `VARCHAR(36)` | no | primary key |

- Constraint `uq_decision_insight` (UniqueConstraint)

## `interviews`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `code` | `VARCHAR(16)` | no | unique, indexed |
| `project_id` | `VARCHAR(36)` | no | FK → research_projects.id, indexed |
| `participant_id` | `VARCHAR(36)` | no | FK → participants.id, indexed |
| `recruitment_id` | `VARCHAR(36)` | yes | FK → recruitment_records.id |
| `title` | `VARCHAR(200)` | no | — |
| `objective` | `TEXT` | no | — |
| `scheduled_at` | `DATETIME` | yes | indexed |
| `duration_minutes` | `INTEGER` | no | default `30` |
| `interviewer_id` | `VARCHAR(36)` | yes | FK → users.id |
| `status` | `VARCHAR(24)` | no | indexed, default `planned` |
| `channel` | `VARCHAR(80)` | no | default `Video call (simulated)` |
| `consent_status` | `VARCHAR(24)` | no | default `pending` |
| `recording_enabled` | `BOOLEAN` | no | default `False` |
| `notes` | `TEXT` | no | — |
| `summary` | `TEXT` | no | — |
| `follow_up_questions` | `JSON` | no | — |
| `completed_at` | `DATETIME` | yes | — |
| `id` | `VARCHAR(36)` | no | primary key |
| `created_at` | `DATETIME` | no | — |
| `updated_at` | `DATETIME` | no | — |


## `recruitment_events`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `recruitment_id` | `VARCHAR(36)` | no | FK → recruitment_records.id, indexed |
| `from_stage` | `VARCHAR(24)` | yes | — |
| `to_stage` | `VARCHAR(24)` | no | — |
| `note` | `VARCHAR(240)` | no | — |
| `actor_id` | `VARCHAR(36)` | yes | FK → users.id |
| `created_at` | `DATETIME` | no | — |
| `id` | `VARCHAR(36)` | no | primary key |


## `consent_records`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `interview_id` | `VARCHAR(36)` | yes | FK → interviews.id, indexed |
| `participant_id` | `VARCHAR(36)` | no | FK → participants.id, indexed |
| `consent_type` | `VARCHAR(32)` | no | — |
| `status` | `VARCHAR(24)` | no | default `pending` |
| `recorded_by_id` | `VARCHAR(36)` | yes | FK → users.id |
| `recorded_at` | `DATETIME` | no | — |
| `note` | `VARCHAR(320)` | no | — |
| `id` | `VARCHAR(36)` | no | primary key |


## `evidence`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `code` | `VARCHAR(16)` | no | unique, indexed |
| `interview_id` | `VARCHAR(36)` | yes | FK → interviews.id, indexed |
| `project_id` | `VARCHAR(36)` | no | FK → research_projects.id, indexed |
| `participant_id` | `VARCHAR(36)` | yes | FK → participants.id, indexed |
| `evidence_type` | `VARCHAR(32)` | no | indexed |
| `content` | `TEXT` | no | — |
| `interpretation` | `TEXT` | no | — |
| `customer_context` | `TEXT` | no | — |
| `segment` | `VARCHAR(32)` | no | indexed, default `unknown` |
| `provenance` | `VARCHAR(320)` | no | — |
| `provenance_status` | `VARCHAR(16)` | no | default `recorded` |
| `confidence` | `VARCHAR(16)` | no | default `medium` |
| `review_status` | `VARCHAR(16)` | no | default `unreviewed` |
| `captured_by_id` | `VARCHAR(36)` | yes | FK → users.id |
| `captured_at` | `DATETIME` | no | — |
| `id` | `VARCHAR(36)` | no | primary key |


## `interview_guide_questions`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `interview_id` | `VARCHAR(36)` | no | FK → interviews.id, indexed |
| `text` | `VARCHAR(400)` | no | — |
| `purpose` | `VARCHAR(240)` | no | — |
| `order_index` | `INTEGER` | no | default `0` |
| `is_leading` | `BOOLEAN` | no | default `False` |
| `id` | `VARCHAR(36)` | no | primary key |


## `decision_evidence`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `decision_id` | `VARCHAR(36)` | no | FK → decisions.id, indexed |
| `evidence_id` | `VARCHAR(36)` | no | FK → evidence.id, indexed |
| `role` | `VARCHAR(16)` | no | default `supporting` |
| `note` | `VARCHAR(240)` | no | — |
| `created_at` | `DATETIME` | no | — |
| `id` | `VARCHAR(36)` | no | primary key |

- Constraint `uq_decision_evidence` (UniqueConstraint)

## `insight_evidence`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `insight_id` | `VARCHAR(36)` | no | FK → insights.id, indexed |
| `evidence_id` | `VARCHAR(36)` | no | FK → evidence.id, indexed |
| `role` | `VARCHAR(16)` | no | default `supporting` |
| `note` | `VARCHAR(240)` | no | — |
| `created_at` | `DATETIME` | no | — |
| `id` | `VARCHAR(36)` | no | primary key |

- Constraint `uq_insight_evidence` (UniqueConstraint)

## `feedback_records`

| Column | Type | Nullable | Key / constraint |
| --- | --- | --- | --- |
| `code` | `VARCHAR(16)` | no | unique, indexed |
| `project_id` | `VARCHAR(36)` | no | FK → research_projects.id, indexed |
| `participant_id` | `VARCHAR(36)` | yes | FK → participants.id, indexed |
| `interview_id` | `VARCHAR(36)` | yes | FK → interviews.id, indexed |
| `source_type` | `VARCHAR(32)` | no | indexed |
| `collection_method` | `VARCHAR(32)` | no | — |
| `source_reference` | `VARCHAR(320)` | no | — |
| `collected_at` | `DATETIME` | no | indexed |
| `contributor` | `VARCHAR(160)` | no | — |
| `content` | `TEXT` | no | original customer words |
| `interpretation` | `TEXT` | no | researcher reading, stored separately |
| `context` | `TEXT` | no | — |
| `verification_status` | `VARCHAR(24)` | no | indexed, default `unverified` |
| `created_by_id` | `VARCHAR(36)` | yes | FK → users.id |
| `id` | `VARCHAR(36)` | no | primary key |
| `created_at` | `DATETIME` | no | — |
| `updated_at` | `DATETIME` | no | — |

- Composite index `ix_feedback_project_source` (`project_id`, `source_type`).
