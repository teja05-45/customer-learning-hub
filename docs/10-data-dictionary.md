# Data dictionary

Field-level reference for the 17 tables. Types are the SQLAlchemy types as created in the
SQLite schema; JSON columns hold arrays of strings.

Conventions: `id` is a UUID string on every table (`organization_settings` uses the literal id
`default`); `created_at` / `updated_at` are timezone-aware UTC timestamps on mutable tables;
human-facing `code` values are prefixed and monotonic (`INT-0007`).

## `users`

| Field | Type | Notes |
| --- | --- | --- |
| name | string(120) | Display name, e.g. "Priya Menon" |
| email | string(200) | Synthetic address, unique. Never used to send anything |
| role | string(24) | `ceo` \| `researcher` \| `business_owner` \| `cx` \| `admin` |
| job_title | string(120) | e.g. "Customer Research Coordinator" |
| initials | string(4) | For the avatar |
| is_active | bool | Inactive people stay referenced by history |

## `organization_settings`

| Field | Type | Notes |
| --- | --- | --- |
| id | string | Always `default` |
| name | string | Workspace name, "Everyday Goods" |
| research_lead_id | FK users.id, nullable | Who owns research |
| recording_default | bool | Default for new interviews; off |
| retention_months | int | Shown in settings; **not enforced** |
| show_demo_banner | bool | Hides the banner, not the footer note |

## `research_projects`

| Field | Type | Notes |
| --- | --- | --- |
| name | string(200) | Required, min 5 characters |
| objective | text | What the study must answer; required |
| description | text | Scope and method detail |
| status | string(24) | `draft`, `planning`, `recruiting`, `in_progress`, `analysis`, `completed`, `archived` |
| priority | string(16) | `low`, `medium`, `high`, `critical` |
| methodology | string(80) | Free text, e.g. "Semi-structured interviews" |
| owner_id | FK users.id | Research owner |
| business_functions | JSON | Which functions will use the learning |
| target_segments | JSON | Segments the study intends to cover |
| start_date, deadline | date | Deadline drives "due soon" ordering |
| archived_at, completed_at | timestamp | Set by archive / completion |

## `research_questions`

| Field | Type | Notes |
| --- | --- | --- |
| project_id | FK projects.id | Cascade delete with the project |
| text | string(400) | The question, phrased answerably |
| order_index | int | Display order |
| is_resolved | bool | Closed with a resolution note or not |
| resolution_note | string(400) | What was learned, or why it stays open |

## `participants`

| Field | Type | Notes |
| --- | --- | --- |
| code | string(16) | `P-1001`… unique |
| display_name | string(120) | First name plus initial, invented |
| segment | string(32) | `first_time_buyer`, `repeat_buyer`, `lapsed_buyer`, `household_buyer`, `unknown` |
| purchase_frequency | string(40) | Human label, e.g. "once, 4 months ago" |
| orders_count | int | Purchase history depth |
| last_purchase_at | date, nullable | Recency |
| product_category | string(80) | What they bought |
| eligibility | string(24) | `eligible`, `limited`, `ineligible` |
| eligibility_note | string(240) | Why, e.g. "bought once, no repeat" |
| contact_route | string(80) | Channel *label only* — no address stored |
| contact_consent | bool | Whether they agreed to be contacted |
| notes | text | Research-relevant context |
| is_synthetic | bool | Always true in this dataset |
| last_research_contact_at | timestamp | Prevents over-contacting |

There is no email, phone, address or external customer id column anywhere in the schema.

## `recruitment_records`

| Field | Type | Notes |
| --- | --- | --- |
| project_id, participant_id | FK | Unique pair |
| stage | string(24) | Ten stages; transitions enforced |
| next_action | string(200) | What happens next, in words |
| notes | text | Free text |
| invited_at, responded_at, scheduled_at | timestamp | Milestones, set by the stage change |
| updated_by_id | FK users.id | Last person to move it |

`recruitment_events`: recruitment_id, from_stage, to_stage, note, actor_id, created_at — the
append-only history.

## `interviews`

| Field | Type | Notes |
| --- | --- | --- |
| code | string(16) | `INT-0001`… |
| project_id, participant_id | FK | Required |
| recruitment_id | FK, nullable | When created from the pipeline |
| title | string(200) | How the session is remembered |
| objective | text | What this conversation must cover |
| scheduled_at | timestamp | Drives the upcoming list |
| duration_minutes | int | Realistic, defaults 30 |
| interviewer_id | FK users.id | Who runs it |
| status | string(24) | `planned`, `scheduled`, `in_progress`, `completed`, `cancelled` |
| channel | string(80) | "Video call (simulated)" — no link present |
| consent_status | string(24) | Derived from consent records |
| recording_enabled | bool | Cannot be true without granted recording consent |
| notes | text | Typed notes, never audio |
| summary | text | Post-session summary |
| follow_up_questions | JSON | Open threads carried forward |
| completed_at | timestamp | Set on completion |

## `interview_guide_questions`

interview_id, text, purpose, order_index, is_leading. `is_leading` records a bias risk
explicitly instead of hiding it.

## `consent_records`

interview_id, participant_id, consent_type (`participation`, `recording`, `quoting`,
`sharing_internal`), status (`pending`, `granted`, `declined`, `withdrawn`), recorded_by_id,
recorded_at, note.

## `evidence`

| Field | Type | Notes |
| --- | --- | --- |
| code | string(16) | `EV-0001`… |
| interview_id | FK, nullable | Null only for imported notes; then provenance is `partial` or `missing` |
| project_id, participant_id | FK | Denormalised for filtering, validated for consistency |
| evidence_type | string(32) | `verbatim_quote`, `observation`, `researcher_interpretation`, `contradictory_evidence`, `open_question` |
| content | text | **The customer's words** or a factual observation |
| interpretation | text | **The researcher's reading** — a separate field, always |
| customer_context | text | Situation, e.g. "second bottle, sensitive scalp" |
| segment | string(32) | Segment this evidence speaks for |
| provenance | string(240) | Where it came from: interview code, participant code, note number |
| provenance_status | string(16) | `recorded`, `partial`, `missing` |
| confidence | string(16) | `low`, `medium`, `high` |
| review_status | string(16) | `unreviewed`, `reviewed`, `flagged` |
| captured_by_id | FK users.id | Who typed it |
| captured_at | timestamp | When |

## `insights`

| Field | Type | Notes |
| --- | --- | --- |
| code | string(16) | `INS-0001`… |
| title | string(240) | The finding, as a claim |
| summary | text | What we believe and why (min 20 characters) |
| interpretation | text | Further reasoning, kept separate from the summary |
| research_question | string(400) | Which question this answers |
| project_id | FK, nullable | Insight can exist before being filed |
| status | string(24) | `draft`, `under_review`, `validated_internal`, `needs_more_research`, `archived` |
| confidence | string(16) | `low`, `medium`, `high` |
| owner_id | FK users.id | Accountable author |
| limitations | text | What this does **not** say |
| segments | JSON | Segments the finding applies to |
| validated_at, validated_by_id | timestamp, FK | Set when status becomes `validated_internal` |

`insight_evidence`: insight_id, evidence_id, role (`supporting` \| `contradictory`), note.

## `decisions`

| Field | Type | Notes |
| --- | --- | --- |
| code | string(16) | `DEC-001`… |
| title | string(240) | The decision, phrased as a decision |
| business_function | string(32) | `brand_marketing`, `product_category`, `growth`, `customer_experience`, `operations`, `executive` |
| problem_statement | text | What problem this answers |
| description | text | Detail |
| rationale | text | Why this option |
| limitations | text | What it does not settle |
| project_id | FK, nullable | The study that informed it |
| owner_id | FK users.id | Accountable decision owner |
| decision_date | date | When the call was made |
| status | string(24) | `proposed`, `under_review`, `accepted`, `rejected`, `deferred` |
| evidence_sufficient | bool, nullable | `true` supported, `false` internal judgement, `null` not assessed |

`decision_evidence`: decision_id, evidence_id, role, note.
`decision_insights`: decision_id, insight_id, created_at.

## `actions`

| Field | Type | Notes |
| --- | --- | --- |
| code | string(16) | `ACT-001`… |
| title | string(240) | A verb and an object |
| description | text | Enough detail to start |
| owner_id | FK users.id | One named person, never a team |
| due_date | date | Drives overdue calculations |
| priority | string(16) | `low`, `medium`, `high`, `critical` |
| status | string(24) | `not_started`, `in_progress`, `completed`, `blocked` |
| decision_id, insight_id | FK, nullable | Where the work came from |
| completed_at | timestamp | Set on completion, cleared on reopen |

## `activity_logs`

entity_type (`project`, `participant`, `recruitment`, `interview`, `evidence`, `insight`,
`decision`, `action`, `settings`), entity_id, entity_label, verb (`created`, `updated`,
`linked`, `unlinked`, `stage_changed`, `consent_recorded`, `reset`, …), summary (a sentence
written for humans), actor_id, project_id, created_at.

## `alembic_version`

Single column `version_num`, currently `fb86ec9b6cc0` (initial schema).

## Export columns

CSV exports intentionally expose a **subset**: no internal UUIDs, no emails and no contact
fields. Research content (evidence text, insight summaries) is included, because that is the
point of the export. Columns per entity are defined in `EXPORT_SPECS` in
`backend/app/api/v1/endpoints/system.py`, and every file adds `is_synthetic` and `exported_at`,
plus the `X-Data-Origin: synthetic-demo-data` response header.
