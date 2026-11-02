# Deployment

## Three supported ways to run it

### 1. Docker Compose (recommended for review)

```bash
docker compose up --build
docker compose ps          # both containers should report healthy
```

| Service | Image | Host port | Purpose |
| --- | --- | --- | --- |
| `backend` | `python:3.12-slim` + uvicorn | 8000 | FastAPI, seeds on first start |
| `frontend` | `node:20-alpine` build → `nginx:1.27-alpine` | **8081** → 8080 | Static bundle + `/api` reverse proxy |

Why 8081: port 8080 is commonly already in use on developer machines. The container always
listens on 8080; only the host side of the mapping changes.

Both images ship a `HEALTHCHECK`, and `frontend` waits for `backend` to be healthy
(`depends_on: condition: service_healthy`) so the app never serves a page whose API is not
ready.

Data lives on the named volume `clh-data`, mounted at `/app/data` and holding
`clh.db`. `docker compose down` keeps the demo data; `docker compose down -v` deletes it and
the next start reseeds.

### 2. Local development

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

cd frontend
npm install
npm run dev            # :5173, proxies /api to 127.0.0.1:8000
```

Vite's proxy means the browser only ever sees one origin in development, so CORS is configured
but not exercised day to day.

### 3. Frontend against any API

`VITE_API_BASE_URL` is prepended to `/api/v1` at build time:

```bash
VITE_API_BASE_URL=https://api.example.test npm run build
```

## Environment variables

| Variable | Default | Notes |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///backend/data/clh.db` | Any SQLAlchemy URL; Docker sets `sqlite:////app/data/clh.db` |
| `ENVIRONMENT` | `development` | Reported by `/health` |
| `LOG_LEVEL` | `INFO` | `DEBUG` adds request detail |
| `CORS_ORIGINS` | localhost dev origins | Comma separated |
| `DEMO_MODE` | `true` | Reported by `/health` and `/session` |
| `SEED_ON_STARTUP` | `true` | Seeds only when the users table is empty |
| `SEED_DEMO_DATA` | `true` | Off for a genuinely empty instance |
| `VITE_API_BASE_URL` | empty (same origin) | Frontend build-time |
| `VITE_PROXY_TARGET` | `http://127.0.0.1:8000` | Vite dev proxy target |

`compose.yaml` sets the backend values explicitly, so the stack behaves the same on any machine.

## PostgreSQL

```bash
export DATABASE_URL="postgresql+psycopg://clh:secret@localhost:5432/clh"
pip install "psycopg[binary]"
cd backend && .venv/Scripts/alembic upgrade head
uvicorn app.main:app
```

The Alembic migration `fb86ec9b6cc0` creates the full schema. Two SQLite-isms to watch when
porting: `ORDER BY … NULLS LAST` (supported by PostgreSQL, emulated on SQLite) and JSON columns
(stored as text on SQLite, `json` on PostgreSQL — both read back as Python lists).

## Production shape this prototype does **not** reach

A real deployment needs, at minimum:

1. **Authentication** — the plan is in [AUTH.md](AUTH.md).
2. **A managed database** with backups, and migrations run as a release step, not on import.
3. **A reverse proxy with TLS** in front of nginx, and `CORS_ORIGINS` restricted to the real
   origin.
4. **Structured log shipping** — logging is JSON-ish key/value to stdout today, ready for
   Docker or a collector, but nothing consumes it.
5. **Secrets management** — the app takes no secrets today; the moment auth exists it will.
6. **Media and retention policy** if audio or attachments are ever added
   ([13-security-and-privacy.md](13-security-and-privacy.md)).

## Operations

| Task | Command |
| --- | --- |
| Logs | `docker compose logs -f backend` |
| Health | `curl -s localhost:8000/api/v1/health` |
| Reset demo data | Settings → Reset, or `POST /api/v1/demo/reset` with `{"confirm": true, "phrase": "RESET"}` |
| Backup SQLite | `docker compose exec backend python -c "import shutil;shutil.copy('/app/data/clh.db','/app/data/backup.db')"` then copy out of the volume |
| Migrate | `alembic upgrade head` |
| Rebuild after code change | `docker compose up -d --build` |
| Shell in container | `docker compose exec backend bash` |

Startup is idempotent: `init_db()` creates missing tables and the seed runs only when there are
no users. Starting twice does not duplicate records — verified by running the stack from a
clean volume and then restarting.

## Resource expectations

- Backend image 280 MB, measured idle memory 113 MB (`docker stats`).
- Web image 75 MB (nginx + 1.2 MB of built assets), measured idle memory 4.5 MB.
- The dataset is ~70 rows; no query in the app takes measurable time at this size. The
  dashboard is the heaviest endpoint (one query per panel, all indexed by project or date),
  and it answers in 37–58 ms locally through nginx; search answers in 10–14 ms.

## What would break first at scale

1. The dashboard's per-panel queries — fine at hundreds of rows, worth caching at tens of
   thousands.
2. Search — `LIKE '%term%'` scans; PostgreSQL full-text or `pg_trgm` is the next step.
3. SQLite write contention with more than a handful of concurrent users.
