# Performance

## Measurement

Taken on 2 November 2026 on the development machine (Windows, Python 3.11.9), through the real
FastAPI application against a freshly seeded temporary SQLite database, using Starlette's
in-process `TestClient` to remove network and browser noise. Thirty sequential requests per
endpoint after a warm-up login; timings include session resolution, query work and JSON/CSV
serialisation.

| Endpoint | Median | p95 | Max |
| --- | --- | --- | --- |
| `GET /api/v1/projects?page_size=20` | 33.4 ms | 53.3 ms | 58.4 ms |
| `GET /api/v1/dashboard` | 84.7 ms | 111.5 ms | 124.0 ms |
| `GET /api/v1/analytics` | 40.3 ms | 51.6 ms | 74.0 ms |
| `GET /api/v1/search?q=shampoo` | 25.1 ms | 33.4 ms | 37.8 ms |
| `GET /api/v1/exports/participants.csv` | 22.5 ms | 25.7 ms | 26.7 ms |

Dataset at measurement time: 5 projects, 10 participants, 14 recruitment records, 11 interviews,
~20 evidence rows, 4 insights, 4 decisions, 5 actions, 7 users.

## What this does and does not tell you

- It is a **local, single-user measurement**, not a load test. There is no concurrency, no TLS, no
  proxy and no browser rendering in these numbers.
- The dashboard is the slowest endpoint because it derives several aggregates in sequence (counts,
  timeline, segment coverage, outstanding actions, recent activity). That is the first place to
  optimise if it becomes a problem.
- No caching is used. Every request recomputes from the database, which is the correct default for
  a tool where a stale metric is worse than a slow one.
- No performance regression is asserted in CI. Adding a benchmark job would be the way to make
  these numbers meaningful over time.

## Known scaling characteristics

| Concern | Current behaviour | Implication |
| --- | --- | --- |
| Database | SQLite, single writer | Fine for a small team; PostgreSQL is the deployment path (`database.md`) |
| List endpoints | Some load all rows then filter/paginate in memory | Acceptable at prototype scale; add SQL pagination before large datasets |
| Search | Deterministic `ILIKE`-style matching across seven entity types | No index-assisted full-text search; volumes are small |
| Exports | Full table scan into memory, then one CSV response | Stream or page exports for very large tables |
| Sessions | One indexed lookup per request, plus a write to `last_seen_at` | Every request performs a small write; a read-only cache or throttled touch would reduce write contention |
| Frontend | Single bundle (~1 MB, ~270 kB gzip) | First load is heavier than needed; route-level code splitting is the obvious win |
| Background work | None | No queues, workers or scheduled jobs; retention is not automated |

## Reproducing the measurement

The benchmark is a short script rather than a committed harness: seed a temporary database, sign
in, then time 30 sequential requests to each endpoint. It asserts `200` on every call, so a
broken response is a failed measurement rather than a fast one.
