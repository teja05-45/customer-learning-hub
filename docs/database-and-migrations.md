# Database and migrations

Engine: SQLite for local development, tests and the default Docker volume. SQLAlchemy 2.0 models,
Alembic migrations. No production database is claimed or connected.

## 1. Schema overview

| Domain | Tables |
| --- | --- |
| Identity | `users`, `sessions` |
| Workspace | `workspace_settings`, `activity` |
| Research | `research_projects`, `project_questions`, `project_memberships` |
| Customers | `participants`, `recruitment_records`, `recruitment_stage_history` |
| Sessions | `interviews`, `interview_questions`, `consent_records` |
| Feedback | `feedback_records` |
| Evidence & insight | `evidence`, `insights`, `insight_evidence` |
| Decisions | `decisions`, `decision_insights`, `business_actions` |
| Measurement | `outcomes` |

Every primary key is a UUID string. Timestamps are UTC. Statuses and roles are stored as text and
validated by enums at the API boundary, so a new value does not require rewriting a table.

### Project membership (new)

```
project_memberships
  id             varchar(36)  PK
  project_id     varchar(36)  FK research_projects.id  ON DELETE CASCADE  indexed
  user_id        varchar(36)  FK users.id              ON DELETE CASCADE  indexed
  role           varchar(24)  viewer | editor | project_owner
  created_at     datetime     not null
  granted_by_id  varchar(36)  FK users.id  ON DELETE SET NULL, nullable
  UNIQUE (project_id, user_id)  -- uq_project_membership
  INDEX  (user_id, project_id)  -- ix_project_memberships_user_project
```

The composite index serves the two hot queries: "projects this user can see" and "can this user act on
this project". The unique constraint makes grants idempotent.

## 2. Migration chain

| Revision | Purpose |
| --- | --- |
| `c8e3a1d5f204` | Outcome measurement (`outcomes`) |
| `d4e8f1a2c7b9` | Project membership (`project_memberships`) — **head** |

`d4e8f1a2c7b9` is **additive**: it creates a table and indexes. It does not alter or delete any
existing column or row. It can be rolled back by dropping the membership table, which returns the
application to workspace-wide reads — that is a security regression, so downgrade is for development
only.

## 3. Backfill (deterministic, least privilege)

The migration grants:

1. each project's `owner_id` → `project_owner`;
2. every **active** workspace admin (`role='admin' AND is_active=1`) → `project_owner` on every
   project;
3. demonstrable contributors → `editor` on the project(s) where they already worked:
   `interviews.interviewer_id`, `evidence.captured_by_id`, `feedback_records.created_by_id`,
   `insights.owner_id`, `decisions.owner_id` (only where a project exists), and
   `outcomes.owner_id` via its decision's project;
4. nobody else.

Duplicate (project, user) pairs are collapsed, with the first row winning (owner/admin before
contributor). Insertion is done with parameterized SQL in batches, using generated UUIDs.

It deliberately does **not** grant every existing user access to every project. That would leave the
original vulnerability in place under a new table name. Users who relied on workspace-wide reading must
be granted membership by a project owner.

## 4. Verification performed

Commands were run from `backend/` with a temporary SQLite database:

```bash
DATABASE_URL="sqlite:///./data/migration_check.db" \
  ./.venv/Scripts/python.exe -m alembic upgrade head
DATABASE_URL="sqlite:///./data/migration_check.db" \
  ./.venv/Scripts/python.exe -m alembic downgrade -1
DATABASE_URL="sqlite:///./data/migration_check.db" \
  ./.venv/Scripts/python.exe -m alembic upgrade head
```

Results:

| Check | Result |
| --- | --- |
| Fresh upgrade → downgrade → upgrade | passed; table and indexes recreate cleanly |
| Upgrade on a copy of the seeded QA database | passed; no data loss |
| Memberships created on that copy | **15** — 10 `project_owner`, 5 `editor` |
| Active admins without a membership | **0** |
| Project owners without a membership | **0** |
| Temporary database | deleted after verification |

The real `data/qa.db` had no `alembic_version` row, so the copy was stamped at `c8e3a1d5f204` before
upgrading. The working database was not modified by this check.

## 5. Data preservation rules

- No `DROP TABLE`, no column removal, no destructive `ALTER`, no data reset in the migration.
- The seed script is the only code that wipes demo data, and it only runs when explicitly enabled
  (`SEED_ON_STARTUP` + `SEED_DEMO_DATA` + `DEMO_MODE`). It deletes in dependency order and now includes
  `ProjectMembership`.
- Docker volumes are never deleted by the application or by the documented commands.
- `TEST` databases are temporary files created by the test fixture; they are not the demo database.

## 6. Application startup

`init_db()` creates missing tables for a fresh development database, then runs the seed when enabled.
Alembic remains the source of truth for an existing database. In a production-like deployment, run
`alembic upgrade head` before starting the API rather than relying on `create_all`.

## 7. Seed memberships

The demo seed creates an intentionally uneven team so the boundary is demonstrable:

| User | Workspace role | Project grants |
| --- | --- | --- |
| Arjun | admin | implicit owner everywhere |
| Priya | researcher | editor on every project; owner of the shampoo study |
| Dev | business_owner | owner: routine campaign, packaging; editor: body wash |
| Nisha | business_owner | owner: body wash; editor: routine campaign |
| Rohan | business_owner | owner: first-to-second; editor: routine; viewer: packaging; **no access** to shampoo or body wash |
| Vikram | cx | editor: shampoo; viewer: first-to-second |
| Asha | ceo | viewer on every project |

## 8. Operational commands

```bash
cd backend

# apply migrations
./.venv/Scripts/python.exe -m alembic upgrade head

# inspect current revision
./.venv/Scripts/python.exe -m alembic current

# roll back one revision (development only)
./.venv/Scripts/python.exe -m alembic downgrade -1

# seed manually (only with demo flags enabled)
DEMO_MODE=true SEED_ON_STARTUP=true SEED_DEMO_DATA=true \
  ./.venv/Scripts/python.exe -m app.seed
```

## 9. Backup and recovery

SQLite is a single file. Stop the API (or use SQLite's online backup) before copying it; the Docker
volume is `clh-data`. `docs/backup_recovery.md` describes the procedure. A restore must be followed by
`alembic upgrade head` so the membership table exists; without it the application fails closed (no one
has a grant) rather than silently reverting to workspace-wide reads.

## 10. Known limits

- SQLite does not enforce foreign keys unless `PRAGMA foreign_keys=ON`; the application sets it for the
  test/development engine. A PostgreSQL deployment should rely on real FKs and add row-level security
  only if tenancy moves into the database.
- There is no migration for a real customer dataset; the backfill rules are the documented mapping.
- No database-level audit table exists; activity/audit events are application rows.
