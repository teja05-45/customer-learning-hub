# API reference

> **Status (2 November 2026).** This document is retained as the original discovery record.
> Password authentication, server-side sessions and API-enforced roles are now implemented;
> statements below that the API has no authentication, or that `X-Demo-User-Id` grants
> identity, no longer describe the code. See [auth.md](auth.md) and [security.md](security.md).

Base URL: `http://localhost:8000/api/v1` (dev) or `/api/v1` through the web container.
Interactive docs: `http://localhost:8000/docs`, OpenAPI JSON at
`http://localhost:8000/openapi.json`.

61 operations across 14 tags. Every failure uses one envelope:

```json
{ "error": { "code": "rule_violation", "message": "Type RESET and confirm to restore the demo dataset.", "details": { "field": "phrase" } } }
```

| Status | `code` | When |
| --- | --- | --- |
| 400 | `rule_violation` | A domain rule says no (illegal stage jump, missing consent, last-source unlink) |
| 404 | `not_found` | The record does not exist; `details` names the entity and id |
| 409 | `conflict` | The relationship already exists — for example linking the same evidence to an insight twice |
| 422 | `validation_error` | Request body or query failed Pydantic validation; `details` lists field + message |
| 500 | `internal_error` | Unhandled; the message stays generic and the traceback goes to the log |

Lists always return `{ "items": [...], "total": n, "page": 1, "page_size": 20 }`.
Pagination uses `?page=` and `?page_size=` (max 100).

Optional header `X-Demo-User-Id` attributes the activity-log entry to a seeded person. It is
not authentication — omitting it is fine; sending an unknown id is ignored.

## System

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | `{status, version, environment, database, demo_mode, seeded, checked_at}` |
| GET | `/session` | The seeded people for the entry screen, plus a `notice` stating there is no auth |
| GET | `/settings` | Organisation settings |
| PATCH | `/settings` | Update `name`, `recording_default`, `retention_months`, `show_demo_banner` |
| POST | `/demo/reset` | Restore the seed. Body `{ "confirm": true, "phrase": "RESET" }` |
| GET | `/exports/{entity}.csv` | CSV for `projects`, `participants`, `recruitment`, `interviews`, `evidence`, `insights`, `decisions`, `actions` |

`/exports` responds with `text/csv` and `Content-Disposition: attachment;
filename="everyday-goods-<entity>-synthetic.csv"`. Every row carries `is_synthetic=true` and an
`exported_at` timestamp.

## Dashboard and analytics

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/dashboard` | Everything the overview renders in one call |
| GET | `/analytics` | Learning measurements, segment distribution, decision funnel, action completion, unresolved questions, reuse detail, measurement gaps |
| GET | `/search?q=&types=&limit=` | Global search across seven entity types |

### `GET /dashboard`

Flat, frontend-shaped payload: `generated_at`, `active_projects`, `interviews_completed`,
`interviews_upcoming`, `participants_contacted`, `response_rate` (object with numerator,
denominator and a label), `insights_awaiting_review`, `decisions_with_evidence`,
`decisions_total`, `open_actions`, `overdue_actions`, plus `learning`, `timeline`, `segments`,
`decision_status`, `action_status`, `recent_insights`, `upcoming_interviews`,
`recent_activity`, `outstanding_actions`, `projects` and `data_note`.

One request, not eleven, because the overview must render in a single paint.

### `GET /search`

Minimum two characters. All words in the query must appear in one of the entity's searchable
columns — deterministic, no stemming, no vectors, no model. Each result names the entity type
and its project, carries a snippet centred on the match and a `href`. When nothing matches,
`suggestions` offers the nearest real records (for example the three projects that exist) and
`suggestion_reason` explains why.

`types` accepts a comma-separated or repeated list of `project`, `participant`, `interview`,
`evidence`, `insight`, `decision`, `action`.

## Projects

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/projects/templates` | Four templates with objectives and starter questions |
| GET | `/projects` | Filters: `q`, `status` (repeatable), `priority`, `owner_id`, `business_function`, `include_archived` |
| POST | `/projects` | `name`, `objective` required; template `key` optional |
| GET | `/projects/{id}` | Full record with questions, counts and related records |
| PATCH | `/projects/{id}` | Partial update, including status |
| POST | `/projects/{id}/archive` | Sets `archived_at`, hides from active counts |
| POST | `/projects/{id}/questions` | Append a research question |
| PATCH | `/projects/{id}/questions/{qid}` | Edit text, resolve, add a resolution note |
| DELETE | `/projects/{id}/questions/{qid}` | Remove a question |

## Participants and recruitment

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/participants` | Filters: `q`, `segment`, `eligibility`, `product_category`, `sort=name\|recent\|orders\|segment` |
| POST | `/participants` | Creates `PART-xxxx`; no contact fields exist |
| GET | `/participants/{id}` | Record plus recruitment history, interviews, evidence |
| PATCH | `/participants/{id}` | Partial update |
| POST | `/participants/{id}/assign` | Body `{project_id}`; creates a recruitment record at `identified` |
| GET | `/recruitment` | Filters: `project_id`, `stage`, `q` |
| POST | `/recruitment` | Explicit create for an existing participant |
| GET | `/recruitment/{id}` | Record plus its stage event history |
| PATCH | `/recruitment/{id}` | Stage changes must be legal transitions; writes an event |
| DELETE | `/recruitment/{id}` | Removes the record; the participant stays |

Illegal transition example: `PATCH { "stage": "completed" }` on a record at `identified`
returns 422 with `details.allowed = ["selected", "cancelled", "withdrawn"]`.

## Interviews

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/interviews/guide/default` | The default guide: question, purpose, `is_leading` |
| GET | `/interviews` | Filters: `project_id`, `participant_id`, `interviewer_id`, `status`, `q`, `upcoming_only` |
| POST | `/interviews` | Creates `INT-xxxx` and seeds guide questions |
| GET | `/interviews/{id}` | Record, guide, consent records, evidence captured, participant and project summaries |
| PATCH | `/interviews/{id}` | Notes, summary, follow-ups, status, schedule |
| POST | `/interviews/{id}/consent` | `{consent_type, status, note}`; recomputes `consent_status` |
| POST | `/interviews/{id}/recording` | `{enabled: bool}`; refuses when recording consent is declined |

## Evidence

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/evidence` | Filters: `project_id`, `interview_id`, `participant_id`, `evidence_type`, `review_status`, `segment`, `q`, `unverified_only` |
| POST | `/evidence` | `interview_id`, `evidence_type`, `content` required; `interpretation` is separate |
| GET | `/evidence/stats` | Counts by type, provenance and review status; optional `project_id` |
| GET | `/evidence/{id}` | Record with interview, participant, project and linked insights |
| PATCH | `/evidence/{id}` | Partial update, including review status |
| DELETE | `/evidence/{id}` | Also removes insight links |

Provenance statuses: `recorded`, `partial`, `missing`. An evidence row with `missing`
provenance is exactly what the "unverified" filter is for.

## Insights

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/insights` | Filters: `q`, `project_id`, `status`, `segment`, `confidence`, `owner_id`, `sort=recent\|evidence\|confidence\|title` |
| POST | `/insights` | Creates `INS-xxxx`; optional `evidence_ids` to link on create |
| GET | `/insights/{id}` | Record plus linked evidence with roles, decisions that used it |
| PATCH | `/insights/{id}` | Update status, confidence, limitations; validating sets `validated_at` and `validated_by_id` |
| POST | `/insights/{id}/evidence` | `{evidence_id, role: "supporting"\|"contradictory", note}` |
| DELETE | `/insights/{id}/evidence/{eid}` | Unlink |
| GET | `/insights/{id}/related` | Other insight/evidence rows on the same project or segments |
| GET | `/insights/{id}/reuse` | Whether the insight was used in a decision or action |

## Decisions and actions

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/decisions` | Filters: `q`, `status`, `business_function`, `project_id`, `owner_id`, `has_evidence`, `sort=recent\|date\|title` |
| POST | `/decisions` | Creates `DEC-xxx`; links optional on create |
| GET | `/decisions/{id}` | Record with sources, actions and the project |
| PATCH | `/decisions/{id}` | Status, rationale, limitations, `evidence_sufficient` |
| POST | `/decisions/{id}/links` | `{insight_ids: [], evidence_ids: [], role: "supporting"\|"contradictory"}` — links many in one call |
| DELETE | `/decisions/{id}/links/{kind}/{link_id}` | Unlink; recomputes `evidence_sufficient` |
| POST | `/decisions/{id}/actions` | Creates `ACT-xxx` attached to the decision |
| GET | `/actions` | Filters: `status`, `owner_id`, `decision_id`, `q`, `overdue_only`, `due_before` |
| POST | `/actions` | Creates `ACT-xxx`; owner, due date, priority, status |
| GET | `/actions/{id}` | Record with its decision or insight |
| PATCH | `/actions/{id}` | Status, owner, due date; completing sets `completed_at` |
| DELETE | `/actions/{id}` | Remove |

`has_evidence=false` is the register's most useful filter: it lists every decision the business
made without customer research behind it.

## Conventions

- Dates are `YYYY-MM-DD`; timestamps are ISO 8601 with `Z`.
- IDs are UUID strings; human-facing codes (`INT-0003`, `INS-0002`) are separate and stable.
- `PATCH` is partial: send only what changed. Sending `null` clears a nullable field.
- Creating a resource returns the created record with `201`, not a redirect or a bare id.
- CORS allows the dev origins listed in `CORS_ORIGINS`; in Docker the browser stays on one
  origin so CORS is not exercised.
