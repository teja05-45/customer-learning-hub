# High-Level Design

## Context

```
        Researcher / Business owner / Leadership
                          │  browser
                          ▼
              ┌───────────────────────┐
              │  React SPA (nginx)    │  static build, one origin
              └──────────┬────────────┘
                         │ /api/v1
                         ▼
              ┌───────────────────────┐
              │  FastAPI application  │  validation, rules, metrics
              └──────────┬────────────┘
                         │ SQLAlchemy
                         ▼
              ┌───────────────────────┐
              │ SQLite file / volume  │  synthetic data only
              └───────────────────────┘

External systems: none. No email, calendar, CRM, recording or LLM integration.
```

## Containers

| Container | Image | Port | Persistence | Health |
| --- | --- | --- | --- | --- |
| `clh-api` | `backend/Dockerfile` (python:3.12-slim) | 8000 | named volume `clh-data` at `/app/data` | `GET /api/v1/health` |
| `clh-web` | `frontend/Dockerfile` (node build → nginx:1.27) | 8080, published as 8081 | none | `wget /` |

`clh-web` waits for the API health check (`depends_on: condition: service_healthy`) and
proxies `/api/` to `http://backend:8000/api/`, so the browser never makes a cross-origin
request in Docker.

## Primary flows

### Research journey

1. `POST /projects` creates the project, its questions and its target segments.
2. Participants are created or selected from the synthetic directory.
3. `POST /recruitment` creates one record per participant and an initial history event.
4. Stage changes go through `services/pipeline.advance_stage`, which validates the transition
   and appends history.
5. `POST /interviews` attaches a neutral guide, links back to the recruitment record and moves
   it to `scheduled` when a date is supplied.
6. Completing an interview closes the recruitment stage and logs an activity event.
7. Evidence is captured inside an interview. Provenance determines whether it is verified;
   missing provenance forces `flagged` review status and low confidence.
8. Insights link evidence with an explicit role; cross-project links are rejected.
9. Decisions link insights and/or evidence; the serializer emits a warning when the base is
   absent, thin or contradicted.
10. Actions are created from the decision with an owner and due date; overdue is computed.

### Metric flow

```
rows in DB ──▶ services/dashboard.py ──▶ DashboardResponse ──▶ /overview, /analytics
           └─▶ services/analytics.py ──▶ AnalyticsResponse ──▶ /analytics
```

Both screens derive response rate, evidence-linked decisions and interviews completed from
the same rows. `tests/test_metrics.py` asserts they agree.

### Search flow

`GET /search?q=` performs case-insensitive keyword matching per entity, requires every
meaningful word to appear in at least one searchable column, returns grouped results with
`href` values for navigation, and suggests related existing insights/studies by keyword overlap.

## Non-functional requirements

| Requirement | Design response |
| --- | --- |
| Explainability | Every metric carries a definition; warnings are server-produced |
| Traceability | Evidence keeps interview, participant, project, capture date and provenance |
| Data minimisation | Participant schema accepts no contact details; recording disabled |
| Portability | SQLAlchemy + Alembic, SQLite locally, PostgreSQL-compatible types |
| Operability | Health endpoint, structured logs, single-command Docker, idempotent seed |
| Testability | Real database in tests, service-layer formulas, Playwright integration suite |
| Accessibility | Skip link, focus trap in search, labelled forms, axe scan threshold serious |

## Failure behaviour

- API unreachable → client shows a retryable error state on every page that queries data.
- Invalid transition → `400 rule_violation` with the allowed values in `details`.
- Unknown id → `404 not_found` in the standard envelope.
- Validation failure → `422 validation_error` with per-field messages.
- Analytics with no data → metrics display "No data yet" / "None yet"; no divide-by-zero.
- Seed failure at startup → logged, API still starts; health reports degraded if the DB fails.

## Scaling path (not implemented)

PostgreSQL and a managed platform, pagination for every list, aggregate SQL instead of Python
loops, and background exports. Authentication and role enforcement are the first production
prerequisites. See `ROADMAP.md` and `17-limitations-and-next-steps.md`.
