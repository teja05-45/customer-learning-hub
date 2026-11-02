# Customer Learning Hub — Everyday Goods

A working prototype of an evidence-first customer research workspace: plan a study, recruit
participants, capture what customers actually said, turn it into insights, and connect those
insights to business decisions with named owners.

**All data is synthetic.** No real customer was contacted, no Everyday Goods system is
connected, and nothing in this repository sends email, records audio or stores contact details.

![Overview dashboard](docs/screenshots/02-overview.png)

---

## Run it in two minutes

### Option A — Docker (no Python or Node needed)

```bash
docker compose up --build
```

| What | Where |
| --- | --- |
| Web app | http://localhost:8081 |
| API | http://localhost:8000/api/v1 |
| API docs (Swagger) | http://localhost:8000/docs |

Wait for `clh-api` to report **healthy**; the API seeds the demo dataset on first start and
then serves the web app through nginx on the same origin. Stop with `docker compose down`,
wipe the demo database with `docker compose down -v`.

> The web container listens on 8080 and is published on host port **8081**, because 8080 is
> frequently already occupied. Change the left-hand side of `ports:` in `compose.yaml` if you
> prefer another port.

### Option B — local development

Backend (Python 3.11+):

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate      # Windows; on macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (Node 20+):

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`, so the browser stays on one
origin and no CORS setup is needed day to day.

## What you can do in the prototype

| Area | Capability |
| --- | --- |
| Research projects | Create from a template or blank, edit scope, questions, owners and dates, archive |
| Participants | Synthetic directory with segment, purchase context and eligibility; assign to a project |
| Recruitment | Ten-stage pipeline from identified → completed/declined, with next action and due date |
| Interviews | Schedule, run a guided interview workspace, record consent, keep notes |
| Evidence | Capture verbatim quotes, observations and researcher interpretation, kept separate |
| Insights | Draft findings, link the evidence behind them, set confidence and review status |
| Decisions | Register decisions and link the evidence/insights they rest on — or record that there is none |
| Actions | Own the follow-up work with owner, due date and status |
| Analytics | Segment coverage, decision funnel, insight reuse and honest "pending baseline" gaps |
| Search | One deterministic search across projects, participants, interviews, evidence, insights, decisions, actions |
| Exports | CSV per entity, every file labelled `is_synthetic` |
| Demo controls | Role picker, demo banner, one-click reset back to the seeded dataset |

## Repository layout

```
backend/    FastAPI + SQLAlchemy + Alembic, SQLite by default, pytest suite
frontend/   React 18 + TypeScript + Vite + Bootstrap 5 + Recharts, Playwright e2e
docs/       21 documents: product, data model, API, design system, demo script, plan
compose.yaml  API + nginx-served web app, one command
```

## Verification

```bash
cd backend && .venv/Scripts/python -m pytest -q      # 21 passed
cd frontend && npm run typecheck && npm run build    # clean
cd frontend && npx playwright test                   # screens, flows, screenshots
```

The Playwright suite can run against either build:

```bash
E2E_BASE_URL=http://localhost:8081 npx playwright test e2e/smoke.spec.ts
```

## Where to read next

Start with [`docs/README.md`](docs/README.md) — it maps every document. If you have five
minutes, read [`docs/01-product-brief.md`](docs/01-product-brief.md) and follow
[`docs/09-demo-script.md`](docs/09-demo-script.md) with the app open.

## Honest scope

This is a prototype, not a production service. There is no authentication, no authorisation,
no audit-grade retention policy and no real integration. `docs/AUTH.md`,
`docs/13-security-and-privacy.md` and `docs/17-limitations-and-next-steps.md` describe exactly
what is missing and what it would take to close each gap.
