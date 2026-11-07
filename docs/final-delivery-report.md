# Final delivery report

Audit date: 6 November 2026 · Branch: `main` · Base commit: `6bfbe62` · Commits made in this pass:
**none** (the working tree is intentionally left dirty for review).

## 1. Executive summary

> **Release addendum (7 November 2026):** this report describes the first audit pass. The unresolved
> P0 it records — project-level authorization — has since been implemented, migrated, tested and
> documented. The authoritative release report is now
> [`final-submission-audit.md`](final-submission-audit.md). Where the two differ, the audit wins.

This pass independently re-tested the Customer Learning Hub and corrected several claims that did not
survive inspection. The repository did **not** contain the described Notion-style redesign, did not
have 120 backend tests, and could not run Playwright until Chromium was installed. It also lacked
outcome measurement, profile feedback history, journey views and any consequence for consent
withdrawal.

Those gaps were implemented or explicitly documented. The result is a coherent research system with a
verified end-to-end chain, honest labels and a measured set of remaining limits. Project-level
authorization was still missing at the end of this first pass; it is now implemented — see the
addendum above and `authorization-and-permissions.md`.

Final state:

| Check | Result |
| --- | --- |
| Backend | **122 passed**, 0 failed, 0 skipped |
| TypeScript | clean |
| Production build | clean; entry 261.65 kB (81.70 kB gzip), largest chunk 382.81 kB |
| Playwright | **24 passed** against the Docker build |
| Axe | 13 primary screens + dialogs, 0 serious/critical |
| Responsive | 375 / 768 / 1024 / 1440 px, no page overflow |
| Docker Compose | built, both containers healthy, persistence verified |
| Hosted deployment | not performed, not claimed |

## 2. Baseline

At the start: branch `main`, clean tree, **108** backend tests, clean typecheck, successful build with a
1,011.67 kB entry chunk, no Docker images/volumes, and 20 Playwright failures caused only by a missing
Chromium binary. No commit implemented the claimed palette. Full command output and the discrepancy
list are in `docs/final-qa-baseline.md`.

## 3. Business workflow validation

The full chain was mapped and exercised:

```
Project → Customer discovery → Recruitment → Consent → Session / async feedback
→ Evidence → Insights → Decisions → Actions → Outcome measurement
```

Every stage is verified through API tests and/or Playwright, including project-level isolation after
the release addendum. Details,
including the exact database records and permission rules, are in
`docs/workflow-validation-matrix.md`.

## 4. Page-by-page audit

All 22 registered routes were inspected. There is no Customers or Reports route; participants are the
customer directory and Analytics/Settings provide reporting. One coverage gap remains: `/projects/new`
was verified through the API but not driven end-to-end through its form. Full table and per-page notes:
`docs/page-by-page-qa.md`.

## 5. Defects discovered

| ID | Severity | Defect |
| --- | --- | --- |
| QA-01 | Critical | Consent withdrawal had no consequences |
| QA-02 | High | Outcome measurement did not exist |
| QA-03 | High | Profile omitted feedback history |
| QA-04 | High | Journey board and timeline missing |
| QA-05 | High | Approved palette never implemented |
| QA-06 | High | Reversed seed outcome windows blocked result recording |
| QA-07 | Medium | Past timeline milestones labelled "Upcoming" |
| QA-08 | Medium | 1 MB entry chunk |
| QA-09 | Medium | Landmark/contrast issues after theme change |
| QA-10 | Critical | No project-level authorization — **fixed in the release pass** |
| QA-11 | Low | Leading-wildcard search unindexed (open) |

## 6. Defects fixed

QA-01 to QA-10 are fixed with regression coverage; QA-11 remains open and documented. The
reproduction, root cause, fix, test and verification for each are in
`docs/final-debug-register.md` (historical detail in `docs/bug-fix-register.md`).

## 7. Backend changes

- Consent lifecycle consequences: cancel future sessions, block re-booking, update participant contact
  consent, write interview and participant audit events, preserve collected research.
- `Outcome` model/enums/schemas/endpoints, migration `c8e3a1d5f204`, business-owner permissions,
  server-derived status and audit events.
- Participant detail: feedback history and per-interview insight counts derived from evidence links.
- Project journey service and `/projects/{id}/journey` endpoint.
- Corrected seed outcome windows; corrected timeline state derivation.
- New tests: `test_outcomes.py`, `test_consent_withdrawal.py`, `test_journey_view.py`.

## 8. Frontend changes

- Route-level lazy loading with Suspense; `/outcomes` route and navigation.
- New Outcome measurement screen (plan, record result, filters, honest reasons).
- Journey board and timeline on project detail, replacing the default "Questions" tab with the
  learning journey.
- Participant profile feedback history and derived insight counts.
- New types for outcomes, journey and feedback history.
- `frontend/src/styles/notion.css` implementing the approved tokens and component overrides; loaded
  after the legacy sheets.
- `SectionCard` exposes an accessible name so sections are real landmarks.
- Extended Playwright helpers, screenshots, a11y and responsive lists; new `workflows.spec.ts`.

## 9. Consent and authorization status

**Consent:** implemented and verified. Grant, deny, withdraw and retention of history work. Withdrawal
stops future contact and future bookings; it does not erase evidence collected before withdrawal. A
production retention/deletion policy is still required.

**Authorization:** workspace roles and project-level membership are both implemented and verified.
`project_memberships` (viewer/editor/project_owner) gates *where*; the workspace role gates *what*.
Lists, dashboard, analytics, search and exports are scoped. Admins are implicit owners of every
project, which is a deliberate residual risk (not tenant isolation). See QA-10 and
`authorization-and-permissions.md`.

## 10. Customer profile improvements

Real relationships now connect a participant to participation history, per-interview evidence and
insight counts, feedback sources with depth and verification, and recruitment records. The history is
project-labelled and does not copy records or leak another participant's feedback.

## 11. Learning journey status

Verified. Nine stages are derived from real records; cards link to those records. The timeline uses
actual dates and computes past/upcoming/overdue. There is deliberately no drag-and-drop; status
changes belong to the entity endpoint with its validation.

## 12. Outcome measurement status

Verified. The lifecycle is planned → measurement pending → measured (achieved / not achieved /
inconclusive). Achieved is derived from actual, target and direction. An explicit measured status
without a result is rejected; a result without a target is inconclusive. The loop is connected to a
decision and optionally an action.

## 13. Search and performance findings

Search remains `lower(column) LIKE '%term%'`. A 50,000-row synthetic SQLite benchmark measured a
17.91 ms median full scan versus 0.036 ms for an FTS5 trigram index lookup. At the demo's 10 rows the
scan is negligible, and a B-tree cannot help a leading wildcard, so no index was added. The scalable
path (FTS5 trigram or PostgreSQL `pg_trgm`, with triggers and a short-query fallback) is documented as
next work. Bundle splitting reduced the entry from 1,011.67 kB to 261.65 kB with no feature loss.

## 14. Screenshot gallery

All images are under `docs/screenshots/` and were captured from the production build after real data
loaded.

| Area | Files |
| --- | --- |
| Entry | `01-demo-entry.png` |
| Workspace | `02-overview.png`, `03-projects.png`, `17-global-search.png` |
| Project | `04-project-detail.png`, `05-project-evidence.png`, `22-project-journey-board.png`, `23-project-journey-timeline.png` |
| Customers | `06-participants.png`, `24-participant-profile.png` |
| Research | `07-recruitment.png`, `08-interviews.png`, `09-interview-workspace.png`, `19-feedback-sources.png`, `25-consent-withdrawal.png` |
| Evidence & insight | `20-evidence.png`, `10-insights-library.png`, `11-insight-traceability.png` |
| Decisions & actions | `12-decision-register.png`, `13-decision-detail.png`, `14-actions.png`, `21-outcomes.png` |
| Administration | `15-analytics.png`, `16-settings.png` |
| Responsive | `18-mobile-overview.png` (375), `26-tablet-projects.png` (768), `27-mobile-outcomes.png` (375) |

## 15. README updates

README now documents the real workflow, implemented capabilities, current palette, screenshot
gallery, verified commands, Docker results, limitations and roadmap. It no longer claims 108 tests,
20 browser tests or an "Executive Emerald" implementation as the current design.

## 16. Backend test results

```
122 passed, 1 warning in ~150 s
```

Warning: Starlette's `anyio.abc.BlockingPortal` deprecation in the test client. No failures, errors or
skips. Includes the consent, outcome, journey, RBAC, migration, export and traceability suites.

## 17. Frontend test results

- `npm run typecheck`: exit 0.
- `npm run build`: exit 0; no chunk-size advisory.
- No frontend unit/component test runner is configured. This is a stated coverage gap; Playwright
  covers rendered behaviour, not isolated component logic.

## 18. Playwright test results

**24 passed** against `http://localhost:8081` (Docker production build), including:

- every primary screen, deep links, 404 and API error state;
- keyboard skip link and command-palette search;
- complete research-to-decision journey;
- survey → evidence without an interview;
- cross-project relationship refusal and unaudited attempts;
- feedback create/verify/delete;
- every CSV export;
- journey board/timeline, profile feedback history, outcome lifecycle, consent withdrawal;
- axe and four responsive widths.

A first run failed only because Chromium was absent; after `npx playwright install chromium`, 20/20
existing tests passed before the new tests were added.

## 19. Accessibility results

Axe: 0 serious/critical violations on 13 primary screens, the traceability screens, the add-evidence
dialog and the command palette. Keyboard skip navigation and search were exercised. The palette's
secondary text was darkened from `#787774` to `#6f6e6a` to meet 4.5:1 on the rail and white.

**Not claimed:** full WCAG 2.2 AA conformance. A manual screen-reader review and reduced-motion manual
check remain outstanding; automated tooling cannot establish conformance alone.

## 20. Responsive results

375, 768, 1024 and 1440 px passed for the primary screens; the page never scrolls horizontally and the
rail switches to an off-canvas drawer below 992 px. Wide tables scroll inside their wrapper. The
nine-column journey board scrolls inside its own container by design.

## 21. Docker results

`docker compose up --build -d` built both images, created the named volume and started both
containers; both reported healthy. Verified:

- API health 200 and web 200 with the expected page title;
- seeded production startup log (7 users, 5 projects, 10 participants, 11 interviews, 2 outcomes);
- authenticated write through the container API;
- the written record was still present after `docker compose restart backend`;
- no errors in the API logs.

No pre-existing volume was deleted. Hosted deployment readiness is not claimed.

## 22. Deployment status

Local development and Docker Compose are verified. There is no hosted deployment, no CI run, no TLS
termination and no external identity provider. The product is a portfolio prototype, not a production
service.

## 23. Git commits

No commits were created in the first pass. The release pass records its changes in focused
conventional commits (`fix(auth)`, `feat(ui)`, `test(qa)`, `docs(release)`) and does not bundle
unrelated work.

## 24. Remaining gaps

| Gap | Severity | Status |
| --- | --- | --- |
| Project-level authorization / membership | P0 | **Implemented**; 16 adversarial tests |
| Retention/deletion policy after withdrawal | P1 | Policy decision, not implemented |
| Indexed search at scale | P2 | Measured, not implemented |
| Frontend unit/component tests | P2 | Not configured |
| UI path for `/projects/new` | P3 | Partially verified |
| SSO, password reset, rate limiting | P2 | Not implemented |
| Real outreach/audio/commerce integrations | — | Deliberately out of scope |
| Hosted deployment | — | Not performed |

## 25. Recruiter evaluation

Independent simulated score: **86/100, Recommend selection with conditions**. Strong product judgment,
workflow coherence, debugging and now a real project authorization boundary; unindexed search,
partial membership auditing and the missing frontend unit layer are the remaining reservations. Full
scorecard: `docs/final-recruiter-evaluation.md`.

## 26. Submission recommendation

Submit for evaluation as a portfolio prototype with the limitations above stated openly. Do not
describe it as multi-tenant, enterprise-isolated, fully WCAG-conformant or production-deployed. Project
membership is implemented; lead with the verified research workflow, the project boundary and the
honest treatment of uncertainty.
