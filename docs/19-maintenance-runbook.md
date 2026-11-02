# Maintenance runbook

Tasks a successor would actually need. Commands assume the repository root.

## Daily-ish

### Check the stack is alive

```bash
docker compose ps
curl -s localhost:8000/api/v1/health
```

`status: ok`, `database: ok`, `seeded: true`. Anything else, read the logs:

```bash
docker compose logs --tail=100 backend
```

### Restore the demo dataset

Settings → Demo data → **Reset** (type `RESET`), or:

```bash
curl -s -X POST localhost:8000/api/v1/demo/reset \
  -H 'Content-Type: application/json' \
  -d '{"confirm": true, "phrase": "RESET"}'
```

This deletes every row and re-seeds deterministically. It also removes any record the reviewer
created — which is the point.

## Weekly

### Back up the SQLite file

```bash
docker compose exec backend python -c "import shutil; shutil.copy('/app/data/clh.db', '/app/data/clh-backup.db')"
docker cp clh-api:/app/data/clh-backup.db ./clh-backup-$(date +%F).db
```

For a hot copy, stop the container first (`docker compose stop backend`), then copy. SQLite
tolerates the live copy above only because the demo has near-zero write volume; do not rely on
it under load.

### Restore from a backup

```bash
docker compose stop backend
docker cp ./clh-backup-2026-11-01.db clh-api:/app/data/clh.db
docker compose start backend
```

### Check for dependency drift

```bash
cd backend && .venv/Scripts/python -m pip list --outdated
cd frontend && npm outdated
```

Nothing auto-updates. Pinned versions in `requirements.txt` and `package.json` are intentional.

## After a code change

```bash
cd backend && .venv/Scripts/python -m pytest -q
cd frontend && npm run typecheck && npm run build
docker compose up -d --build
```

Then re-run the e2e suite against the built app:

```bash
cd frontend && E2E_BASE_URL=http://localhost:8081 npx playwright test
```

### Regenerate documentation screenshots

```bash
cd frontend && E2E_BASE_URL=http://localhost:8081 npx playwright test e2e/screenshots.spec.ts
```

Writes 18 PNGs into `docs/screenshots/`. They are captured from the real app, so they go stale
the moment a screen changes.

## Schema changes

```bash
cd backend
.venv/Scripts/alembic revision --autogenerate -m "describe the change"
# review the generated file: autogenerate misses server defaults and enum changes
.venv/Scripts/alembic upgrade head
```

Rules of thumb:

- New enum value → no migration; validation lives in `models/enums.py` and Pydantic.
- New column → nullable or with a default, so existing demo databases keep working.
- Renamed column → add, backfill in the migration, drop in a later migration.

Reset the local database if a migration half-applied:

```bash
rm -f backend/data/clh.db && cd backend && .venv/Scripts/alembic upgrade head
```

The app reseeds on next start because the users table is empty.

## Changing the seeded demo data

`backend/app/seed/demo_data.py` is the single source: startup, reset and tests all use it.
Dates are computed relative to "now", so the dataset never looks stale.

After editing:

1. `rm -f backend/data/clh.db` (local) and restart, or reset through the API.
2. Re-run `pytest` — several tests assert counts and codes (`INT-0001`, `INS-0002`).
3. Update the numbers quoted in `docs/09-demo-script.md` and `docs/16-metrics.md` if they moved.
4. Regenerate screenshots.

## Common problems

| Symptom | Cause | Fix |
| --- | --- | --- |
| `docker compose up` fails on port 8080 | Something else (often Apache) holds it | The stack publishes 8081 already; if you changed it, edit `ports:` |
| Web app loads but the API 502s | Backend not healthy yet | `docker compose ps`, wait for `healthy`; check `docker compose logs backend` |
| Data looks like a reviewer's edits | Nobody reset it | Reset via Settings |
| `alembic upgrade` says "table already exists" | Database created by `create_all` | Delete `data/clh.db` and re-run, or `alembic stamp head` |
| Tests pass locally, fail in a fresh clone | Stale `.venv` or missing `npm ci` | Recreate the virtualenv; `npm ci` |
| Playwright cannot find a browser | Browsers not installed | `npx playwright install chromium` |
| Screenshots look stale in a doc | Regenerate them | See above |
| Search returns nothing for an obvious word | Query is under two characters, or all words must match | Try one word |

## Rotating the demo database on a hosted instance

```bash
docker compose down -v      # deletes the volume
docker compose up -d --build
```

The API reseeds on start. Reviewer-created records are gone by design.

## Deleting a participant (manual, since no UI exists)

There is no delete endpoint for participants — deliberate, because removing a person while
keeping their quotes would create unattributable evidence. If one must be removed:

```bash
docker compose exec backend python - <<'PY'
from app.core.database import SessionLocal
from app.models import Evidence, Participant, RecruitmentRecord, Interview
from sqlalchemy import delete, select
db = SessionLocal()
participant = db.execute(select(Participant).where(Participant.code == 'P-1004')).scalar_one()
interview_ids = [i.id for i in db.execute(select(Interview).where(Interview.participant_id == participant.id)).scalars()]
db.execute(delete(Evidence).where(Evidence.participant_id == participant.id))
db.execute(delete(Interview).where(Interview.participant_id == participant.id))
db.execute(delete(RecruitmentRecord).where(RecruitmentRecord.participant_id == participant.id))
db.delete(participant)
db.commit()
print('removed', participant.code, 'and', len(interview_ids), 'interviews')
PY
```

Then delete any insight or decision that now cites nothing, or leave it — `evidence_warning`
will say the insight has no linked evidence.

## Who to ask

This is a prototype with no on-call rota. The code is the documentation of record:
`docs/05-data-model.md`, `docs/06-api-reference.md`, and the tests.
