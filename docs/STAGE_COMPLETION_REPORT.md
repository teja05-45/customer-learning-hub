# Stage Completion Report

> **Status (2 November 2026).** This document is retained as the original discovery record.
> Password authentication, server-side sessions and API-enforced roles are now implemented;
> statements below that the API has no authentication, or that `X-Demo-User-Id` grants
> identity, no longer describe the code. See [auth.md](auth.md) and [security.md](security.md).

## What was delivered

A working, documented prototype of the Customer Learning Hub: project → participant →
recruitment → interview → evidence → insight → decision → action, with derived metrics and
deterministic search. All data is synthetic. The prototype is runnable with one Docker command
and with local Python/Node commands on Windows.

## Defects resolved

| ID | Defect | Severity | Status |
| --- | --- | --- | --- |
| D-001 | Recruitment timeline always empty in the list | High | Fixed, tested |
| D-002 | Interview lifecycle bypassed recruitment history | High | Fixed, tested |
| D-003 | Cross-project evidence link accepted after creation | High | Fixed, tested |
| D-004 | Project total wrong with business-function filter | Medium | Fixed |
| D-005 | Terminal recruitment stages invisible | Medium | Fixed |
| D-006 | Interview summary stored but never shown | Medium | Fixed, tested |
| D-007 | Segment chart failed `svg-img-alt` | Medium | Fixed, verified with axe |
| D-008 | `.env` could enter the Docker build context | High | Fixed |

Two confirmed feature gaps were implemented: insight editing and evidence review/provenance
correction. Four screenshot-reported loading symptoms could not be reproduced against the
running implementation; the investigation is recorded in `DEFECT_REGISTER.md` rather than
claimed as a fix.

## Verification actually executed

| Check | Command | Result |
| --- | --- | --- |
| Backend tests | `pytest -q` (backend) | 46 passed |
| Frontend types | `npm run typecheck` | clean |
| Frontend build | `npm run build` | succeeded; one chunk-size advisory |
| Browser suite | `npx playwright test` | 7 passed (smoke 3, a11y 2, journey 1, screenshots 1) |
| Docker build | `docker compose build` | both images built |
| Docker runtime | `docker compose up -d` | API and web healthy |
| Proxy | `GET :8081/api/v1/projects` | 200 |
| Container mode | `GET :8081/api/v1/health` | `environment: production`, seeded |

A stale local Uvicorn held host port 8000 during the first Docker check and made health report
`development`; it was terminated and the container verified through the nginx proxy. This is
recorded because it affected the observed result.

## Architecture delivered

- Modular monolith: FastAPI routers → services → models, React SPA with TanStack Query.
- Single error envelope, validation at the boundary, transactions per request.
- One recruitment transition service that guarantees history.
- Shared metric services so the dashboard and analytics cannot drift.
- SQLite by default with a PostgreSQL-compatible schema and Alembic revision.
- Two Docker images, persistent volume, health checks, nginx proxy.

## Remaining gaps (explicit)

1. **No authentication or authorisation.** Demo role entry is labelled and tested as such.
2. **SQLite single-writer.** PostgreSQL is the production path.
3. **Several lists are unpaginated.** Fine at prototype volume, listed as P1.
4. **Evidence deletion is permanent.** No tombstone or immutable audit trail yet.
5. **Frontend bundle is a single ~988 kB chunk (~270 kB gzip).** Code-splitting scheduled.
6. **No statistical representativeness claim.** Deliberate; not a gap to close.
7. **No decision outcome tracking.** The product records decisions, not whether they worked.

## Delivery readiness

Suitable for: a customer demo, a technical interview, and local evaluation on Windows or via
Docker. Not suitable for: public hosting, real customer contact, or storing personal data.

## Documentation

Twenty-two canonical documents exist alongside the original discovery set: PRD, architecture,
HLD, LLD, tech stack, design, database, API, auth, security, testing, deployment,
implementation plan, tasks, roadmap, changelog, decisions, risks, operations, acceptance
criteria, defect register and this report. `README.md` covers setup, commands and limitations.

## Recommended next actions

1. Add authentication and server-side role checks (P0).
2. Move to PostgreSQL and run migrations in deployment (P0).
3. Add immutable audit events for deletion and status changes (P1).
4. Paginate and push aggregation into SQL (P1).
5. Add decision outcome review and reuse-by-team reporting (P2).
