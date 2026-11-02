# Troubleshooting

Each entry is a failure that actually occurred while building or running this repository, with
the fix that was applied.

## Every download reports "Export failed"

**Cause (fixed):** the export endpoint only allowed the `admin` role, while demonstration entry
signed reviewers in as a `researcher`. The request returned `403`, and the client replaced the
server's message with a generic "The export could not be generated."

**Fix:** exports are now available to any authenticated member (they are reads), the endpoint
re-checks the actor and writes an audit row, and `api.downloadCsv` surfaces the API's own error
envelope, treats an empty body as a failure, and only reports success after the blob is created.
`backend/tests/test_exports.py` covers the regression.

## 401 on every API call after signing in

**Cause:** the demonstration reset deletes and recreates every user, which cascades to
`auth_sessions`. The cookie still exists but its session row is gone.

**Fix:** sign in again after a reset; the UI returns to the entry screen. Tests that reset data
re-authenticate explicitly (`tests/conftest.py`, `test_journey._reset`).

## `POST /auth/demo` returns 403 `demo_disabled`

`DEMO_MODE` is off. That is the production-safe default. Set `DEMO_MODE=true` only for a demo
instance that also runs `SEED_DEMO_DATA=true`; otherwise use email + password.

## `POST /auth/register` returns 403 `registration_closed`

The workspace already has a user. Registration only claims an empty database. Sign in as the
administrator instead.

## `sqlite3.OperationalError: no such column: users.password_hash`

An existing `backend/data/clh.db` volume predates the authentication migration.

**Fix:** run the migration (`python -m alembic upgrade head`) or delete the local database and
re-seed. `init_db()` also adds the column on SQLite for convenience, but Alembic is the supported
path.

## `docker compose up` fails with `open //./pipe/dockerDesktopLinuxEngine`

Docker Desktop is not running on Windows. Start it and wait for "Engine running"; then retry.
This was the state of the machine during the documentation pass, so the Compose health check is
recorded as not re-verified in `acceptance_criteria.md`.

## Port already in use

The web app is published on **8081** because 8080 is commonly occupied; the API uses 8000.
Change only the host side of the mapping in `compose.yaml`, or stop the other process.

## Frontend builds but every request 404s

`VITE_API_BASE_URL` is unset and the app is not behind the nginx proxy. Locally, run
`npm run dev` (Vite proxies `/api` to `127.0.0.1:8000`). In Docker, the web container proxies
`/api` to the `backend` service.

## Playwright fails before any test with a connection error

The browser suite needs the API and the web app running, and its reset helper needs demo data.
Start both (or Compose), then set `E2E_BASE_URL` to the app under test.

## `npm run typecheck` fails after pulling

Run `npm ci`. A stale `node_modules` against a changed `tsconfig` or dependency set produces
errors that the committed lockfile does not.
