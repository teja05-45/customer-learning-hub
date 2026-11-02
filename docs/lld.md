# Low-Level Design

> **Status (2 November 2026).** This document is retained as the original discovery record.
> Password authentication, server-side sessions and API-enforced roles are now implemented;
> statements below that the API has no authentication, or that `X-Demo-User-Id` grants
> identity, no longer describe the code. See [auth.md](auth.md) and [security.md](security.md).

## Backend modules

| Module | Key symbols | Notes |
| --- | --- | --- |
| `app/main.py` | `lifespan`, `_ensure_seed_data`, exception handlers | Creates tables, seeds only when the user table is empty |
| `app/core/database.py` | `Base`, `engine`, `SessionLocal`, `get_db`, `init_db` | Enables SQLite foreign keys on connect |
| `app/core/errors.py` | `AppError`, `NotFoundError`, `ConflictError`, `RuleViolationError` | Status and code live on the class |
| `app/api/deps.py` | `get_actor`, `Pagination` | Demo identity via `X-Demo-User-Id`, 1–100 page size |
| `app/services/pipeline.py` | `advance_stage(db, record, to_stage, note, actor_id, force)` | Single place a stage changes; appends `RecruitmentEvent` |
| `app/services/serializers.py` | `project_summary`, `recruitment_out`, `evidence_out`, `decision_detail`, `insight_is_reused` | Derived counts and warnings |
| `app/services/dashboard.py` | `build_dashboard(db, months)` | Metric queries and 3–12 month timeline |
| `app/services/analytics.py` | `build_analytics(db)` | Labelled metrics, reuse detail, measurement gaps |
| `app/services/search.py` | `search`, `suggest_related`, `_match` | Deterministic keyword search |
| `app/services/common.py` | `next_code`, `as_aware`, `month_key`, `month_sequence` | Code generation and timezone helpers |

## Request lifecycle

1. Uvicorn receives the request; CORS middleware applies the configured origins.
2. FastAPI validates path/query/body against Pydantic schemas.
3. `get_db` yields a session; `get_actor` resolves the demo actor if a header is present.
4. The endpoint loads rows, applies rules, writes an `ActivityLog` entry where relevant.
5. One `db.commit()` per successful request; `db.refresh()` before serialising.
6. The service maps ORM rows to response models, adding derived counts and warnings.
7. Errors raised as `AppError` are converted to the standard envelope by the handler.

## Recruitment transition algorithm

```
advance_stage(record, to_stage, force=False):
    if record.stage == to_stage: return None
    if not force and to_stage not in RECRUITMENT_TRANSITIONS[record.stage]: raise 400
    record.stage = to_stage; record.updated_at = now
    if to_stage == invited: set invited_at if empty; clear responded_at
    if to_stage in RESPONDED_STAGES and responded_at is None: set responded_at
    if to_stage in (invited, scheduled, completed): update participant contact time
    append RecruitmentEvent(from, to, note, actor, now)
```

Interview scheduling calls this with `force=True` because booking a conversation is real
progress even if the board was not updated first. The history event is never skipped.

## Insight validation rule

- Create with `status=validated_internal` and no `evidence_ids` → `400`.
- Patch to `validated_internal` with zero links → `400 rule_violation`, field `evidence_ids`.
- On success, `validated_at` and `validated_by_id` are stamped; moving away clears them.
- `link_evidence` rejects evidence whose `project_id` differs from the insight's project.

## Evidence provenance rule

```
provenance = payload.provenance.strip()
if provenance: status = recorded
else:           status = missing; review_status = flagged; confidence = low
```

`EvidenceOut.is_verified_source` is true only when status is `recorded` and the provenance text
is non-empty. The serializer adds `provenance_warning` when that is false.

## Metric definitions (implemented)

| Metric | Formula |
| --- | --- |
| Response rate | `responded_at IS NOT NULL / invited_at IS NOT NULL` over recruitment records |
| Participants contacted | distinct participant ids whose stage ∈ contacted stages |
| Findings with evidence | insights with ≥ 1 `insight_evidence` row / all insights |
| Decisions with evidence | decisions with ≥ 1 insight or evidence link / all decisions |
| Reuse | insight linked to ≥ 2 decisions, or linked ≥ 14 days after creation |
| Overdue action | due date < today and status ≠ completed |
| Median evidence→decision | days between earliest linked evidence capture and decision creation |
| Segment coverage | recruitment records grouped by participant segment for a project |

## Search algorithm

- Query is lowercased and split on non-alphanumerics.
- Words shorter than 2 characters and stop words are removed.
- Every remaining term must match at least one column (`AND` of `OR` LIKE clauses).
- Results are limited per entity, grouped with labels, and returned with a navigable `href`.
- Suggestions come from keyword overlap (>3 chars) with existing insights and projects.

## Error contract

```json
{"error": {"code": "rule_violation", "message": "...", "details": {"allowed": ["scheduled"]}}}
```

Codes: `not_found` (404), `conflict` (409), `validation_error` (422), `rule_violation` (400),
`forbidden` (403, reserved), `http_error` (other HTTP).

## Frontend data flow

- `services/api.ts` normalises transport errors into `ApiError` and parses the envelope.
- Query keys mirror resources: `['projects', params]`, `['recruitment', params]`, `['insight', id]`.
- Mutations invalidate the resource plus `['dashboard']` where the metric changes.
- Toast provider is the only routine feedback channel; destructive actions use `ConfirmDialog`.
- `SessionProvider` stores the chosen demo user id in `localStorage` under `clh.demoUserId`.

## Test seams

- `conftest.py` points `DATABASE_URL` at a temporary SQLite file before importing the app.
- Tests use the real HTTP surface via `TestClient`; there are no mocked services.
- `sample_ids` resolves a project, participant, completed interview and user from the seed.
