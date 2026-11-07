# Final submission audit

Audit date: 7 November 2026 · Branch: `main` · Base commit: `6bfbe62`
Authoritative release report. Supersedes the status statements in `final-delivery-report.md` where
they differ (that document is retained as the first-pass record).

## 1. Verdict

The submission is coherent and runnable, and the critical security gap from the first audit is
closed. A workspace role now answers *what kind of work* a person may do; a project membership answers
*which project* they may do it in. Both gates are enforced by the API, not by hidden buttons.

| Area | Status |
| --- | --- |
| Project-level authorization (IDOR/BOLA) | **Implemented, migrated, tested** |
| Nine business workflows | Verified through API and/or browser |
| Notion-inspired visual system | Applied through `notion.css` (approved tokens, Inter) |
| Data preservation | Additive migration; no resets, drops or volume deletion |
| Documentation set | Updated/added; see §9 |
| Git | Local commits created; **not pushed** (awaiting approval) |

## 2. What was actually executed

| Check | Command | Result |
| --- | --- | --- |
| Backend suite | `cd backend && ./.venv/Scripts/python.exe -m pytest -q` | **138 passed**, 1 deprecation warning, 0 failed/skipped, 274.31 s |
| Authorization suite | `pytest tests/test_project_authorization.py -q` | **16 passed** |
| Authorization + outcomes | `pytest tests/test_project_authorization.py tests/test_outcomes.py -q` | **25 passed** |
| TypeScript | `cd frontend && npx tsc --noEmit` | exit 0 |
| Production build | `cd frontend && npm run build` | exit 0; entry 264.31 kB (82.45 kB gzip) |
| Browser suite | `cd frontend && npx playwright test` against live API + Vite | **24 passed**, 3.6 min |
| Browser smoke | `npx playwright test e2e/smoke.spec.ts` | 3 passed |
| Migration cycle | fresh `upgrade → downgrade -1 → upgrade` on a temporary DB | passed |
| Backfill on a copy of seeded QA data | `alembic upgrade head` | 15 memberships (10 owner, 5 editor), 0 admins/owners missing |
| Data integrity | copy deleted afterwards; working DB untouched | confirmed |

Environment: Python 3.11 / FastAPI 0.115 / SQLAlchemy 2.0 / SQLite, Node 24 / Vite 6 / Playwright
1.64 Chromium. Tests ran on Windows 11 in Git Bash. The browser suite ran against a live local stack
(API `:8000`, Vite `:5173`), not only a static build.

## 3. The authorization fix

### Model

- `ProjectMembership(project_id, user_id, role, created_at, granted_by_id)` with a unique
  `(project_id, user_id)` and a `(user_id, project_id)` index.
- `ProjectRole`: `viewer < editor < project_owner`.
- Workspace `admin` is an implicit `project_owner` on every project.
- Effective permission = workspace-role gate **∩** project-membership gate.

### Enforcement

`backend/app/services/access.py` is the single place that answers "may this user act on this project,
at what level?". Every project-scoped endpoint calls `assert_project_read`, `assert_project_write` or
`assert_project_manage`; list-style reads use `visible_project_ids`. That scoping now covers:

- project lists, project detail and journey;
- participants (derived from the studies they appear in), recruitment, interviews, evidence, feedback,
  insights, decisions, actions, outcomes;
- dashboard counts, analytics bases, global search and CSV exports;
- membership administration, with last-owner protection.

Orphan decisions/insights (no project yet) are readable/writable only by their owner or an admin; they
adopt a project when linked, and cross-project links are rejected.

### Migration

`d4e8f1a2c7b9_project_membership.py` (down_revision `c8e3a1d5f204`) is additive. Backfill is
least-privilege: project owner → `project_owner`; active admins → `project_owner` on all projects;
demonstrable contributors (interviewer, evidence capturer, feedback creator, insight/decision/outcome
owner) → `editor`; nobody else. It deliberately does not grant everyone everything.

### Proof

`backend/tests/test_project_authorization.py` — 16 HTTP tests (real sessions, seven seeded users)
covering direct reads, nested records, aggregates, exports, search, cross-project links, viewer
writes, researcher admin attempts, owner-only membership management, immediate revocation and
unauthenticated requests. Full design: `docs/authorization-and-permissions.md`.

## 4. Business workflow validation

The chain — project → discovery → recruitment → consent → session/feedback → evidence → insight →
decision → action → outcome — was exercised. Highlights:

- **Consent withdrawal** cancels future sessions, blocks re-booking, flags the participant, writes
  audit events, and retains prior lawful evidence (4 backend tests + browser journey).
- **Outcomes** are derived: pending without a result; achieved/not achieved/inconclusive from actual,
  target and direction; a measured status without a result is rejected (9 backend tests + browser).
- **Journey** board/timeline derives nine stages and date states from real records (service tests +
  browser).
- **Traceability** survives survey → evidence → insight → decision, including contradictory and
  contextual-only evidence (browser traceability suite).
- **Exports** parse for every CSV, are formula-injection safe and are scoped to visible projects.

Per-workflow evidence: `docs/business-workflows.md` and `docs/workflow-validation-matrix.md`.

## 5. Design

`frontend/src/styles/notion.css` is loaded last and implements the approved tokens: `#FFFFFF`,
`#F7F7F5`, `#252525`, `#787774`, `#E9E9E7`, `#347A69`, `#7565B5`, `#F1F1EF`, Inter typography.
Screenshots in `docs/screenshots/` were regenerated from the running app during this pass (the
screenshot suite passed). Project-aware UI additions: switcher with access label, role pill,
read-only state, access-denied page, Members tab for owners. The frontend hides controls a role cannot
use but is not the security boundary. Design reference: `docs/08-design-system.md`.

## 6. Defects

- Closed: QA-01…QA-10, QA-12…QA-15 (including the consent/outcome/journey work and the authorization
  gap). Details: `docs/final-debug-register.md`.
- Found during this pass: a demo-reset regression caused by narrowing `/settings` and `/demo` together
  (fixed by splitting the middleware rule; smoke re-run green), and a business-owner membership-write
  denial caused by a missing middleware prefix (fixed; owner-only authorization remains in the
  service).
- Open and disclosed: unindexed leading-wildcard search (measured at 50k rows), membership
  role-change/removal audit gaps, stale frontend role after revocation until reload, no frontend unit
  tests, no retention automation.

## 7. Test-expectation changes (not weakened assertions)

Three browser tests assumed workspace-wide access and failed after the boundary landed:

1. the full journey created a decision as a business owner with no grant on the newly created project
   → the test now grants that owner `editor` membership through the real API and asserts `201`;
2. the outcome workflow signed in as a user who cannot see the shampoo study → changed to an
   administrator (implicit owner), which is the correct actor;
3. the screenshot suite clicked Settings while signed in as a read-only CEO → now takes that one
   screenshot with an administrator session and restores the CEO session.

No server rule was relaxed and no assertion was removed to make these pass.

## 8. Data preservation

- The only schema change is additive; no destructive operations.
- The migration and backfill were exercised on a **copy** of the seeded QA database; the copy was
  deleted.
- Demo reset only runs when the three demo flags are enabled; Docker volumes are not deleted.
- Backend tests use a temporary database fixture, not the demo file.

## 9. Documentation map

| Requirement | Document |
| --- | --- |
| This audit | `final-submission-audit.md` |
| Architecture | `architecture.md`, `07-frontend-architecture.md` |
| Business workflows | `business-workflows.md`, `workflow-validation-matrix.md` |
| Authorization | `authorization-and-permissions.md`, `auth.md`, `13-security-and-privacy.md` |
| Database and migrations | `database-and-migrations.md`, `05-data-model.md`, `data_dictionary.md` |
| API | `06-api-reference.md`, `api.md` |
| Design system | `08-design-system.md`, `design.md` |
| Defects | `final-debug-register.md`, `bug-fix-register.md` |
| QA baseline | `final-qa-baseline.md`, `testing.md` |
| Delivery | `final-delivery-report.md` (first pass), this document (release) |
| Recruiter evaluation | `final-recruiter-evaluation.md` (re-scored 86/100) |
| Interview explanation | `PROJECT-WORKFLOW-EXPLANATION.md` |
| Changelog | `changelog.md` 1.8.0 |

## 10. Honest limitations

1. **Admin bypass.** Administrators own every project implicitly. This is not tenant isolation.
2. **No retention automation.** Withdrawal stops contact but does not erase prior evidence; that is a
   policy decision left open.
3. **Search.** Leading-wildcard `LIKE` is unindexed; correct at demo size, measured at 50k rows.
4. **Frontend tests.** Playwright only; no unit/component runner.
5. **Integrations.** No real outreach, audio capture, commerce or support connection.
6. **Deployment.** No hosted deployment was performed or claimed.
7. **Migration scope.** Backfill rules are validated on synthetic data, not a real customer database.

## 11. Git and release

Local commits group the work into backend authorization, frontend, tests and documentation. The
repository was **not pushed**: the task requires explicit approval before changing remote history. No
force-push, tag or release was created.

## 12. Reproduce

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest -q          # 138 passed
cd frontend && npx tsc --noEmit && npm run build               # clean
# with API on :8000 and Vite on :5173:
cd frontend && npx playwright test                             # 24 passed
```
