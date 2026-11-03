# Testing

All test data is synthetic. Tests use the real HTTP surface and a real temporary SQLite
database; services are not mocked.

## How to run

```bash
# Backend (from backend/)
python -m pytest -q

# Frontend (from frontend/)
npm run typecheck
npm run build
npx playwright test
```

The Playwright suite expects the API at `http://127.0.0.1:8000/api/v1` (override with
`E2E_API_URL`) and the web app at `http://localhost:5173`, or `E2E_BASE_URL` for the Docker build.

## Backend suites

| File | Coverage |
| --- | --- |
| `tests/test_api.py` | Health, derived dashboard numbers, project CRUD/validation, 404 envelope, participant data minimisation, recruitment transitions, consent gate, evidence provenance, insight validation, decisions, actions, search, analytics labels, CSV export, demo reset, demo directory |
| `tests/test_auth.py` | Anonymous requests rejected, password login/logout, cookie flags, role enforcement on writes, demo entry gated by demo mode, client-supplied identity header ignored, first-run registration, password change revoking other sessions |
| `tests/test_security.py` | Failed-sign-in throttling and `Retry-After`, counter cleared by a successful login, per-account isolation, cross-site writes rejected (`Origin`, `Referer`, `Origin: null`), trusted and same-host origins accepted, reads unaffected, administrator account creation/role change/deactivation/password reset, and the last-administrator guard |
| `tests/test_exports.py` | All eight CSV exports, non-administrator export (the "Export failed" regression), anonymous rejection, sensitive-column exclusion, Unicode, header-only empty dataset, audit entry, unknown-entity error |
| `tests/test_workflow.py` | Question → project → participant → recruitment → interview → evidence → insight → decision → action → find it again |
| `tests/test_journey.py` | The full journey with four segments, contradictions, validation, decision limits, action lifecycle, metric agreement, search navigation and cross-project rejection |
| `tests/test_metrics.py` | Dashboard/analytics agreement, counter movement on new records, overdue lifecycle, reuse definition, segment totals reconciling with the directory |
| `tests/test_pipeline.py` | Contacted/response-rate definitions, distinct-participant counting, interview-driven history events, stage-count/filter agreement, coverage derivation |
| `tests/test_integrity.py` | Formula-injection neutralisation, settings persistence, link uniqueness, sufficiency recomputation, unlink audit trail |
| `tests/test_seed.py` | Demo reset repeatability, unique generated codes, synthetic labelling, provenance mix |
| `tests/test_feedback.py` | Statement and interpretation kept separate, survey depth labelled as limited, unattributed sources allowed and marked, verified sources require a reference, interview/project matching, source-type/interview mismatch, CX role rejection, filtering and review, audited deletion, CSV content preservation |
| `tests/test_traceability.py` | Feedback-derived evidence is verbatim and snapshotted; unverified/unattributed labelling; three classifications and grouped reads; one evidence across several insights; re-classification leaves the statement untouched; feedback edits do not rewrite derived evidence; duplicates, invalid values, missing records; cross-project rejection and the explicit cross-project workflow; audited unlink with both identifiers; quality counts and unsubstantiated state; decision chain; traceability export provenance and uniqueness; role enforcement; atomic insight creation |
| `tests/test_migrations.py` | Alembic upgrade on a real file, column presence, a full downgrade to the previous revision, re-upgrade, and preservation of existing link and evidence rows |
| `tests/test_schema_upgrade.py` | A legacy database without the traceability columns gains them through the compatibility guard, is idempotent on a second run, and keeps every row |

## Actual results

Executed on 3 November 2026 against the working tree of this release:

```
cd backend && python -m pytest -q
108 passed, 1 warning in 73.91s
```

The warning is a third-party Starlette/anyio deprecation notice, not a project failure.

```
cd frontend && npm run typecheck     # exit 0, no output
cd frontend && npm run build         # exit 0, built in 5.70s
```

`vite build` reports one chunk-size advisory (single ~1 MB bundle). Code-splitting is a listed
improvement, not a failure.

### Test isolation

`tests/conftest.py` points `DATABASE_URL` at a temporary SQLite file created with
`tempfile.mkdtemp` and rebuilds the synthetic dataset with `seed_demo_data(reset=True)` for each
test that needs it. Nothing is written to `backend/data/clh.db`, and every participant the seed
creates carries `is_synthetic = true`. Participants created through the API are marked
`is_synthetic = false`, because the API path represents real records.

Authentication is exercised through the real login endpoint, so the tests also verify that the
cookie round-trips through Starlette's `TestClient`.

## Frontend verification

- `tsc --noEmit` — clean.
- `vite build` — succeeds with one chunk-size advisory (single ~1 MB bundle).
- Playwright specs: `smoke.spec.ts` (primary screens, deep links, unknown route, API failure
  state, skip link, command palette), `a11y.spec.ts` (axe scan of every primary screen, plus the
  insight page, evidence page and add-evidence dialog),
  `journey.spec.ts` (research-to-decision workflow), `exports.spec.ts` (all nine entity Settings
  downloads parsed as CSV), `traceability.spec.ts` (survey → evidence → insight; evidence ↔ insight
  ↔ decision; cross-project and role refusal; export and audited removal at four widths;
  context-only insight), `feedback.spec.ts` (record → verify → delete), `responsive.spec.ts`
  (375/768/1024/1440 plus the auth screen), `screenshots.spec.ts` (documentation captures).

```
cd frontend && npx playwright test
20 passed (1.9m)
```

The traceability export is verified twice: in `test_traceability.py` (headers, provenance,
classification, statement integrity, no duplicate pairs) and in `traceability.spec.ts`, which
downloads the file through the Settings button, parses it and checks the statement and rationale.

Against the Docker build (`E2E_BASE_URL=http://localhost:8081`), the smoke and traceability specs
were also executed:

```
npx playwright test e2e/smoke.spec.ts e2e/traceability.spec.ts
8 passed (27.5s)
```

Both servers were running for that run: FastAPI on `127.0.0.1:8000` and Vite on
`localhost:5173`. The API was started with `DEMO_MODE=true` because the browser helpers use the
demonstration entry; production defaults remain demo-off.

### Isolated API contexts

The journey and deep-link specs authenticate their API contexts explicitly. `X-Demo-User-Id` is
ignored by the server, and a browser cookie issued on `localhost:5173` is not sent to
`127.0.0.1:8000`; tests therefore use either a signed-in API context or a same-origin relative
request. Neither a header nor a cross-host cookie is treated as authentication.

### Redesign verification

The Executive Emerald redesign was checked by `responsive.spec.ts` at four widths, by axe on every
primary screen (no serious or critical violations) and by regenerating all screenshots. The first
axe run caught a real contrast failure in the sidebar section labels; the token was lightened to
`#B9CDC2` (≈6:1 on the chrome) and the suite was rerun green.

## What is deliberately not covered

- No component-level unit tests; the browser suite covers navigation, forms, filters, modals and
  states.
- The migration test runs on SQLite only. The migration is written for the generic Alembic API and
  PostgreSQL uses the same operations, but no PostgreSQL instance was available to execute it.
- The traceability export is not tested with a spreadsheet application; CSV correctness and
  formula neutralisation are tested at the file level.
- No load or performance testing; volumes are prototype-scale. `docs/performance.md` records the
  one measurement that was taken and how.
- No penetration testing. Authentication tests cover the enforcement path, not exploitation.
- No visual-regression snapshots.

## Failure triage

1. Re-run the failing test alone to distinguish state leakage from a real defect.
2. Inspect the API response and the server log.
3. If a session-related test fails with 401, check whether the test reset the dataset after
   signing in — a reset replaces every user, so the cookie is intentionally dead.
4. For Playwright, open the retained trace: `npx playwright show-trace <trace.zip>`.
5. Fix the cause; do not relax assertions or skip tests.
