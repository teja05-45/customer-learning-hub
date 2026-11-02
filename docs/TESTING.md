# Testing

All test data is synthetic. Tests use the real HTTP surface and a real temporary SQLite
database; services are not mocked.

## How to run

```powershell
# Backend (from backend/, with the virtual environment created)
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing

# Frontend (from frontend/)
npm run typecheck
npm run build
npx playwright test

# Playwright against the Docker build
$env:E2E_BASE_URL="http://localhost:8081"; npx playwright test
```

The Playwright suite expects the API at `http://127.0.0.1:8000/api/v1` (override with
`E2E_API_URL`) and the web app at `http://localhost:5173` by default.

## Backend suites

| File | Coverage |
| --- | --- |
| `tests/test_api.py` | Health, derived dashboard numbers, project CRUD/validation, 404 envelope, participant data minimisation, recruitment transitions, consent gate, evidence provenance, insight validation, decisions, actions, search, analytics labels, CSV export, demo reset, demo session |
| `tests/test_workflow.py` | Question → project → participant → recruitment → interview → evidence → insight → decision → action → find it again |
| `tests/test_journey.py` | The full 22-step journey with four segments, contradictions, validation, decision limits, action lifecycle, metric agreement, search navigation and cross-project rejection |
| `tests/test_metrics.py` | Dashboard/analytics agreement, counter movement on new records, overdue lifecycle, reuse definition, segment totals reconciling with the directory |
| `tests/test_pipeline.py` | Contacted/response-rate definitions, distinct-participant counting, interview-driven history events, stage-count/filter agreement, coverage derivation |
| `tests/test_integrity.py` | Database constraints, link uniqueness, sufficiency recomputation, archive behaviour |

Final verified result: **42 passed** (`pytest -q`, one third-party Starlette deprecation
warning, no failures).

## Frontend verification

- `tsc --noEmit` — clean.
- `vite build` — succeeds; one chunk-size advisory (single bundle ~988 kB, ~270 kB gzip).
  Code-splitting is a listed improvement, not a failure.
- Playwright:
  - `smoke.spec.ts` — every primary screen renders with real data, no console errors, deep
    links, unknown route, API failure state, keyboard skip link, command-palette focus trap.
  - `a11y.spec.ts` — axe scan of every primary screen and the palette; fails on serious or
    critical WCAG 2.1 A/AA violations.
  - `journey.spec.ts` — executes the full research-to-decision workflow and verifies it in the
    UI, including insight editing, evidence review/provenance correction and search navigation.
  - `screenshots.spec.ts` — captures documentation screenshots.

Final verified result: **7 passed** (`npx playwright test`).

## What is deliberately not covered

- No component-level unit tests (the browser suite covers navigation, forms, filters, modals,
  loading, empty and error states).
- No load or performance testing; volumes are prototype-scale.
- No penetration testing; there is no authentication to test.
- No automated visual-regression snapshots; screenshots are for documentation.

## Test data policy

Every fixture is synthetic. The demo reset endpoint restores a known dataset, so a Playwright
run does not depend on previous state. Backend tests share a session-scoped database by design
and use before/after deltas where order could matter; the dedicated journey test resets first.

## Failure triage

1. Re-run the failing test alone to distinguish state leakage from a real defect.
2. Inspect the API response and the request id in the server log.
3. For Playwright, open the retained trace: `npx playwright show-trace <trace.zip>`.
4. Fix the cause; do not relax assertions or skip tests.

See `11-testing.md` for the original strategy discussion.
