# Testing

Two layers, both runnable in under a minute: a pytest suite for API behaviour and a Playwright
suite for the real interface against a real backend. There is no mocking layer anywhere, so a
broken contract fails a test instead of hiding behind a stub.

## Running

```bash
# Backend — 21 tests
cd backend && .venv/Scripts/python -m pytest -q

# Frontend types and production bundle
cd frontend && npm run typecheck && npm run build

# End-to-end (needs the API on :8000 and the web app on :5173, or set E2E_BASE_URL)
cd frontend && npx playwright test

# End-to-end against the Docker build
cd frontend && E2E_BASE_URL=http://localhost:8081 npx playwright test e2e/smoke.spec.ts
```

## Backend suite

`backend/tests/conftest.py` builds a fresh SQLite database per test session from the models,
seeds the same deterministic dataset the app uses, and overrides the FastAPI dependency so
tests never touch `data/clh.db`.

| Test | What it protects |
| --- | --- |
| `test_health_reports_ok` | Health endpoint reports database and seed state |
| `test_dashboard_numbers_are_derived_not_hardcoded` | Dashboard counts match the records they claim to count |
| `test_project_create_and_read` | Round-trip create/get, codes and defaults |
| `test_project_validation_rejects_bad_dates_and_short_names` | 422 envelope with per-field details |
| `test_unknown_ids_return_404_envelope` | Every resource returns the same error shape |
| `test_participant_creation_never_stores_contact_details` | A payload with `email`/`phone` is rejected or ignored; no contact column exists |
| `test_recruitment_transitions_and_history` | Illegal stage jumps rejected; legal ones append an event |
| `test_recruitment_reports_segment_gap` | Pipeline reports where segment coverage is missing |
| `test_interview_lifecycle_and_recording_consent_gate` | Recording cannot be enabled without granted recording consent |
| `test_evidence_without_provenance_is_flagged` | Missing provenance surfaces as `missing`, not silently accepted |
| `test_evidence_with_provenance_is_verified` | Provenance recorded ⇒ status `recorded` |
| `test_insight_requires_evidence_before_validation` | An insight cannot be validated with no evidence linked |
| `test_decision_without_evidence_is_warned_not_hidden` | Decision with no source is accepted **and** flagged |
| `test_decision_links_and_action_creation` | Links and actions round-trip through the decision |
| `test_decision_status_transitions_are_validated` | Decision lifecycle is enforced |
| `test_search_finds_insight_and_related_work` | Search returns grouped, typed results |
| `test_analytics_labels_metric_basis` | Every metric carries whether it is calculated or pending baseline |
| `test_csv_export_is_labelled_synthetic` | `is_synthetic=true` and `exported_at` present on every row |
| `test_demo_reset_requires_confirmation_phrase` | Reset refuses without `confirm` + `RESET` |
| `test_session_is_labelled_as_demo_not_authentication` | The session payload states it is not auth |
| `test_full_research_to_decision_journey` | Project → participant → recruitment → interview → evidence → insight → decision → action, end to end |

The last test is the important one: it walks the entire product promise in a single flow and
asserts the chain stays connected at every hop.

## Frontend end-to-end

| Spec | Covers |
| --- | --- |
| `e2e/smoke.spec.ts` | All ten primary screens render with real data, no console errors, no horizontal scroll; deep links work; unknown routes render the not-found screen; a failed dashboard request shows an error state with a retry; the skip link takes the first Tab, the command palette traps Tab and restores focus on Escape |
| `e2e/screenshots.spec.ts` | Captures the 18 documentation screenshots, desktop and mobile |
| `e2e/helpers.ts` | Shared reset + role entry helpers, plus the overflow assertion |

The suite resets the demo dataset before each test, so runs are repeatable and independent of
whatever the previous reviewer clicked.

### What the smoke test proves about the delivered artifact

It runs through the same nginx-served production bundle a reviewer uses, not the dev server:
`E2E_BASE_URL=http://localhost:8081` points it at the Docker stack. In that configuration the
API is reached over the nginx proxy, so the test also exercises the proxy rules and the SPA
fallback.

## What is not covered

| Gap | Why | Risk |
| --- | --- | --- |
| No unit tests for React components | The value here is the flow, and the flow is covered end to end | A component logic bug is caught late |
| No authentication tests | There is no authentication | N/A until AUTH.md is implemented |
| No load or performance test | Prototype dataset is ~70 records | Unknown behaviour beyond a few thousand records |
| No PostgreSQL matrix | SQLite is the configured default; alembic migration is written but CI does not run both | JSON columns and `nulls_last()` ordering are the likely differences |
| No visual regression diffing | Screenshots are documentation, not assertions | Styling regressions are caught by eye |
| No mobile interaction tests beyond the overflow assertion | Sidebar drawer behaviour is untested | Small |
| No accessibility automation (axe) | Manual review only; see [14-accessibility.md](14-accessibility.md) | Moderate — contrast and labels were fixed by hand |

## Manual checks performed

- Every screen at 1440×960 and 390×844 in Chromium, with no horizontal scroll and no console
  error.
- Keyboard-only pass through the shell: nav, search dialog (open with `Ctrl/⌘+K`, `Esc` to
  close, focus restored), forms, and modal dialogs.
- Demo reset twice in a row, confirming the dataset returns to identical counts.
- Docker build from a clean volume: first start seeds, second start does not duplicate.
- CSV download opened in a spreadsheet to confirm the `is_synthetic` column.

## Continuous integration (not configured)

A working CI job would be:

```yaml
- run: cd backend && pip install -r requirements.txt && pytest -q
- run: cd frontend && npm ci && npm run typecheck && npm run build
- run: docker compose up -d --build && cd frontend && E2E_BASE_URL=http://localhost:8081 npx playwright test e2e/smoke.spec.ts
```

It is documented rather than committed because this prototype has no remote pipeline; adding
one that nobody watches would be decoration.
