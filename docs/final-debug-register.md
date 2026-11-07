# Final debug register

This register records every defect found in the audit and release pass, its root cause, fix, and the
test that now protects it. It includes defects found *during* this pass, not only pre-existing ones.
No row is marked fixed without an executed check.

Severity uses P0 (data/security/broken core), P1 (major feature wrong or missing), P2 (quality or
scale), P3 (cosmetic).

## 1. Closed defects

| ID | Sev | Defect | Root cause | Fix | Verified by |
| --- | --- | --- | --- | --- | --- |
| QA-01 | P0 | Consent withdrawal had no consequences | Withdrawal only inserted a consent row; no dependent state was updated | Cancel future sessions, set `contact_consent=withdrawn`, block re-booking, write interview/participant activity; retain prior evidence | `test_consent_withdrawal.py` (4 tests); `workflows.spec.ts` withdrawal journey |
| QA-02 | P0 | Outcome measurement did not exist | No model, API, UI or tests | Added `Outcome`, migration `c8e3a1d5f204`, endpoints, `/outcomes` screen, journey integration, derived status | `test_outcomes.py` (9 tests); `workflows.spec.ts` plan → record → status |
| QA-03 | P1 | Participant profile omitted feedback history | Profile serializer joined only interviews/evidence | Added feedback history and per-interview insight counts derived from evidence links | `test_project_authorization.py` nested-record test; `workflows.spec.ts` profile history |
| QA-04 | P1 | Journey board and timeline missing | Never implemented; project tabs were static | `build_journey` service + `/projects/{id}/journey`, board/timeline UI from real records | `test_journey_view.py`; `workflows.spec.ts` board + timeline |
| QA-05 | P1 | Approved Notion palette never implemented | Legacy "Executive Emerald" theme remained | `notion.css` loaded last, exact tokens, Inter, component overrides | Manual visual review + screenshots; axe contrast checks |
| QA-06 | P1 | Reversed seed outcome windows blocked result recording | Seed generated `window_end` before `window_start`; server validation rejected every result | Corrected seed dates; regression test asserts chronological windows | `test_outcomes.py` seed-window test |
| QA-07 | P2 | Past timeline milestones labelled "Upcoming" | State was hard-coded | Compare milestone dates with today; past/upcoming/overdue derived | `test_journey_view.py`; `workflows.spec.ts` timeline |
| QA-08 | P2 | 1,011.67 kB entry bundle | All screens shipped in one chunk | Route-level lazy loading with Suspense | Production build: entry ≈264 kB (82 kB gzip) |
| QA-09 | P2 | Landmark/contrast issues after theme change | Section headings not associated; secondary text below AA on the rail | Accessible section names; darkened secondary token to `#6f6e6a`; axe re-run | `a11y.spec.ts` (axe), 0 serious/critical on covered screens |
| QA-10 | **P0** | **No project-level authorization (IDOR/BOLA)** | Authorization was workspace-role-only; every signed-in user could read every project by id | `ProjectMembership` + `ProjectRole`, additive migration with least-privilege backfill, central `services/access.py`, scoping of lists/dashboard/analytics/search/exports, membership API, frontend role UI | `test_project_authorization.py` (16 tests); full backend suite; browser suite |
| QA-11 | P2 | Leading-wildcard search cannot use an index | `lower(column) LIKE '%term%'` | **Not fixed.** Measured (17.91 ms median at 50k rows), bounded, and documented with the FTS5/`pg_trgm` path as next work | Benchmark recorded in the delivery report; remains open |
| QA-12 | P1 | Demo reset broke for researchers during this pass | Narrowing `/settings` to admin also narrowed `/demo`, because both were matched together | Split the middleware rule: `/demo` → researcher/admin, `/settings` → admin only | Manual API reproduction; `smoke.spec.ts` re-run green |

## 2. Defect found and fixed within the authorization work

| ID | Sev | Symptom | Cause | Resolution |
| --- | --- | --- | --- | --- |
| QA-13 | P1 | A workspace `business_owner` received `403` when adding a project member, even as project owner | The middleware's write-role prefix list did not include the nested `/projects/{id}/members` route, so only researcher/admin passed the first gate | Added `MEMBER_MANAGEMENT` regex granting all signed-in roles through the *middleware* gate; `assert_project_manage` remains the authoritative check | 
| QA-14 | P1 | A `researcher` could still `PATCH /settings` | `/settings` was in the researcher write prefix set, contradicting the role matrix | Moved `/settings` and `/users` to admin-only in `USER_ADMIN_ROLES`; tests updated | 
| QA-15 | P1 | Decisions recorded without a project were readable by every signed-in user | Orphan records had no project to scope by, so the read path skipped the check | `assert_entity_read/write` for orphans: admin or `owner_id` only; attaching to a project adopts scope; linking cross-project records is rejected | `test_project_authorization.py` orphan and cross-link tests |

## 3. How each fixed defect was verified

- **Security (QA-10, QA-13–15):** pytest makes real HTTP requests with real cookie sessions as seven
  seeded users. Denials are asserted as `403`, not inferred from hidden UI. The suite covers direct
  reads, nested records, aggregate counts, exports, search and cross-project links.
- **Consent (QA-01):** unit-level API test plus a browser journey; both assert the cancellation and the
  re-booking refusal, and that prior evidence remains.
- **Outcomes (QA-02, QA-06):** API tests for every derived transition, including the rejections; seed
  windows asserted chronological.
- **Journey (QA-04, QA-07):** service tests for stage derivation and date state; browser test for board
  and timeline rendering from real records.
- **Theme and accessibility (QA-05, QA-09):** screenshots captured from the production build; axe run
  on the primary screens with zero serious/critical violations.
- **Bundle (QA-08):** build output compared before/after; no feature removed.

## 4. Known open defects and limits

| ID | Sev | Item | Why it remains |
| --- | --- | --- | --- |
| QA-11 | P2 | Unindexed substring search | Correct at demo scale, measured; an index needs an FTS/trigram design and migration. Documented, not hidden. |
| QA-16 | P2 | Membership role changes/removals are not audited (adds are) | Small follow-up; the data model and activity service support it. |
| QA-17 | P2 | Frontend cache can show a stale control after a grant is revoked | The API refuses immediately (test 15); the UI refreshes on reload. |
| QA-18 | P3 | Journey board needs horizontal scrolling at 1440 px | Nine stages are intentionally shown; a responsive summary is future polish. |
| QA-19 | P2 | No frontend unit/component tests | Playwright covers rendered behaviour; isolated component logic is untested. Stated coverage gap. |
| QA-20 | P2 | No retention/deletion automation after withdrawal | A legal/product policy decision; the prototype stops contact and retains lawful research. |

## 5. Reproducing the security checks

```bash
cd backend
./.venv/Scripts/python.exe -m pytest tests/test_project_authorization.py -q   # 16 passed
./.venv/Scripts/python.exe -m pytest -q                                      # full suite
```

Expected: every denial is `403`; a member removal takes effect on the next request; an admin can read
every project; a viewer cannot write even with a business workspace role.
