# Operations Runbook

> **Status (2 November 2026).** This document is retained as the original discovery record.
> Password authentication, server-side sessions and API-enforced roles are now implemented;
> statements below that the API has no authentication, or that `X-Demo-User-Id` grants
> identity, no longer describe the code. See [auth.md](auth.md) and [security.md](security.md).

## Daily checks

```powershell
curl http://localhost:8000/api/v1/health
docker compose ps
docker compose logs --tail=50 backend
```

Healthy means `status: ok`, `database: ok`, `seeded: true`, and both containers report
`(healthy)`. The API health check runs every 15 seconds inside the container.

## Logs

```powershell
docker compose logs -f backend
docker compose logs -f frontend
```

Logs are structured at `INFO` by default and exclude participant names, evidence text and
contact routes. Raise verbosity with `LOG_LEVEL=DEBUG` for a local investigation only, and
avoid leaving it on: request logs may then include more context than a demo should retain.

## Data lifecycle

| Action | Command | Effect |
| --- | --- | --- |
| Keep data, stop | `docker compose down` | Volume `clh-data` preserved |
| Wipe demo data | `docker compose down -v` | Volume deleted; next start reseeds |
| Reset while running | `POST /api/v1/demo/reset {"confirm":true,"phrase":"RESET"}` | Rebuilds the synthetic dataset |
| Backup | `docker run --rm -v clh-data:/data -v ${PWD}:/backup alpine tar czf /backup/clh-backup.tgz -C /data .` | Copies the SQLite file |
| Restore | Reverse the backup into the volume, then restart | Verify health and counts after |

All data is synthetic; a backup contains no real customer information.

## Common incidents

| Symptom | Diagnosis | Response |
| --- | --- | --- |
| Web shows API unreachable | `docker compose ps`; API unhealthy | Check logs, database path and volume permissions; restart |
| Dashboard numbers frozen | Seed or query failure | Check health `seeded`; query `/dashboard` directly; look for a 500 in logs |
| Stage change rejected | Business rule, not an outage | Read `details.allowed` in the response; move through a valid stage |
| Recording toggle rejected | No granted recording consent | Record consent first; this is intended |
| Disk growth | Old volumes/backups | `docker system df`; prune only after confirming no data is needed |
| Port 8000 already in use | Local Uvicorn or another service | Stop the other process or change the host port mapping |

## Deployment and rollback

1. Build images with a version tag; keep the previous tag available.
2. Run migrations before starting the new API (`alembic upgrade head` when using Alembic).
3. Start the new stack, wait for `healthy`, run the browser smoke suite against the new base URL.
4. If the smoke suite fails, stop the new stack and start the previous image against the same
   volume; no destructive migration is used in this prototype.
5. Announce the rollback with the failing check and the image tag.

## Monitoring (minimum for a hosted demo)

- HTTP health endpoint polled every minute, alert after three failures.
- Error rate from the reverse proxy; alert on sustained 5xx.
- Disk usage of the database volume.
- Business signal worth watching weekly: share of decisions with a linked customer source, and
  overdue follow-ups. These indicate adoption, not just uptime.

## Access and secrets

- Do not commit `.env`; it is excluded from Git and from the Docker build context.
- Rotate any credential immediately if it is ever pasted into a shared document or log.
- There is no authentication in this prototype. If hosted, put basic auth at the proxy and do
  not store anything beyond synthetic data.

## Handover checklist

- [ ] Compose stack starts from clean on the customer machine.
- [ ] Health, web and proxy endpoints verified.
- [ ] Demo reset demonstrated.
- [ ] Logs and backup locations known to the owner.
- [ ] Known limitations restated: no auth, no real outreach, no audio, SQLite single-writer.
