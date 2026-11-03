# Final Delivery Report

Date: 3 November 2026
Repository: Customer Learning Hub — Everyday Goods
Change: evidence-to-insight traceability

## 1. Executive summary

The application already recorded feedback, evidence, insights, decisions and
actions, but the chain was broken in two places: evidence could only be created
from an interview, and an evidence-to-insight link could only be "supporting" or
"contradictory", with no author, reason or confidence. Customers who answered a
survey could never reach an insight.

That is now fixed. Evidence can be derived from any feedback source with the
customer's words copied verbatim. Each insight-evidence relationship carries its
own classification (supporting / contradictory / contextual), a rationale, an
optional confidence judgement, tags and an author. Researchers can navigate in both
directions, read the decision chain back to the original words, and export the whole
chain. Verification uncovered three defects that would have broken a real upgrade;
all three were fixed and covered by tests.

| Check | Result |
| --- | --- |
| Backend tests | **108 passed** |
| TypeScript | clean |
| Vite build | clean (one bundle-size advisory) |
| Playwright (dev servers) | **20 passed** |
| Playwright (Docker, smoke + traceability) | **8 passed** |
| Docker Compose | both services built; API healthy; web 200; `seeded: true` |

## 2. Original business problem

Everyday Goods could not reliably answer "what did customers actually tell us, and
what did we do about it?". Research lived in interviews; most customers never
attend one. Findings were asserted without a defensible link to the words behind
them, and inconvenient feedback could quietly disappear.

## 3. Existing functionality discovered (audit)

- Server-side sessions and role enforcement in middleware.
- Projects, participants, recruitment, interviews, consent.
- Eight feedback source types with depth labels and separated interpretation.
- Evidence with five types and provenance status.
- Insights, decisions, actions, dashboards, analytics, search.
- Nine CSV exports, 91 backend tests, 14 Playwright tests.
- An `insight_evidence` association already existed with a unique pair constraint
  and two roles — the right shape to extend.

Full detail: `docs/traceability-audit.md`.

## 4. New functionality implemented

- Evidence derivation from any feedback source (`POST /feedback/{id}/evidence`).
- Provenance snapshot on evidence: source type, method, depth, reference,
  verification state, collection date, plus `feedback_record_id`.
- Third classification `contextual`; rationale, confidence, tags, author and
  `updated_at` on the relationship.
- `PATCH` / `DELETE` on a relationship; unlink is audited.
- Grouped reads: insight → evidence, evidence → insights, insight traceability,
  decision traceability.
- Traceability CSV export.
- UI: grouped evidence with provenance, quality counts, unsubstantiated state,
  add-evidence and edit-relationship flows, reverse view, decision chain.

## 5. Architecture changes

- No new entity was introduced. `InsightEvidence` was extended; `Evidence` gained
  a nullable feedback link and a provenance snapshot.
- Serializers own the derived traceability shapes; routers stay thin. New schemas
  live in `app/schemas/traceability.py`.
- Provenance for interview evidence is derived from the live interview; provenance
  for feedback-derived evidence is a stored snapshot so later corrections cannot
  silently rewrite how the words are presented.

## 6. Database changes

- `evidence`: `feedback_record_id` (FK `SET NULL`), `source_type`,
  `collection_method`, `research_depth`, `source_reference`, `verification_state`,
  `collected_at`; index on `feedback_record_id`.
- `insight_evidence`: `rationale`, `confidence`, `tags`, `created_by_id` (FK
  `SET NULL`), `updated_at`; index `(insight_id, role)`.
- Alembic revision `b7d2f4a91c03`, tested upgrade → downgrade → upgrade with data.
- Existing non-Alembic databases gain the columns through
  `ensure_sqlite_columns()`, tested by `test_schema_upgrade.py`.

## 7. API changes

New or extended: `POST/GET /feedback/{id}/evidence`,
`GET /insights/{id}/evidence`, `PATCH/DELETE /insights/{id}/evidence/{relationship}`,
`GET /evidence/{id}/insights`, `GET /insights/{id}/traceability`,
`GET /decisions/{id}/traceability`, `GET /exports/traceability.csv`.
`POST /insights/{id}/evidence` keeps its `InsightDetail` response for compatibility
and now accepts classification, rationale, confidence and tags.
See `docs/api.md` and `docs/evidence-traceability.md`.

## 8. UI/UX changes

- Insight page: three separated evidence groups, provenance per item, quality
  indicators, conflict warning, explicit "unsubstantiated" state.
- Add-evidence dialog: search, source-type and verification filters, statement
  preview, multi-select, classification, required rationale, optional confidence
  and tags.
- Edit-relationship dialog: re-classification without touching the quote.
- Evidence page: every insight that uses the item, grouped, with reason and author.
- Decision page: reasoning chain back to customer statements, contradictions and
  gaps.
- Feedback page: **Create evidence** action.
- Settings: **Evidence traceability** export.
- Executive Emerald used throughout; no new visual language.

## 9. Security and authorization

- Authentication unchanged: server-side sessions, HTTP-only cookie, PBKDF2.
- Every new write goes through the existing middleware policy (researcher/admin for
  feedback/evidence/insights) and is covered by a test that verifies a CX user gets
  `403` and an anonymous request `401`.
- Cross-project linking is refused server-side with `400`; the frontend filter is
  convenience only.
- No secrets introduced; no contact fields added; export includes no email or notes.
- Frontend input validation is mirrored on the server; it is not the boundary.

## 10. Test results (executed)

```
cd backend && python -m pytest -q
108 passed in 73.91s

cd frontend && npm run typecheck
exit 0

cd frontend && npm run build
exit 0, built in 6.52s (one chunk-size advisory: 1,011.67 kB)

cd frontend && npx playwright test
20 passed (1.9m)
```

New backend suites: `test_traceability.py` (15), `test_migrations.py` (1),
`test_schema_upgrade.py` (1). The migration suite runs Alembic against a real file.

## 11. Accessibility results

`frontend/e2e/a11y.spec.ts` ran axe (WCAG 2.0/2.1 A and AA) on all twelve primary
screens, the insight detail page, the evidence detail page and the open
add-evidence dialog. Zero serious or critical violations. Keyboard-only navigation
and the skip link are covered by `smoke.spec.ts`.

## 12. Responsive verification

`responsive.spec.ts` passed at 375, 768, 1024 and 1440 for the primary screens.
The new test additionally loads a real insight and checks all four widths for
horizontal overflow. No overflow was observed.

## 13. Export verification

Ten exports: the nine existing entities (unchanged and still passing) plus
`traceability.csv`. Verified in the API (headers, BOM, provenance, classification,
rationale, statement integrity, no duplicate insight/evidence pairs, synthetic
origin) and in the browser (download, parse, statement and rationale present). The
download is written to the audit trail.

## 14. Docker verification

`docker compose up -d --build` built both images; `clh-api` reported healthy;
`GET /api/v1/health` returned `status: ok`, `seeded: true`; the web app returned
200 at `http://localhost:8081`; `E2E_BASE_URL=http://localhost:8081` ran the smoke
and traceability specs — 8 passed.

The run also exercised a **pre-existing volume** from an earlier schema. Without
the compatibility guard the API failed on the first insert; with it, the volume was
upgraded in place and reseeded.

## 15. Deployment verification

Locally verified with Docker Compose. **No public/hosted deployment was performed**,
so no production-readiness claim is made. TLS, managed PostgreSQL, backups and an
identity provider remain deployment work, not delivered here.

## 16. Documentation updates

- `docs/traceability-audit.md` — audit performed before the change.
- `docs/evidence-traceability.md` — model, lifecycle, API, UI, export, coverage.
- `docs/evaluator-report.md` — independent scorecard and adversarial review.
- `docs/final-delivery-report.md` — this document.
- Updated: `README.md`, `docs/api.md`, `docs/database.md`, `docs/changelog.md`,
  `docs/testing.md`.
- Historical discovery documents (`docs/01-…` to `docs/20-…`) were left as dated
  records; some quote the previous test counts.

## 17. Git commits

Ten commits, each a single-line conventional subject with no body and no generated
attribution. See `git log --oneline` for hashes:
`feat(backend): add evidence insight relationships`,
`feat(api): expose insight traceability endpoints`,
`feat(exports): include evidence traceability`,
`fix(backend): seed demo data on startup`,
`fix(backend): upgrade existing volumes on start`,
`test(backend): validate evidence relationship integrity`,
`feat(ui): add supporting and contradictory evidence`,
`test(e2e): verify complete evidence traceability journey`,
`docs: document evidence traceability architecture`,
`docs: add independent evaluator and delivery reports`.

## 18. Screenshots

The Playwright screenshot spec regenerated `docs/screenshots/` during the full run.
`11-insight-traceability.png` now shows the grouped evidence section, and
`02-overview.png` is referenced at the top of the README. Screenshots were captured
only after data loaded.

## 19. Known limitations

- **AI assistance is not implemented.** The repository has no provider abstraction
  and no Groq/Gemini client; adding one would have introduced an unrequested paid
  dependency. The deterministic workflow is complete.
- No SSO, email password reset or self-service customer submission.
- SQLite is the Compose database (single writer); PostgreSQL is the intended
  production engine and was not available to execute the migration against.
- Some lists load all rows; the add-evidence picker filters source type and
  verification client-side.
- Evidence deletion is permanent (audited, no tombstone).
- Authorization is workspace-wide: any researcher may edit any project.
- No CI configuration; no load, penetration or visual-regression testing.
- Bundle size advisory (~1 MB single chunk).
- Unlinking uses the native browser confirm rather than the product dialog.

## 20. Remaining risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| A future migration rebuilds a cascading parent | Silent link loss | The current migration guards it and the test asserts row survival; the same pattern must be reused |
| Provenance snapshot vs live source drift | A reader may see stale depth/verification | Snapshot is deliberate; a drift badge is not implemented |
| Classification is Pydantic-only | A raw SQL write could store an invalid value | All product writes go through the API; a DB `CHECK` is future work |
| Coarse roles | Over-broad edit rights inside one workspace | Acceptable single-tenant; per-project membership is future work |
| Documentation drift in older docs | Reviewer confusion | Current docs updated; historical set is date-stamped |

## 21. Hiring evaluator scorecard

Reference: `docs/evaluator-report.md`. Weighted score **82/100**;
recommendation **Recommend selection** (not "strongly"); AI and deployment are the
drag, provenance and ownership are the strength.

## 22. Final submission recommendation

Ready to submit, with the limitations stated rather than hidden.

**Implemented and tested:** feedback-derived evidence, three classifications,
relationship metadata and author, immutability, provenance snapshot, grouped and
reverse reads, unaudited-to-audited unlink, traceability export, decision chain,
migration round-trip, legacy-volume upgrade, role enforcement, UI flows, axe and
four-width responsive checks, Docker build and containerised browser tests.

**Implemented but not tested:** nothing material. The only untested implementation
detail is the migration on PostgreSQL (same Alembic operations, no instance).

**Partially implemented:** provenance-drift visibility (not built), source-type and
verification filtering (client-side), pagination (not built).

**Not implemented:** AI suggestions, SSO, email reset, retention enforcement,
tombstoned evidence deletion, CI pipeline.

**Blocked by external access or credentials:** hosted deployment verification
(no target platform), PostgreSQL migration execution (no instance), real recruiter
feedback (none requested; the evaluator report is explicitly simulated).
