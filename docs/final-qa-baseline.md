# Final QA baseline

Recorded before any code changes in this audit, then re-run after the fixes. Commands were executed
on Windows 11 in Git Bash against the repository at branch `main`, commit `6bfbe62`.

## Environment

| Component | Version |
| --- | --- |
| Python | 3.11.9 (backend virtualenv) |
| FastAPI / Pydantic / SQLAlchemy | 0.115.6 / 2.10.4 / 2.0.36 |
| SQLite (local dev and default Compose volume) | 3.45.1 |
| Node / npm | 24.12.0 / 11.6.2 |
| Docker / Compose | 29.6.1 / v5.3.0 |
| Browser | Playwright Chromium headless shell 156.0.8078.4 |

## Initial state — what the repository actually contained

| Check | Result |
| --- | --- |
| Branch / working tree | `main`, clean |
| Recent commits | Documentation and traceability work only. **No commit implements the claimed Notion-style redesign.** |
| Actual theme | "Executive Emerald": cream canvas `#F7F5EF`, dark green chrome `#103F32`, serif page titles |
| Claimed theme | White `#FFFFFF`, rail `#F7F7F5`, Inter, `#347A69` accent, `#7565B5` AI accent |
| Backend tests | `108 passed` (not the reported 120) |
| TypeScript | clean |
| Production build | successful, entry chunk `index-*.js` ≈ **1,011.67 kB** (large-chunk advisory) |
| Playwright | initially **20 failed** — all launches failed because the Chromium binary was absent, not because of application assertions |
| Browser installed? | No. `npx playwright install chromium` was required (118.1 MiB) |
| Docker images / containers / volumes | None existed before this audit |
| Demo dataset | synthetic: 7 users, 5 projects, 10 participants, 14 recruitment records, 11 interviews, 13 evidence items, 5 feedback sources, 4 insights, 4 decisions, 7 actions |

The delivery report's claims about the redesign, the 120 tests and the 21 passing browser tests were
therefore not reproducible. They are recorded as a documentation defect, not silently accepted.

## Baseline defects and gaps confirmed by inspection

| ID | Finding | Severity |
| --- | --- | --- |
| B-01 | Consent withdrawal had no backend consequence: no cancellation, no re-booking block, no participant contact flag | P0 |
| B-02 | Authorization is workspace-wide role-based; there is no project membership or cross-project data boundary | P0 — **resolved in the release pass** |
| B-03 | Outcome measurement did not exist (no model, API, UI or tests) | P0 |
| B-04 | Participant profile had no feedback history | P1 |
| B-05 | No learning-journey board or timeline | P1 |
| B-06 | Search uses `lower(column) LIKE '%term%'`, an unindexable scan | P2 |
| B-07 | Docker Compose never verified | P1 |
| B-08 | 1 MB entry bundle | P2 |
| B-09 | Approved Notion palette never applied | P1 |

## Post-fix results (same machine, same commands)

| Command | Result |
| --- | --- |
| `backend: .venv/Scripts/python.exe -m pytest -q` | **122 passed**, 1 deprecation warning, 0 skipped, ~150 s |
| `frontend: npm run typecheck` | clean, exit 0 |
| `frontend: npm run build` | clean. Entry `index-BvXVDkA9.js` 261.65 kB (81.70 kB gzip). Largest chunk `generateCategoricalChart-krqHXKvZ.js` 382.81 kB (105.76 kB gzip). No >500 kB warning. |
| `frontend: npx playwright test` (against Docker build on `:8081`) | **24 passed**, 0 failed, ~2.6 min |
| Axe | 13 primary screens + traceability/edit dialogs + command palette, 0 serious/critical violations |
| Responsive | 375 / 768 / 1024 / 1440 px, no page-level horizontal overflow |
| Docker Compose | both images built, both containers healthy, API/Web reachable, write survived backend restart |

## Browser and server errors observed

- Before installing Chromium: `browserType.launch: Executable doesn't exist ... chrome-headless-shell.exe` (environment blocker; resolved).
- During outcome testing: `PATCH /api/v1/outcomes/{id}` returned **400** with "The measurement end date cannot be before the start date." Root cause was reversed seed window dates, not the endpoint. Fixed in `backend/app/seed/demo_data.py`; regression test added.
- No 5xx responses and no backend tracebacks were found in the final suite or container logs.
- No uncaught JavaScript console errors were observed in the passing journeys. The suite does not install a global console-error listener, so this is observed behaviour rather than an exhaustive console audit.

## Release pass re-run (7 November 2026)

After project-level authorization, outcome/journey/consent work and the project-aware UI were added,
the same commands were executed again on the live local stack:

| Check | Result |
| --- | --- |
| Backend suite | **138 passed**, 1 deprecation warning, 0 failed/skipped, 274.31 s |
| Authorization suite | **16 passed** |
| TypeScript | clean, exit 0 |
| Production build | clean, exit 0; entry 264.31 kB (82.45 kB gzip) |
| Playwright (live API `:8000`, Vite `:5173`) | **24 passed**, 3.6 min |
| Smoke subset | 3 passed |
| Migration cycle | upgrade → downgrade → upgrade passed on a temporary database |
| Backfill on a copy of seeded QA data | 15 memberships (10 `project_owner`, 5 `editor`); 0 admins or owners missing; copy deleted |

The first full browser run after the change had 3 failures, all stale test assumptions about
workspace-wide access (a business owner without a project grant, a user who could not see the outcome's
project, and a CEO clicking admin-only Settings). The tests were corrected to grant membership, use
an administrator, or switch sessions; no server rule was weakened. The re-run was 24/24 green.

## What remained unverified at baseline

- Docker build and persistent volume behaviour.
- The claimed visual redesign (it did not exist).
- Cross-project access control.
- Outcome lifecycle (did not exist).
- Consent withdrawal consequences (did not exist).

## Status vocabulary

`Verified` · `Partially verified` · `Broken` · `Not implemented` · `Blocked`. A status is only
`Verified` when the behaviour was exercised through a running application or an executed test, not
because a screen exists.
