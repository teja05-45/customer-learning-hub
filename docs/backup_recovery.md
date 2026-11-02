# Backup and Recovery

## Scope

Two kinds of state exist: the database and the environment/configuration. Nothing else is
durable — there are no uploaded files, no audio and no external object storage.

| State | Where | Backup method |
| --- | --- | --- |
| Database (SQLite) | `clh-data` Docker volume at `/app/data/clh.db`, or `backend/data/clh.db` locally | Consistent file copy while the API is stopped, or `sqlite3 .backup` while it runs |
| Database (PostgreSQL) | `DATABASE_URL` target | `pg_dump` / managed snapshot |
| Configuration | Environment variables, `.env` (not committed) | Secret store / deployment configuration history |
| Alembic revision | Repository | Git |

## Procedure — SQLite (Docker)

```bash
# 1. Stop the API so no write is in flight (the web container can stay up).
docker compose stop backend

# 2. Copy the database out of the named volume.
docker run --rm \
  -v customer-learning-hub_clh-data:/data \
  -v "$PWD/backups:/backup" \
  alpine sh -c 'cp /data/clh.db /backup/clh-$(date +%Y%m%d-%H%M).db'

# 3. Restart and check health.
docker compose start backend
curl -fsS http://localhost:8000/api/v1/health
```

Prefer `sqlite3 /app/data/clh.db ".backup '/backup/clh.db'"` when the service must stay up: it
takes a consistent snapshot instead of copying a file mid-write.

## Procedure — SQLite (local)

```bash
# Stop uvicorn, then:
cp backend/data/clh.db "backend/data/clh-$(date +%Y%m%d-%H%M).db"
```

## Restore

```bash
docker compose stop backend
docker run --rm \
  -v customer-learning-hub_clh-data:/data \
  -v "$PWD/backups:/backup" \
  alpine sh -c 'cp /backup/clh-20261102-1200.db /data/clh.db'
docker compose start backend
curl -fsS http://localhost:8000/api/v1/health
```

Then verify data, not just liveness: sign in, confirm the project count on the overview matches
expectation, and download one CSV. A healthy process in front of an empty database is not a
successful restore.

If the restore predates a migration, run `python -m alembic upgrade head` before starting the API.

## Verified run

The file-level restore was exercised on 2 November 2026 against a temporary SQLite database with
two tables and three rows:

```
rows_after_delete=0
rows_after_restore=projects:2 evidence:1
integrity_check=ok
BACKUP_RESTORE_VERIFIED
```

The script copies the database, deletes every row, restores the copy, then re-counts rows and runs
`PRAGMA integrity_check`. It verifies schema and data return, not merely that a file exists.

This does **not** prove the Docker volume commands above: the Docker daemon was unavailable in
that environment. Those commands follow the documented volume name and should be rehearsed once
on the target host.

## Recovery targets

| Scenario | Target | Reality in this release |
| --- | --- | --- |
| Restore last good database | Under 15 minutes | Achievable with the procedure above; one operator, two commands |
| Point-in-time recovery | Not supported | Only snapshots taken by the operator |
| Backup retention | Not automated | The operator decides; no scheduled job exists |
| Restore drill | Quarterly | Not yet scheduled |

## What is not covered

- No automated, scheduled backup job ships with the project.
- No off-site replication or encryption at rest.
- No restore test in CI.
- Losing the database without a backup loses all research records: there is no event-sourcing or
  external copy.

Treat automated, encrypted, off-site backups as a production prerequisite (`security.md`).
