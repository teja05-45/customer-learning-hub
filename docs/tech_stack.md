# Tech Stack

Versions are pinned or locked in the repository. Verify with `backend/requirements.txt` and
`frontend/package-lock.json`.

## Backend

| Technology | Version | Role |
| --- | --- | --- |
| Python | 3.11+ (Docker uses 3.12) | Runtime |
| FastAPI | 0.115.6 | HTTP API, OpenAPI generation |
| Uvicorn | 0.34.0 | ASGI server |
| SQLAlchemy | 2.0.36 | ORM and query layer |
| Alembic | 1.14.0 | Schema migrations |
| Pydantic | 2.10.4 | Validation and contracts |
| pydantic-settings | 2.7.0 | Environment configuration |
| python-dotenv | 1.0.1 | `.env` loading |
| SQLite | bundled | Local and demo persistence |
| pytest | 8.3.4 | Backend test runner |
| pytest-cov | 6.0.0 | Coverage tooling |
| HTTPX | 0.28.1 | Test transport for FastAPI |

PostgreSQL compatibility comes from SQLAlchemy's portable types and Alembic; no PostgreSQL
driver is installed because the prototype does not require one.

## Frontend

| Technology | Version | Role |
| --- | --- | --- |
| React | 18.3.1 | UI runtime |
| TypeScript | 5.7.2 | Type safety |
| Vite | 6.0.5 | Dev server and build |
| React Router | 6.28.0 | Client routing |
| TanStack Query | 5.62.7 | Server-state caching |
| React Hook Form | 7.54.2 | Project creation form |
| Zod + hookform resolvers | 3.24.1 / 3.9.1 | Schema validation |
| Bootstrap | 5.3.3 | Grid and base components |
| react-bootstrap | 2.10.5 | Modals |
| Recharts | 2.15.0 | Timeline, segment and funnel charts |
| Lucide React | 0.468.0 | Icons |
| Playwright | 1.64.1 | Browser integration tests |
| axe-core Playwright | 4.14.0 | Automated accessibility checks |

## Infrastructure

| Technology | Version | Role |
| --- | --- | --- |
| Docker | 29.x (verified locally) | Container runtime |
| Docker Compose | v5.x | Two-service local stack |
| nginx | 1.27-alpine | Static hosting and `/api` reverse proxy |
| Node | 20-alpine (build image) | Frontend build stage |

## Deliberate omissions

| Not used | Reason |
| --- | --- |
| Microservices / message broker | No independent scaling or team boundary |
| Redis / Celery | No background workload in scope |
| Auth provider | Demo identity only; documented as the first production prerequisite |
| Embeddings / vector search | Keyword search is explainable and sufficient at this volume |
| Charting/design system beyond Bootstrap | Existing identity retained; no redesign needed |
| ORM async stack | SQLite + sync SQLAlchemy is simpler and adequate for the prototype |

## Compatibility notes

- Docker publishes the web app on host port **8081** because 8080 is often occupied; the
  container listens on 8080.
- The Vite dev server proxies `/api` to `http://127.0.0.1:8000`, so development needs no CORS.
- Recharts requires a fixed-height container; charts are wrapped in explicit-height divs.
