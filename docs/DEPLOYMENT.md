# Deployment

## Docker Compose (recommended)

From the repository root:

```powershell
docker compose up --build
```

| Service | Container | Host port | Notes |
| --- | --- | --- | --- |
| API | `clh-api` | 8000 | Python 3.12-slim, Uvicorn, health check on `/api/v1/health` |
| Web | `clh-web` | **8081** → 8080 | nginx static build, proxies `/api/` to `backend:8000` |

Open <http://localhost:8081>. The web container starts only after the API reports healthy.
The API creates tables and seeds the synthetic dataset on first start; the SQLite file lives
on the named volume `clh-data` at `/app/data/clh.db`.

```powershell
docker compose logs -f backend     # follow API logs
docker compose down               # stop, keep data
docker compose down -v            # stop and delete the demo database
```

If 8081 is occupied, change the left-hand side of the `frontend` port mapping.

## Local development (Windows PowerShell)

Backend:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\.env.example .env      # optional; defaults are demo-ready
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm ci
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` to `http://127.0.0.1:8000`, so no CORS
configuration is needed locally.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | SQLite under `backend/data` | Any SQLAlchemy URL |
| `ENVIRONMENT` | `development` | Reported by health |
| `LOG_LEVEL` | `INFO` | Logging threshold |
| `DEMO_MODE` | `true` | Labels the session as a demonstration |
| `SEED_ON_STARTUP` | `true` | Run the seed check at startup |
| `SEED_DEMO_DATA` | `true` | Allow synthetic seeding |
| `CORS_ORIGINS` | localhost dev ports | Comma-separated allowed origins |
| `VITE_API_BASE_URL` | empty (same origin) | Frontend API base when not proxied |
| `VITE_PROXY_TARGET` | `http://127.0.0.1:8000` | Vite dev proxy target |

Never commit a `.env` file. Docker Compose sets only non-secret demo values.

## Database setup and migrations

The API creates missing tables at startup, which is enough for the demo. For managed
environments, run Alembic before starting the API:

```powershell
cd backend
.venv\Scripts\python.exe -m alembic upgrade head
```

To point at PostgreSQL, install the driver and set `DATABASE_URL`, for example
`postgresql+psycopg://user:password@host:5432/clh`. The models use portable types; run
Alembic to create the schema.

## Seeding

Seeding is idempotent: it is skipped when users already exist. `POST /api/v1/demo/reset` with
`{"confirm": true, "phrase": "RESET"}` rebuilds the dataset. All data is synthetic.

## Verification after deploy

```powershell
curl http://localhost:8000/api/v1/health
curl http://localhost:8081/api/v1/projects
$env:E2E_BASE_URL="http://localhost:8081"; cd frontend; npx playwright test
```

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Web shows "API could not be reached" | API not healthy | `docker compose ps`, then `docker compose logs backend` |
| Port 8000 already in use | Local Uvicorn running | Stop it, or change the API port mapping |
| Port 8081 in use | Another service | Change the host port mapping |
| Empty lists everywhere | Seed disabled or DB reset | Check `SEED_ON_STARTUP`, POST demo reset |
| 422 on every write | Request missing required fields | Inspect the `details` array in the error envelope |
| Stale demo data after schema change | Old volume | `docker compose down -v` and restart |
| Playwright fails to connect | Wrong base URL | Set `E2E_BASE_URL` and `E2E_API_URL` |

## Production gaps

This stack is not production-hardened: there is no authentication, no TLS termination, no
rate limiting and SQLite is single-writer. See `SECURITY.md`, `AUTH.md` and `ROADMAP.md`.
