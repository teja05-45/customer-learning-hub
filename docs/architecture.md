# Architecture

> **Status (2 November 2026).** This document is retained as the original discovery record.
> Password authentication, server-side sessions and API-enforced roles are now implemented;
> statements below that the API has no authentication, or that `X-Demo-User-Id` grants
> identity, no longer describe the code. See [auth.md](auth.md) and [security.md](security.md).

## Style

A **modular monolith**: one FastAPI process, one React single-page application, one relational
database. Modules are separated by responsibility, not deployed separately. This is deliberate:
the domain is small, the team is one FDE, and a distributed system would add failure modes
without adding product value.

```
React SPA ──HTTP/JSON──▶ FastAPI (/api/v1) ──SQLAlchemy 2──▶ SQLite (PostgreSQL-compatible)
   │                           │
   │ TanStack Query            ├── API routers (HTTP concerns)
   │ React Router              ├── services (business rules, aggregation, serialisation)
   └── nginx in Docker         └── models (persistence) + Pydantic schemas (contracts)
```

## Backend layers

| Layer | Location | Responsibility |
| --- | --- | --- |
| Entry point | `app/main.py` | Lifespan, seeding, CORS, error envelopes, router mounting |
| Configuration | `app/core/config.py` | Environment-driven settings via pydantic-settings |
| Persistence | `app/core/database.py`, `app/models/` | Engine, session, declarative models |
| Contracts | `app/schemas/` | Pydantic request/response models and validation |
| HTTP | `app/api/v1/endpoints/` | Routing, dependencies, status codes, transaction boundaries |
| Domain services | `app/services/` | Metrics, search, serialisation, templates, pipeline rules, activity log |
| Cross-cutting | `app/core/errors.py`, `logging.py` | Single error envelope, structured logs |

Routers do not contain aggregation maths. Anything a second screen needs lives in
`app/services/`; for example both the dashboard and analytics call
`insight_is_reused()` from `services/serializers.py` rather than re-deriving reuse.

## Key services

- `services/dashboard.py` — builds `DashboardResponse`; every number is a query result.
- `services/analytics.py` — builds labelled metrics with `basis` ∈ observed, calculated,
  pending_baseline, plus measurement gaps.
- `services/serializers.py` — maps ORM rows to response models, adds counts and warnings
  (`evidence_warning`, `provenance_warning`, segment gaps).
- `services/pipeline.py` — the only place a recruitment stage changes; always appends a
  `RecruitmentEvent`, including when the trigger is an interview being scheduled or completed.
- `services/search.py` — deterministic keyword search with stop-word handling and
  related-research suggestions based on keyword overlap. No embeddings, no LLM.
- `services/activity.py` — writes the cross-entity audit trail used by project and decision
  timelines.

## Data integrity

- Foreign keys are enabled on SQLite (`PRAGMA foreign_keys=ON`) so constraints actually bite.
- Unique constraints guard `insight_evidence(insight_id, evidence_id)` and the equivalent
  decision links.
- Cascade rules are explicit: project deletion cascades to its questions, recruitment,
  interviews and evidence; user deletion sets ownership columns to null.
- Requests commit once, at the end of a successful handler; validation failures roll back.

## Frontend structure

```
src/
  app/          App routes, session provider, toast provider
  layouts/      AppShell (sidebar, header, search trigger, demo banner)
  pages/        One component per route
  components/   Reusable primitives (ui.tsx), cards, dialogs, global search
  services/     Typed fetch client, error normalisation, query-string builder
  types/        Shared API types
  utils/        Formatters, label maps, state-transition maps
  styles/       Design tokens and layout rules
```

Server state is owned by TanStack Query with explicit query keys; mutations invalidate the
affected keys. Local form state stays local. There is no global Redux-style store.

## Cross-cutting choices

- **Error envelope.** Every failure is `{"error":{"code","message","details"}}`. The client
  turns `details` into per-field messages.
- **Honesty in the response.** Warnings are server-produced, not reconstructed in the UI, so
  every screen shows the same caveat.
- **Demo identity.** `X-Demo-User-Id` identifies an actor for the activity log. It grants no
  permission. See `auth.md`.
- **Synthetic data.** Seeding is idempotent and guarded by a user-count check.

## Trade-offs

| Choice | Benefit | Cost |
| --- | --- | --- |
| SQLite default | Zero-setup demo, single file volume | Single-writer; production needs PostgreSQL |
| Aggregation in Python | Clear, testable formulas | Not tuned for large datasets |
| Warnings in serializers | One source of truth | Slightly chattier payloads |
| No auth | Reviewer can explore immediately | Not deployable to the public internet |
| In-memory filtering for JSON list fields | Portable SQLite/PostgreSQL | Loads all projects; fine at prototype scale |

See `hld.md`, `lld.md`, `decisions.md` and `../docs/05-data-model.md` for detail.
