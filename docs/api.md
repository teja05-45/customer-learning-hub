# API Reference

Base path: `/api/v1`. Interactive documentation: `http://localhost:8000/docs`.
All responses are JSON. Errors always use one envelope:

```json
{"error": {"code": "rule_violation", "message": "Cannot move from 'invited' to 'completed'.", "details": {"allowed": ["responded", "declined", "no_response", "cancelled"]}}}
```

Every `/api/v1` route except the public ones requires a server-side session, carried by the
`clh_session` HTTP-only cookie issued at login. Public routes are `health`, `session`,
`auth/login`, `auth/logout`, `auth/me`, `auth/register` (empty workspace only) and `auth/demo`
(demo mode only). A missing or expired session returns `401 unauthorized`; a role that may not
perform the write returns `403 forbidden`. `X-Demo-User-Id` is ignored.

Failed sign-ins are throttled per client address and per account: after `LOGIN_MAX_FAILURES`
(default 8) failures inside `LOGIN_WINDOW_SECONDS` (default 300) the login endpoint answers
`429 rate_limited` with a `Retry-After` header and issues no cookie. A successful sign-in clears
the counter. State-changing requests are also refused with `403 csrf_origin_rejected` when the
browser reports an `Origin` or `Referer` this deployment does not trust; requests with neither
header (curl, server-to-server) are unaffected.

## Authentication

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| POST | `/auth/register` | Public while no user exists | `{name, email, password, organisation_name}`; first account becomes `admin`; `403 registration_closed` afterwards |
| POST | `/auth/login` | Public | `{email, password}`; sets the session cookie; identical error for unknown email and wrong password; `429 rate_limited` when throttled |
| POST | `/auth/logout` | Public | Deletes the session row and cookie; idempotent |
| GET | `/auth/me` | Session | Current user |
| POST | `/auth/password` | Session | `{current_password, new_password}`; revokes other sessions |
| POST | `/auth/demo` | Public when `DEMO_MODE=true` | `{user_id}`; issues a real session for a seeded synthetic user; `403 demo_disabled` otherwise |

## Accounts (administrator only)

Every route below requires the `admin` role; a researcher or reviewer receives `403 forbidden`.

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/users` | Every account: name, email, role, job title, active flag, creation time |
| POST | `/users` | `{name, email, role, job_title, password}`; 201; `409 conflict` for a duplicate email |
| PATCH | `/users/{id}` | `{name?, role?, job_title?, is_active?}`; deactivating revokes that account's sessions; the last active administrator cannot be demoted or deactivated (`400 rule_violation`) |
| POST | `/users/{id}/password` | `{new_password}`; revokes the target's sessions. No email is sent — the administrator passes the password on |

## System

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Status, version, environment, database, demo mode, seeded flag |
| GET | `/session` | Demo user directory, role descriptions and the demo-entry notice (public) |
| GET | `/dashboard?months=6` | Derived overview metrics, timeline, segments, activity |
| GET | `/analytics` | Labelled metrics, reuse detail, measurement gaps |
| GET | `/search?q=&types=` | Global search across seven entity types |
| GET | `/settings` / PATCH | Organisation settings (name, research lead, recording default) |
| POST | `/demo/reset` | Rebuild the synthetic dataset (`{"confirm": true, "phrase": "RESET"}`) |
| GET | `/exports/{entity}.csv` | CSV export for `projects`, `participants`, `recruitment`, `interviews`, `evidence`, `feedback`, `insights`, `decisions`, `actions`; any signed-in member; `X-Row-Count`, `X-Data-Origin`; audited |

## Projects

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/projects` | `q`, `status[]`, `priority[]`, `owner_id`, `business_function`, `include_archived`, `page`, `page_size` |
| POST | `/projects` | Creates questions with the project; 201 |
| GET | `/projects/{id}` | Includes counts, unresolved questions and segment gap |
| PATCH | `/projects/{id}` | Partial update; deadline must not precede start date |
| POST | `/projects/{id}/archive` | Sets archived status and timestamp; evidence remains |
| GET | `/projects/templates` | Project templates |
| POST | `/projects/{id}/questions` | Add a research question |
| PATCH | `/projects/{id}/questions/{qid}` | Update question text/resolution |
| DELETE | `/projects/{id}/questions/{qid}` | Remove a question |

## Participants and recruitment

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/participants` | `q`, `segment[]`, `eligibility[]`, `product_category`, `sort`, pagination |
| POST | `/participants` | Contact fields are ignored; records created here are real, so `is_synthetic: false` (only the seed sets it true) |
| GET | `/participants/{id}` | Recruitment history, participation history, evidence count |
| PATCH | `/participants/{id}` | Edit segment, eligibility, purchase context, notes |
| POST | `/participants/{id}/assign` | Add to a project pipeline |
| GET | `/recruitment` | `project_id`, `stage[]`, `segment[]`, `q`; returns stage counts, coverage, warnings and **stage history** |
| POST | `/recruitment` | Bulk add; skips ineligible/duplicates with reasons |
| GET | `/recruitment/{id}` | Single record with full timeline |
| PATCH | `/recruitment/{id}` | Stage transition validated; appends history event |
| DELETE | `/recruitment/{id}` | Remove a record from the pipeline |

## Interviews

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/interviews` | `status[]`, `project_id`, `participant_id`, `interviewer_id`, `q`, `upcoming_only` |
| POST | `/interviews` | Creates a guide, links recruitment, advances it to `scheduled` when dated |
| GET | `/interviews/{id}` | Guide, consent records, evidence |
| PATCH | `/interviews/{id}` | Status, schedule, consent status, notes, summary, follow-up questions |
| POST | `/interviews/{id}/consent` | Records one consent decision with actor and timestamp |
| POST | `/interviews/{id}/recording` | Rejected unless recording consent is `granted` |
| GET | `/interviews/guide/default` | Neutral guide plus quality rules |

## Feedback sources

All routes require a session. Writes require the `researcher` or `admin` role; a `cx` or
`business_owner` account receives `403 forbidden`.

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/feedback` | `project_id`, `participant_id`, `source_type[]`, `verification_status[]`, `unattributed_only`, `q`; returns source counts, unverified and unattributed totals |
| POST | `/feedback` | 201. Required: `project_id`, `source_type`, `collection_method`, `content`. Optional: `participant_id`, `interview_id`, `source_reference`, `collected_at`, `contributor`, `interpretation`, `context`, `verification_status` |
| GET | `/feedback/{id}` | One source with project, participant, interview and creator refs, plus `research_depth` and `depth_note` |
| PATCH | `/feedback/{id}` | Edits content, interpretation, context, contributor, reference, method, source type, participant, collected date or verification. Project and interview links are immutable |
| DELETE | `/feedback/{id}` | Audited delete; returns the deleted code |

Rules enforced by the API:

- `source_type=interview` requires an `interview_id` in the same project; other source types may
  not link an interview. Cancelled interviews are rejected.
- `verification_status=verified` requires a non-empty `source_reference`.
- `participant_id` is optional. An unattributed record is returned with `is_attributed: false`.
- `research_depth` is derived from the collection method: interviews are `deep`, written and
  structured feedback `medium`, short surveys `limited`, and support/review/import/manual records
  `context`. `depth_note` explains the limitation.
- The collection date may not be in the future.

## Evidence, insights, decisions, actions

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/evidence` | `project_id`, `interview_id`, `participant_id`, `evidence_type[]`, `review_status[]`, `segment`, `q`, `unverified_only` |
| POST | `/evidence` | Must belong to an interview; missing provenance is flagged |
| GET/PATCH/DELETE | `/evidence/{id}` | PATCH can correct provenance or review status |
| GET | `/evidence/stats` | Totals by type, unverified and unreviewed counts |
| GET | `/insights` | `q`, `project_id`, `status[]`, `segment[]`, `confidence[]`, `owner_id`, `sort` |
| POST | `/insights` | Optional evidence ids; validation requires at least one link |
| GET/PATCH | `/insights/{id}` | Edit fields and review state |
| POST | `/insights/{id}/evidence` | Link with `role` supporting/contradictory; cross-project rejected |
| DELETE | `/insights/{id}/evidence/{evidence_id}` | Unlink; evidence record unchanged |
| GET | `/insights/{id}/related` | Related research by keyword overlap |
| GET | `/insights/{id}/reuse` | Reuse flag and definition |
| GET | `/decisions` | `q`, `status[]`, `business_function[]`, `project_id`, `owner_id`, `has_evidence`, `sort` |
| POST | `/decisions` | Links insights/evidence; may be unevidenced and labelled |
| GET/PATCH | `/decisions/{id}` | Status transitions validated |
| POST | `/decisions/{id}/links` | Link more sources |
| DELETE | `/decisions/{id}/links/{kind}/{link_id}` | Unlink; recomputes sufficiency |
| POST | `/decisions/{id}/actions` | Create follow-up with owner and due date |
| GET | `/actions` | `status[]`, `owner_id`, `decision_id`, `q`, `overdue_only`, `due_before` |
| POST | `/actions` | Create a standalone action |
| GET/PATCH/DELETE | `/actions/{id}` | Update status, owner, due date, priority |

## Status vocabularies

- Project: draft, planning, recruiting, in_progress, analysis, completed, archived.
- Recruitment: identified, selected, invited, responded, scheduled, completed, declined,
  no_response, cancelled, withdrawn (transitions in `app/models/enums.py`).
- Interview: planned, scheduled, in_progress, completed, cancelled.
- Insight: draft, under_review, validated_internal, needs_more_research, archived.
- Decision: proposed, under_review, accepted, rejected, deferred.
- Action: not_started, in_progress, completed, blocked.
- Feedback source: interview, written_feedback, structured_form, short_survey, customer_support,
  product_review, manual_entry, csv_import.
- Collection method: in_person_interview, video_interview, phone_interview, written_feedback,
  structured_form, short_survey, support_feedback, product_review, imported_feedback,
  manual_entry.
- Verification: unverified, needs_review, verified.

## Examples

```bash
curl "http://localhost:8000/api/v1/recruitment?project_id=<id>"
curl -X PATCH http://localhost:8000/api/v1/recruitment/<id> \
  -H "Content-Type: application/json" \
  -d '{"stage":"invited","note":"Invitation sent through Ops (simulated)."}'
curl "http://localhost:8000/api/v1/search?q=shampoo%20scent"
```

See `06-api-reference.md` for narrative examples and `backend/scripts/api_audit.py` for a live
contract audit script.
