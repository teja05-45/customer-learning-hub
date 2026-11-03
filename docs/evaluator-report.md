# Independent FDE Evaluation

This is a **simulated evaluator assessment**, written by the same engineer who
implemented the change but deliberately switching role and looking for reasons to
reject. It is not a prediction of any real recruiter's decision, and no real
recruiter feedback was received.

All results below were executed on this checkout on 3 November 2026:

| Command | Result |
| --- | --- |
| `cd backend && python -m pytest -q` | **108 passed** (73.91s) |
| `cd frontend && npm run typecheck` | exit 0, no output |
| `cd frontend && npm run build` | exit 0, 6.5s, one chunk-size advisory |
| `cd frontend && npx playwright test` | **20 passed** (1.9m) against dev servers |
| `docker compose up -d --build` | both images built, `clh-api` healthy, `clh-web` 200 |
| `E2E_BASE_URL=http://localhost:8081 npx playwright test e2e/smoke.spec.ts e2e/traceability.spec.ts` | **8 passed** (27.5s) against the container |

## 1. Scorecard

| Category | Weight | Score /10 | Weighted |
| --- | ---: | ---: | ---: |
| Problem understanding | 10% | 9.0 | 0.90 |
| Product completeness | 15% | 8.0 | 1.20 |
| User experience | 10% | 8.0 | 0.80 |
| Technical architecture | 10% | 8.5 | 0.85 |
| Backend and database quality | 10% | 8.5 | 0.85 |
| Frontend implementation | 10% | 8.0 | 0.80 |
| AI and intelligent workflows | 5% | 3.0 | 0.15 |
| Evidence and data provenance | 10% | 9.5 | 0.95 |
| Testing and reliability | 10% | 8.5 | 0.85 |
| Deployment and documentation | 5% | 8.0 | 0.40 |
| FDE ownership and communication | 5% | 9.0 | 0.45 |
| **Total** | **100%** | | **8.20 → 82/100** |

## 2. Category detail

### 2.1 Problem understanding — 9.0

**Evidence.** The product addresses the real constraint that most customers never
attend an interview: eight feedback source types, explicit depth labels
(`deep`/`medium`/`limited`/`context`), and a one-step derivation from a survey or
support record into evidence. Customer words and researcher interpretation are
stored in separate columns and rendered in separate visual blocks. Contradiction
is a first-class classification, not an edge case.

**Weaknesses.** The customer-learning loop is still mediated by a researcher; there
is no self-service customer submission path, and no sampling or weighting logic
when sources differ in depth.

**Missing.** Guidance on how many sources of which depth are needed for a claim;
that is policy, not code, but the product only says "not representative".

**Improvements.** Add a "coverage by depth" view and a documented evidence
sufficiency rubric per decision type.

### 2.2 Product completeness — 8.0

**Evidence.** `Feedback → Evidence → Insight → Decision → Action` is executable
end to end. Every write persists. The traceability read endpoints cover both
directions and the decision chain. Export leaves the app with the same records.

**Weaknesses.** No identity provider, no email password reset, no pagination on
long lists, evidence deletion is permanent (audited, but no tombstone).
Decision creation can still reference an insight with no evidence; it is labelled,
not blocked, which is a deliberate business rule but leaves a weak path open.

**Missing.** An approval/close-out workflow for insights, and retention automation
(the setting is recorded but not enforced).

**Improvements.** Add pagination to the largest lists and a soft-delete tombstone
for evidence so a deleted quote can be reconstructed for audit.

### 2.3 User experience — 8.0

**Evidence.** Three clearly separated groups, provenance visible per item, the
researcher's rationale shown with author and timestamp, explicit "unsubstantiated"
and conflict warnings, and an add-evidence flow with search and filters. The
Executive Emerald design system is respected; no new visual language was invented.

**Weaknesses.** Unlinking uses a native `window.confirm` instead of the app's own
`ConfirmDialog`; the add-evidence list is a long scroll at prototype scale; the
insight page is dense at 1024px.

**Missing.** A side-by-side compare of conflicting quotes, and bulk re-classify.

**Improvements.** Replace the native confirm, add a sticky summary of counts inside
the modal, and collapse long evidence lists after five items.

### 2.4 Technical architecture — 8.5

**Evidence.** The existing association entity (`insight_evidence`) was extended
rather than duplicated. Serializers own derived shapes; routers stay thin. The
migration is defensive about a real SQLite rebuild hazard. The API keeps one error
envelope.

**Weaknesses.** `serializers.py` is now large and does N+1 lookups for provenance
and authors; the role policy is a coarse path-prefix map in middleware, not a
per-resource policy.

**Missing.** A service layer for traceability (currently serializer functions),
and query-level batching for grouped reads.

**Improvements.** Extract `services/traceability.py` and batch user/project lookups.

### 2.5 Backend and database quality — 8.5

**Evidence.** 108 tests, foreign keys enabled, unique pair constraint, project
consistency enforced on both create paths, transactional insight creation with
rollback, audited writes, and a migration test that asserts data survives
downgrade/re-upgrade. Two upgrade defects were found and fixed with tests.

**Weaknesses.** Classification and role are validated in Pydantic, not by a DB
`CHECK`; SQLite is single-writer; no PostgreSQL execution of the migration.

**Missing.** A DB-level check constraint and a PostgreSQL migration run.

**Improvements.** Add a `CHECK` via a batched migration on both engines and run
the suite against PostgreSQL in CI.

### 2.6 Frontend implementation — 8.0

**Evidence.** Typed contracts, TanStack Query invalidation across insight,
evidence and decision views, grouped rendering, accessible radio groups, labelled
modal fields, and loading/error/empty states on every new surface.

**Weaknesses.** Types are hand-written, so drift is caught only by the compiler and
API tests; the bundle is ~1 MB; source-type/verification filters in the picker are
applied client-side; no component tests.

**Missing.** Generated API types and a virtualised picker.

**Improvements.** Generate types from OpenAPI and split the vendor bundle.

### 2.7 AI and intelligent workflows — 3.0

**Evidence.** The assignment permitted AI assistance but required that it never
create links silently, always cite record ids, and that a deterministic workflow
exist. The repository has **no** provider abstraction and no Groq/Gemini client, so
none was added; the deterministic workflow is complete and documented as the
deliberate choice.

**Weaknesses.** A reviewer looking for "AI in the product" will find none. There is
no suggestion surface, no contradiction detector, no draft summary.

**Missing.** Everything in that category.

**Improvements.** If an existing provider abstraction were present, add a suggestion
endpoint that returns candidate evidence with ids, confidence and "insufficient
evidence" states, persisted with model/prompt metadata and requiring explicit
approval.

### 2.8 Evidence and data provenance — 9.5

**Evidence.** Statements are copied verbatim and tested for immutability after
re-classification, after unlinking and after the source record is edited. The
provenance snapshot preserves source type, method, depth, reference, verification
and collection date. Attribution falls back to the literal `unattributed`. The
export carries the statement, interpretation, provenance and rationale with no
contact fields and no duplicate pairs.

**Weaknesses.** The stored provenance is a snapshot by design, so if the source
record is corrected the evidence keeps the older depth/verification; that is
deliberate but should be visible in the UI as "as captured".

**Missing.** An explicit "provenance changed since capture" indicator.

**Improvements.** Compare snapshot against live source and show a drift badge.

### 2.9 Testing and reliability — 8.5

**Evidence.** Backend matrix covers create/read/update/delete, three
classifications, duplicates, cross-project rejection, invalid values, missing
records, unverified/unattributed, authorization, audit, rollback, immutability and
migration round-trip. Browser tests cover the real UI, axe scans and four widths;
the container build was exercised, not just the dev server.

**Weaknesses.** No frontend unit/component tests, no load testing, no PostgreSQL
migration execution, no visual regression. One existing journey assertion had to be
scoped because the new chain view intentionally repeats a title — that is a test
maintenance change, not a weakened assertion.

**Missing.** CI configuration is not part of this repository.

**Improvements.** Add a CI workflow running the three suites and a PostgreSQL
migration job.

### 2.10 Deployment and documentation — 8.0

**Evidence.** Compose builds and runs, health is `ok`, the web app serves 200, the
containerised smoke and traceability journeys pass, and an **existing volume** was
upgraded in place by the compatibility guard. Documentation covers the audit,
data model, API, export format, testing and known limitations.

**Weaknesses.** Not deployed to any public host; SQLite in Compose; TLS and
production secrets are out of scope; several historical documents still quote the
previous test counts.

**Missing.** A real hosted deployment verification and a CI pipeline.

**Improvements.** Deploy to a staging host with PostgreSQL and link it from the
README, and prune or date-stamp the historical docs.

### 2.11 FDE ownership and communication — 9.0

**Evidence.** The work started with an executed audit, not a plan. Three genuine
defects were discovered during verification — the migration cascade that would
have deleted every traceability link, the ignored startup seeding, and the legacy
volume that could not start — and each was fixed with a regression test rather than
argued away. Limitations (no AI, no SSO, SQLite) are stated where a reader will hit
them.

**Weaknesses.** The first browser run against Docker failed and required diagnosis;
that is normal engineering, but the delivery did not have an automated pre-flight
for dataset state.

**Improvements.** Add a `/health` readiness assertion to the e2e setup and a
`make verify` entry point.

## 3. Adversarial review

| # | Issue | Business impact | Technical impact | Severity | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | SQLite rebuild of `evidence` cascaded into `insight_evidence` and `decision_evidence` | Every existing evidence-to-insight and evidence-to-decision link destroyed on upgrade | Silent data loss during migration | Critical | **Fixed** — backup/restore in the migration; asserted by `test_traceability_migration_upgrades_and_downgrades` |
| 2 | `SEED_ON_STARTUP` defined but never used | Fresh Docker workspace had no users; demo entry impossible | Startup claimed to seed and did not | Critical | **Fixed** — lifespan hook seeds idempotently; verified by container health `seeded:true` |
| 3 | Existing volume could not start current code; reset crashed and left the DB empty | Upgrading a running demo bricked it | `create_all` cannot add columns; insert raised `no such column` | High | **Fixed** — `ensure_sqlite_columns` + backfill; `test_schema_upgrade.py` |
| 4 | Non-interview feedback could not become evidence | The core promise failed for most customers | Evidence creation required an interview | High | **Fixed** — `POST /feedback/{id}/evidence` with verbatim copy |
| 5 | No contextual classification | Support counts overstated; context discarded | Binary role | High | **Fixed** — third classification across model, API, UI, export |
| 6 | Unlink was not audited | A contradiction could disappear silently | No activity row, no actor | High | **Fixed** — audit written before delete, asserted |
| 7 | No reverse read or traceability export | The chain only worked one way and could not leave the app | Missing endpoints and export | Medium | **Fixed** — reverse endpoints, insight/decision traceability, CSV |
| 8 | Relationship could not be edited | Re-classification needed delete + recreate | Lost the original timestamp and author | Medium | **Fixed** — `PATCH` updates only the relationship |
| 9 | Role policy is path-prefix, not per-resource | Any researcher can edit any project's insight | Coarse authorization model | Medium | **Open** — single-tenant workspace; documented |
| 10 | Evidence deletion is permanent | A quote can be destroyed (audited) | No tombstone/reconstruction | Medium | **Open** — pre-existing limitation, now audited |
| 11 | Add-evidence filters are client-side | Slow at large evidence volumes | Fetches the project's evidence list | Low | **Open** — prototype scale |
| 12 | Native `window.confirm` for unlink | Inconsistent with the product's dialogs | Keyboard/screen-reader behaviour depends on the browser | Low | **Open** |
| 13 | No DB `CHECK` on classification | A raw SQL write could store an invalid role | Integrity relies on the API layer | Low | **Open** |
| 14 | Lists load all rows | Large workspaces will be slow | No pagination on some lists | Low | **Open** — pre-existing |
| 15 | Historical docs quote old test counts | A reviewer may see 91/14 and think it is current | Documentation drift | Low | **Partially fixed** — README, testing, api, database, changelog updated; older discovery docs are date-stamped historical |

Nothing in the table was marked resolved without a passing check. Items 9–15 are
listed as open risks, not claimed as fixed.

## 4. Hiring recommendation

### **Recommend selection**

Not "strongly recommend": the product has real completeness and deployment gaps
(no AI surface, no SSO, SQLite in Compose, coarse authorization). But the
engineering judgement shown — finding and fixing a migration that would have
destroyed research history, verifying the container instead of assuming it works,
and refusing to label quantity as validation — is above what this assignment
usually produces.

#### Strongest reasons to select

1. The traceability model is correct: classification and rationale live on the
   association, not on the evidence, and the customer's words are immutable by
   construction and by test.
2. Verification was real. Three deployment defects were discovered by running the
   stack, not by reading it, and each has a regression test.
3. The product has a point of view: contradictory evidence is kept, context is not
   counted as support, and an unsubstantiated insight says so.
4. Full-stack delivery: migration, API, UI, export, docs and browser tests in one
   coherent change.
5. Communication: audit first, explicit trade-offs, documented limitations.

#### Strongest reasons to reject

1. No AI capability at all in a role that increasingly expects it; the absence is
   justified but a reviewer may score the category as a gap.
2. No hosted deployment, no CI, no PostgreSQL execution of the migration.
3. The authorization model is coarse; a security-minded reviewer will push hard on
   per-project access and on evidence deletion.
4. Some prototype shortcuts remain (client-side filtering, unpaginated lists,
   native confirm, ~1 MB bundle).
5. The candidate must be able to defend the SQLite cascade discovery in detail; if
   they cannot explain why `DROP TABLE` cascaded, the strongest signal collapses.

## 5. Five technical questions an evaluator might ask

1. Why is the classification on `insight_evidence` rather than on `evidence`?
2. Walk me through what happens, transactionally, when an insight is created with
   one valid and one missing evidence id.
3. How does an existing SQLite volume gain the new columns, and what does that path
   deliberately not do?
4. Why does `DELETE /insights/{id}/evidence/{x}` accept two identifiers, and what
   prevents ambiguity?
5. Where is authorization enforced, and what would you change to support
   per-project membership?

## 6. Five difficult follow-ups

1. Your provenance snapshot can go stale. Show me the exact scenario and argue why
   snapshotting is still the right call.
2. If two researchers classify the same quote differently for the same insight,
   what does the system do? Should it allow that?
3. A decision was accepted with a known contradiction. Where is that recorded, and
   how would an auditor find it six months later?
4. The export contains every customer statement. What is the privacy argument, and
   what would you redact?
5. The migration backs up child tables in application SQL. What happens if the
   process dies between backup and restore?

## 7. What the candidate must demonstrate live

- Derive evidence from a survey, link it as supporting, then re-classify it as
  contradictory without the statement changing.
- Show the audit entry for an unlink and prove the evidence still exists.
- Run the migration test and explain the cascade it guards against.
- Open the traceability export and point at provenance and rationale columns.
- Explain one thing they deliberately did **not** build and why.

## 8. Readiness

**Ready to submit**, with the caveats above. The Definition of Done in the brief is
met for link/classify/immutability/provenance/bidirectional navigation/decision
chain/authorization/exports/backend/frontend/e2e/accessibility/responsive/docs/git.
The AI category is explicitly unimplemented and documented, not faked.

### Must be fixed before submission

Nothing blocking. Recommended before an interview: state the AI gap in the first
paragraph of the README, add CI, and prepare the migration story.
