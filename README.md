# Customer Learning Hub — Everyday Goods

An evidence-first customer research workspace. Plan a study, build a synthetic customer cohort, run
recruitment and consent, capture the conversation, turn it into reviewed evidence and insight, connect
it to a business decision with a named owner, and record whether the expected change actually happened.

The demo is seeded with **synthetic data only**. Seeding is off by default, so a production instance
starts empty and is claimed by its first administrator. No real customer is contacted, no Everyday
Goods system is connected, no audio is recorded, and no contact details are stored.

![Overview dashboard](docs/screenshots/02-overview.png)

## 1. Project overview

Customer Learning Hub is a research operations product for a consumer-goods team. It is deliberately
built around one chain rather than a pile of unrelated registers:

```
Research project → Customer discovery → Recruitment and consent
→ Sessions or asynchronous feedback → Evidence → Insights
→ Decisions → Actions → Outcome measurement
```

The application refuses to flatter the evidence: small samples are labelled, a decision without linked
customer evidence is marked as internal judgement, a survey is labelled as shallower than an interview,
and an outcome cannot be marked achieved without an actual result.

## 2. Business problem

Everyday Goods teams run research in the gaps between campaigns and support queues. Findings live in
decks, decisions lose their source, contradictory evidence disappears, and nobody checks whether the
change worked. This workspace keeps the customer's words and the researcher's interpretation separate,
preserves provenance and contradictions, assigns ownership, and closes the loop with measurement.

## 3. Target users

| User | Main job |
| --- | --- |
| Research manager / lead researcher | Plan projects, protect evidence quality, review insights |
| Researcher | Recruit, schedule, capture evidence and draft findings |
| Product / category manager (business owner) | Turn findings into decisions and own actions |
| Customer experience / support | Read evidence and contribute feedback sources |
| Executive / admin | Review the portfolio, configure the workspace, export data |

## 4. Core capabilities

Only implemented capabilities are listed. Incomplete stages are marked in section 5 and section 16.

| Area | Capability |
| --- | --- |
| Projects | Create, edit, archive, questions, target segments, owner, business function, filters |
| Project access | Per-project membership (`viewer`, `editor`, `project_owner`); admins are implicit owners; project lists, dashboard, analytics, search and exports are scoped to visible projects |
| Customers | Synthetic participant directory with segment, eligibility and purchase context; no contact fields accepted |
| Customer profile | Participation history, per-interview evidence/insight counts, feedback history, recruitment records |
| Recruitment | Ten-stage pipeline, append-only stage history, segment coverage, defined response-rate denominator |
| Consent | Requested/granted/denied/withdrawn records, append-only history, withdrawal consequences and audit |
| Sessions | Schedule, reschedule, cancel, complete, neutral guide, notes, summary, consent precondition |
| Feedback | Interviews, written feedback, forms, surveys, support, reviews and imports in one provenance-preserving register; explicit depth labels |
| Evidence | Five types, provenance snapshot, review, correction, supporting/contradictory/contextual links |
| Insights | Create, edit, link/unlink evidence, confidence, limitations, segments, review |
| Decisions | Problem, rationale, limitations, linked insights and evidence, owner, status; unevidenced decisions labelled |
| Actions | Owner, due date, priority, status, derived overdue |
| Outcomes | Metric, baseline, target, direction, window, owner, data source, actual result, derived status |
| Learning journey | Project board and timeline derived from real records, with past/upcoming/overdue states |
| Search | Deterministic search across seven entity types, with related-research suggestions |
| Exports | Ten CSV exports with correct headers, Unicode, formula-injection safety and audit logging |
| Analytics | Basis-labelled metrics, segment coverage, unresolved questions, measurement gaps |
| Settings | Organisation, research lead, recording default, retention, user administration, demo reset |
| Authentication | Email + password, PBKDF2 hashing, server-side sessions in an HTTP-only cookie, sign-out, password change |
| Authorisation | API-enforced workspace roles **and** per-project membership; the browser can assert neither |

## 5. End-to-end business workflow

1. **Research project** — define the business question, objective, methodology, functions and target
   segments. Questions live with the project.
2. **Customer discovery** — search the synthetic directory by segment, eligibility and purchase
   context. There are no email addresses, phone numbers or addresses to leak.
3. **Recruitment and consent** — move a participant through the pipeline. Consent is append-only.
   Withdrawal cancels future sessions, blocks re-booking, flags the participant and keeps prior
   evidence; it does not silently erase lawful research.
4. **Sessions or asynchronous feedback** — run a moderated session or record a survey/support/review
   source. A feedback source carries a depth label so it is never presented as an interview.
5. **Evidence** — capture what the customer actually said, with provenance, separately from the
   researcher's interpretation. Contradictory evidence is a first-class type.
6. **Insights** — link supporting, contradictory and contextual evidence. An insight with only
   contextual evidence is not presented as supported.
7. **Decisions** — record the problem, rationale, limitations and linked evidence. A decision without
   customer evidence is labelled as internal judgement.
8. **Actions** — assign an owner, due date and priority. Overdue is derived, not stored.
9. **Outcome measurement** — plan a metric and target before the result exists; record the actual
   result later. Status is calculated from target, direction and actual.

Project access is an explicit grant, not a side effect of signing in. A workspace role decides *what*
kind of work a person may do; membership decides *which* projects they may do it in. A request must
satisfy both gates. See `docs/authorization-and-permissions.md`.

**Incomplete or out of scope:** multi-tenant/organisation isolation above project membership, a formal
retention/deletion policy after withdrawal, SSO, real outreach, audio capture, commerce/support
integrations and hosted deployment.

## 6. Product screenshots

All screenshots were captured from the running production build after real seeded data loaded. They
are grouped by the part of the workspace they describe.

### Workspace

| Overview | Project register |
| --- | --- |
| ![Overview](docs/screenshots/02-overview.png) | ![Projects](docs/screenshots/03-projects.png) |

| Global search | Login / demo entry |
| --- | --- |
| ![Search](docs/screenshots/17-global-search.png) | ![Login](docs/screenshots/01-demo-entry.png) |

### Customer management

| Participant directory | Customer profile with feedback history |
| --- | --- |
| ![Participants](docs/screenshots/06-participants.png) | ![Customer profile](docs/screenshots/24-participant-profile.png) |

### Research

| Recruitment | Interview workspace |
| --- | --- |
| ![Recruitment](docs/screenshots/07-recruitment.png) | ![Interview](docs/screenshots/09-interview-workspace.png) |

| Feedback sources | Consent withdrawal |
| --- | --- |
| ![Feedback](docs/screenshots/19-feedback-sources.png) | ![Consent withdrawal](docs/screenshots/25-consent-withdrawal.png) |

### Evidence and insights

| Evidence library | Insight traceability |
| --- | --- |
| ![Evidence](docs/screenshots/20-evidence.png) | ![Insight](docs/screenshots/11-insight-traceability.png) |

### Decisions and actions

| Decision register | Outcome measurement |
| --- | --- |
| ![Decisions](docs/screenshots/12-decision-register.png) | ![Outcomes](docs/screenshots/21-outcomes.png) |

### Learning journey

| Board | Timeline |
| --- | --- |
| ![Journey board](docs/screenshots/22-project-journey-board.png) | ![Journey timeline](docs/screenshots/23-project-journey-timeline.png) |

### Reports and administration

| Analytics | Settings |
| --- | --- |
| ![Analytics](docs/screenshots/15-analytics.png) | ![Settings](docs/screenshots/16-settings.png) |

### Responsive

| Mobile overview (375 px) | Tablet projects (768 px) |
| --- | --- |
| ![Mobile](docs/screenshots/18-mobile-overview.png) | ![Tablet](docs/screenshots/26-tablet-projects.png) |

## 7. Architecture

```mermaid
flowchart LR
  B[Browser]
  subgraph FE[React 18 + TypeScript · Vite]
    R[React Router · lazy routes]
    Q[TanStack Query]
    U[Notion-style design layer]
  end
  subgraph BE[FastAPI modular monolith]
    A[API routers /api/v1]
    S[Services: journey, search, metrics, pipeline, activity]
    M[SQLAlchemy 2 models]
  end
  DB[(SQLite / PostgreSQL)]
  B --> FE
  R --> Q --> A
  A --> S --> M --> DB
  M -. Alembic migrations .-> DB
```

- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, pytest, HTTPX. Routers handle HTTP;
  `app/services/` owns metrics, search, journey derivation, serialisation, templates and pipeline rules.
- **Frontend:** React 18, TypeScript, Vite, Bootstrap 5, React Router, TanStack Query, React Hook Form
  + Zod, Recharts, Lucide. The current palette is implemented in `frontend/src/styles/notion.css`.
- **Infrastructure:** two Docker images, Compose with a named volume, health checks, nginx proxy,
  idempotent seed.

More detail: `docs/hld.md`, `docs/lld.md`, `docs/architecture.md`.

## 8. Database design

| Entity | Purpose | Key relationships |
| --- | --- | --- |
| `users` | Workspace users and roles | owns projects, decisions, actions, outcomes |
| `research_projects` | A study and its business question | has questions, recruitment records, interviews, insights |
| `participants` | Synthetic customers; no contact details | recruitment records, interviews, feedback |
| `recruitment_records` | Pipeline state per participant/project | belongs to project and participant; append-only stage history |
| `interviews` | Scheduled/completed sessions | participant, project, consent records, evidence |
| `consent_records` | Append-only legal consent history | interview; scope, status, actor, note, timestamp |
| `feedback_sources` | Any asynchronous source | project, optional participant/interview; can become evidence |
| `evidence` | Customer statement or observation | interview or feedback source; provenance snapshot |
| `insights` | Reviewed finding | project; many-to-many evidence with role and rationale |
| `decisions` | Business decision | project, owner, insights, evidence |
| `business_actions` | Follow-up work | decision, owner, due date, status |
| `outcomes` | Expected vs actual change | decision, optional action, owner |
| `activity_events` | Audit trail | entity type/id, actor, project, timestamp |

Relationships that carry reasoning (insight ↔ evidence, decision ↔ insight) are explicit tables, not
JSON blobs, so role, rationale, author and unlink history are preserved.

## 9. Technology stack

Python 3.11, FastAPI 0.115.6, Pydantic 2.10.4, SQLAlchemy 2.0.36, Alembic, SQLite 3.45 (default) or
PostgreSQL, pytest. React 18, TypeScript, Vite, Bootstrap 5, TanStack Query, React Router, React Hook
Form, Zod, Recharts, Lucide, Axe, Playwright. Node 24 / npm 11 were used for verification; the
frontend Docker build uses Node 20. Docker 29.6 and Compose v5.3 were used for the container check.

## 10. Installation

### Docker (no Python or Node required)

```bash
docker compose up --build
```

| What | Where |
| --- | --- |
| Web app | http://localhost:8081 |
| API | http://localhost:8000/api/v1 |
| OpenAPI docs | http://localhost:8000/docs |

Both services must report healthy. The API creates the schema, applies migrations and seeds the
synthetic dataset on first start; nginx proxies `/api` on the same origin.

```bash
docker compose logs -f backend
docker compose down          # keep the named volume
docker compose down -v       # delete the demo database; next start reseeds
```

### Local development

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # Windows; source .venv/bin/activate on Unix
pip install -r requirements.txt
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm ci
npm run dev                     # http://localhost:5173
```

Vite proxies `/api` to `http://127.0.0.1:8000`.

### Database and migrations

SQLite lives at `backend/data/clh.db` by default. To use a managed database, set `DATABASE_URL` and:

```bash
cd backend
.venv/Scripts/python.exe -m alembic upgrade head
```

### Reset or reseed

`POST /api/v1/demo/reset` with `{"confirm": true, "phrase": "RESET"}` rebuilds the dataset. The seed is
idempotent: it is skipped when users already exist.

## 11. Environment variables

Documented in `.env.example`; no secret values are committed. Backend: `ENVIRONMENT`, `LOG_LEVEL`,
`DATABASE_URL`, `SEED_ON_STARTUP`, `SEED_DEMO_DATA`, `DEMO_MODE`, `COOKIE_SECURE`, `CORS_ORIGINS`,
`LOGIN_MAX_FAILURES`, `LOGIN_WINDOW_SECONDS`, `TRUST_PROXY_HEADERS`. Frontend: `VITE_PROXY_TARGET`
(optional when using the proxy). There is no third-party API key because no external service is
connected.

## 12. Running the application

Development: run the backend on `:8000` and Vite on `:5173`, then open `/`. Demo role cards are shown
only while `DEMO_MODE=true`; otherwise use the seeded email/password accounts or the first-admin claim
flow. Production: set `DEMO_MODE=false`, `SEED_*=false`, a real `DATABASE_URL`, HTTPS and
`COOKIE_SECURE=true`.

## 13. Testing

```bash
# backend
cd backend
.venv/Scripts/python.exe -m pytest -q

# frontend static/build
cd frontend
npm run typecheck
npm run build

# browser suite (needs the app running on :5173 or the Docker build on :8081)
npx playwright install chromium
npx playwright test
E2E_BASE_URL=http://localhost:8081 npx playwright test
```

Current results: **122 backend passed**, TypeScript clean, production build clean, **24 Playwright
passed** against Docker. Axe checks 13 primary screens; responsive tests cover 375, 768, 1024 and
1440 px. There is no frontend unit/component runner; that is a disclosed gap.

## 14. API documentation

FastAPI serves OpenAPI at `/docs` and `/redoc`; the JSON schema is at `/openapi.json`. A curated
endpoint reference, auth rules and vocabularies are in `docs/api.md`. Every error uses one envelope:
`{"error": {"code", "message", "details"}}`.

## 15. Security

- Server-side sessions in an HTTP-only cookie; PBKDF2 password hashes; CSRF origin checks on unsafe
  methods; login failure limiting (8 per 5 minutes by default).
- Workspace roles and project memberships are enforced by the API. A browser can assert neither, and
  hiding a control is never treated as the control.
- Unauthorized project access returns `403`; a viewer without editor standing cannot write; list,
  dashboard, analytics, search and export queries are scoped to visible projects.
- Participant contact fields are not accepted by the schema. Outreach is simulated through a
  controlled Ops route and recorded as a status, not a message.
- Consent is append-only and audited. Withdrawal stops future research contact, cancels future
  sessions and blocks re-booking; previously collected evidence is retained.
- CSV exports neutralise formula injection and are audited.

**Known security limitation:** workspace administrators are implicit owners of every project, so this
separates team members from one another, not tenants from one another. True multi-tenant isolation
needs a layer above project membership. This residual risk is stated in
`docs/authorization-and-permissions.md` §10.

## 16. Limitations

- No multi-tenant/organisation separation above project membership; admins can see every project by
  design. Project-level membership itself is implemented and tested.
- No retention/deletion automation after consent withdrawal; that is an organisational policy the
  prototype leaves unspecified.
- Search uses leading-wildcard `LIKE`; correct at demo scale, unindexed at scale. A 50,000-row
  benchmark measured 17.91 ms for the scan versus 0.036 ms for an FTS5 trigram lookup.
- No SSO, email password reset or hosted deployment. Login failure limiting exists; enterprise
  identity does not.
- No real commerce, support, email or audio integrations.
- No frontend unit/component test runner.
- `docs/screenshots` is a curated record, not an automated visual-regression baseline.
- The nine-stage journey board scrolls horizontally inside its own container; it is intentionally not
  a drag-and-drop board because status changes must pass entity validation.
- The prototype is synthetic; no claim is made that the seeded sample is representative.

## 17. Roadmap

Separate from the implemented list above:

1. **P0:** project membership, backfill, read/write filtering and adversarial cross-project tests.
2. **P1:** retention/deletion policy for withdrawn consent, with an explicit product decision.
3. **P2:** FTS5 trigram (SQLite) or `pg_trgm` (PostgreSQL) search with a short-query fallback and
   before/after measurements.
4. **P2:** frontend component tests and a CI pipeline running backend, typecheck, build, Playwright and
   axe.
5. **P2:** SSO/OIDC and password reset.
6. **P3:** hosted deployment with TLS, backups and observability.

## Repository layout

```
backend/
  app/api/v1/endpoints/   HTTP endpoints
  app/services/           dashboard, analytics, search, journey, serializers, pipeline, activity
  app/models/             SQLAlchemy models
  app/schemas/            Pydantic contracts
  app/seed/               synthetic demo dataset
  alembic/                migrations
  tests/                  122 pytest tests
frontend/
  src/pages/              one component per screen
  src/components/         shared UI, evidence card, journey board, search, dialogs
  src/services/api.ts     typed fetch client and error normalisation
  src/styles/             base, legacy emerald layer, current Notion-style layer
  e2e/                    Playwright smoke, a11y, responsive, journey, workflows, screenshots
design-system/            design history and master notes
docs/                     audit, QA, delivery, architecture and operational documents
compose.yaml              API + nginx web app, one command
```

## Documentation

| Document | Contents |
| --- | --- |
| `docs/final-qa-baseline.md` | Measured starting point and discrepancies |
| `docs/workflow-validation-matrix.md` | Every workflow, its API/DB/permissions and evidence |
| `docs/page-by-page-qa.md` | Every route, interactions, defects and screenshots |
| `docs/bug-fix-register.md` | Reproductions, root causes, fixes and open P0s |
| `docs/final-delivery-report.md` | Final delivery record and actual test results |
| `docs/final-recruiter-evaluation.md` | Independent scorecard and recommendation |
| `docs/design.md` | Current palette, typography, components and states |
| `docs/api.md` / `docs/auth.md` / `docs/security.md` | API, session roles and data handling |
| `docs/database.md` / `docs/data_dictionary.md` | Schema, constraints and migrations |
| `docs/testing.md` / `docs/accessibility.md` | Test strategy and accessibility notes |
| `docs/deployment.md` / `docs/operations.md` | Docker, local setup, backup and runbook |

The original discovery documents (`docs/01-…` to `docs/20-…`) are retained; `docs/README.md` maps both
sets.

## Licence and provenance

Portfolio prototype built for the Everyday Goods customer-learning exercise. Synthetic data is
generated by `backend/app/seed/demo_data.py`; no third-party customer data is included. This is a
simulated evaluation, not a production deployment.
