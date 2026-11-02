# API Reference

Base path: `/api/v1`. Interactive documentation: `http://localhost:8000/docs`.
All responses are JSON. Errors always use one envelope:

```json
{"error": {"code": "rule_violation", "message": "Cannot move from 'invited' to 'completed'.", "details": {"allowed": ["responded", "declined", "no_response", "cancelled"]}}}
```

Demo identity is sent as `X-Demo-User-Id: <user id>`. It is recorded on activity entries and
grants no permission.

## System

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Status, version, environment, database, demo mode, seeded flag |
| GET | `/session` | Demo users, roles and the explicit "not authentication" notice |
| GET | `/dashboard?months=6` | Derived overview metrics, timeline, segments, activity |
| GET | `/analytics` | Labelled metrics, reuse detail, measurement gaps |
| GET | `/search?q=&types=` | Global search across seven entity types |
| GET | `/settings` / PATCH | Organisation settings (name, research lead, recording default) |
| POST | `/demo/reset` | Rebuild the synthetic dataset (`{"confirm": true, "phrase": "RESET"}`) |
| GET | `/exports/{entity}.csv` | CSV export; every row and the response header label synthetic data |

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
| POST | `/participants` | Contact fields are ignored; record is `is_synthetic: true` |
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
