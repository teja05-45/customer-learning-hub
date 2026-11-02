# Customer Learning Hub — Everyday Goods

An evidence-first customer research workspace. Plan a study, recruit synthetic participants,
run the conversation, capture what customers actually said, turn it into a reviewed insight,
and connect that insight to a business decision with a named owner and a due date.

**All data is synthetic.** No real customer was contacted, no Everyday Goods system is
connected, no audio is recorded and no contact details are stored.

![Overview dashboard](docs/screenshots/02-overview.png)

---

## The business problem

Everyday Goods teams struggle to coordinate customer research, find earlier studies, preserve
the customer's own words, keep contradictory evidence, and connect learning to decisions. The
product makes that chain explicit and auditable:

```
Research question → Project → Recruitment → Interview → Evidence → Insight → Decision → Action
```

It also refuses to flatter the sample: small studies are labelled as such, unevidenced decisions
are marked as internal judgement, missing provenance is flagged, and metrics that need a
baseline are shown as "pending" instead of invented.

## Quick start

### Docker (no Python or Node required)

```bash
docker compose up --build
```

| What | Where |
| --- | --- |
| Web app | http://localhost:8081 |
| API | http://localhost:8000/api/v1 |
| OpenAPI docs | http://localhost:8000/docs |

Wait for both containers to report healthy. The API creates the schema, seeds the synthetic
dataset on first start, and nginx proxies `/api` on the same origin.

```bash
docker compose logs -f backend
docker compose down           # keep the demo database
docker compose down -v        # delete it; next start reseeds
```

Host port 8081 is used because 8080 is often occupied. The container listens on 8080.

### Windows local development (PowerShell)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

```powershell
cd frontend
npm ci
npm run dev        # http://localhost:5173
```

Vite proxies `/api` to `http://127.0.0.1:8000`, so no CORS setup is needed locally.
Configuration lives in `backend/.env` (copy `.env.example`); every value has a demo-ready
default.

### Database and migrations

SQLite by default at `backend/data/clh.db`. The API creates missing tables at startup. For a
managed database:

```powershell
cd backend
.venv\Scripts\python.exe -m alembic upgrade head
```

Set `DATABASE_URL` to a PostgreSQL URL to change engines; the models use portable types. See
`docs/DATABASE.md`.

### Reset or reseed

`POST /api/v1/demo/reset` with `{"confirm": true, "phrase": "RESET"}` rebuilds the dataset. The
seed is idempotent: it is skipped when users already exist.

## What the prototype does

| Area | Capability |
| --- | --- |
| Projects | Create from template or blank, edit, archive, questions, target segments, owner, filters |
| Participants | Synthetic directory, segment and eligibility filters, purchase context, participation history; no contact fields accepted |
| Recruitment | Ten-stage pipeline, append-only history, segment coverage, defined response-rate denominator |
| Interviews | Schedule, reschedule, cancel, complete, neutral guide, consent records, notes, summary, follow-up questions |
| Evidence | Five types, provenance and verification status, review action, correction, supporting and contradictory links |
| Insights | Create, edit, link/unlink evidence, confidence, limitations, review, related research |
| Decisions | Problem, rationale, limitations, linked sources, owner, status; unevidenced decisions labelled |
| Actions | Owner, due date, priority, status, overdue tracking |
| Overview | Derived metrics, segment coverage, timeline, outstanding follow-ups, activity trail |
| Analytics | Basis-labelled metrics, reuse detail, unresolved questions, measurement gaps |
| Search | Deterministic search across seven entity types, with related-research suggestions |
| Exports | CSV per entity, labelled synthetic and formula-injection safe |
| Settings | Organisation name, research lead, recording default, retention months, demo reset |
| Demo entry | Role picker and banner — explicitly **not** authentication |

## Architecture

A modular monolith:

```
React 18 + TypeScript (Vite) ── /api/v1 ──▶ FastAPI ── SQLAlchemy 2 ──▶ SQLite (PostgreSQL-compatible)
        TanStack Query                      routers → services → models
        React Router                        one error envelope, structured logs
```

- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, pytest, HTTPX. Routers handle HTTP;
  `app/services/` owns metrics, search, serialisation, templates and pipeline rules.
- **Frontend:** React 18, TypeScript, Vite, Bootstrap 5, React Router, TanStack Query,
  React Hook Form + Zod, Recharts, Lucide.
- **Infrastructure:** two Docker images, Compose with a persistent volume, health checks,
  nginx reverse proxy, idempotent seed.

Read `docs/HLD.md`, `docs/LLD.md` and `docs/ARCHITECTURE.md` for detail.

## Repository layout

```
backend/
  app/api/v1/endpoints/   HTTP endpoints
  app/services/           dashboard, analytics, search, serializers, pipeline, activity
  app/models/             SQLAlchemy models
  app/schemas/            Pydantic contracts
  app/seed/               synthetic demo dataset
  alembic/                migration environment and initial revision
  tests/                  46 pytest tests
frontend/
  src/pages/              one component per screen
  src/components/         shared UI, evidence card, search, dialogs
  src/services/api.ts     typed fetch client and error normalisation
  e2e/                    Playwright smoke, accessibility, journey, screenshots
docs/                     22 canonical documents + original discovery set
compose.yaml              API + nginx web app, one command
```

## Verification

These commands were executed for this release:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q                 # 46 passed

cd ..\frontend
npm run typecheck                                     # clean
npm run build                                         # clean (one chunk-size advisory)
npx playwright test                                   # 7 passed

cd ..
docker compose up -d --build                          # both services healthy
```

Run the browser suite against the Docker build:

```powershell
$env:E2E_BASE_URL="http://localhost:8081"
cd frontend; npx playwright test
```

## Security and known limitations

- Synthetic data only; participant contact fields are not accepted by the schema.
- Recording is disabled by default and cannot be enabled without recorded consent. No audio is
  captured.
- **No authentication or authorisation.** The role picker is a demo convenience. This is the
  first production prerequisite; see `docs/AUTH.md`.
- SQLite is single-writer; PostgreSQL is the deployment path.
- Some list screens load all rows rather than paginating.
- Evidence deletion is permanent in this prototype (no tombstone).
- Research activity is never attributed to revenue or repeat-purchase change.

Full lists: `docs/RISKS.md`, `docs/DEFECT_REGISTER.md`, `docs/TASKS.md`.

## Documentation

| Document | Contents |
| --- | --- |
| `docs/PRD.md` | Problem, users, requirements, non-goals |
| `docs/ARCHITECTURE.md` | Modules, boundaries, cross-cutting choices |
| `docs/HLD.md` / `docs/LLD.md` | System design and implementation detail |
| `docs/TECH_STACK.md` | Pinned versions and deliberate omissions |
| `docs/DESIGN.md` | Palette, components, required states, accessibility |
| `docs/DATABASE.md` | Tables, relationships, constraints, migrations |
| `docs/API.md` | Endpoint reference, vocabularies, examples |
| `docs/AUTH.md` | Demo identity and the production path |
| `docs/SECURITY.md` | Minimisation, consent, validation, threats |
| `docs/TESTING.md` | Suites, commands, actual results, gaps |
| `docs/DEPLOYMENT.md` | Docker, Windows, migrations, troubleshooting |
| `docs/OPERATIONS.md` | Runbook, backup, incidents, rollback |
| `docs/IMPLEMENTATION_PLAN.md` | Three-week FDE plan with dependencies and risks |
| `docs/TASKS.md` / `docs/ROADMAP.md` | Delivered work and what comes next |
| `docs/ACCEPTANCE_CRITERIA.md` | Every criterion with verification status |
| `docs/DEFECT_REGISTER.md` | Confirmed defects, gaps, non-reproduced reports |
| `docs/DECISIONS.md` / `docs/RISKS.md` | ADRs and risk register |
| `docs/CHANGELOG.md` | What changed in this hardening release |
| `docs/STAGE_COMPLETION_REPORT.md` | Delivery report and final results |

The original discovery documents (`docs/01-…` to `docs/20-…`) are retained; `docs/README.md`
maps both sets.

## Licence and provenance

Portfolio prototype built for the Everyday Goods customer-learning exercise. Synthetic data is
generated by `backend/app/seed/demo_data.py`; no third-party customer data is included.
