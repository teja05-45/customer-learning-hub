# Changelog

Format: what changed and why it matters. No claim is made for a change that was not executed.

## 1.8.0 — Project-level authorization

### Added

- `ProjectMembership` and `ProjectRole` (`viewer < editor < project_owner`), with migration
  `d4e8f1a2c7b9` and a least-privilege backfill (owners, active admins, demonstrable contributors).
- Central authorization service (`backend/app/services/access.py`): project read/write/manage checks,
  visible-project resolution, participant scoping and entity→project resolvers.
- Membership API: list, grant, change role and revoke, with last-owner protection. Project creation
  grants the creator `project_owner`; reassigning an owner grants the new owner too.
- Scoping of project lists, dashboard, analytics, search, exports and every nested record. Orphan
  decisions/insights are owner/admin-only until attached to a project.
- Frontend `ProjectProvider`, sidebar project switcher with access label, role pill, read-only state,
  access-denied page and a Members tab for project owners. "New project" is limited to
  researcher/admin.
- `backend/tests/test_project_authorization.py` — 16 adversarial HTTP tests.

### Fixed

- A researcher could `PATCH /settings`; workspace settings and user administration are now admin-only.
- A business owner could not add a project member because the middleware prefix list omitted the
  nested members route; all signed-in roles now pass the middleware gate while
  `assert_project_manage` remains authoritative.
- A demo-reset regression from narrowing `/settings` and `/demo` together; `/demo` remains available
  to researcher/admin, `/settings` is admin-only.

### Verified

- **138 backend tests passed** (1 deprecation warning, 0 failed/skipped, 274.31 s).
- TypeScript clean; production build clean (entry 264.31 kB, 82.45 kB gzip).
- **24 Playwright tests passed** against the live API + Vite stack (3.6 min).
- Migration fresh upgrade → downgrade → upgrade passed; backfill on a copy of seeded QA data produced
  15 memberships (10 owner, 5 editor) with no admin or owner left without access; copy deleted.

### Known open

- Workspace admins are implicit owners of every project; this is not tenant isolation.
- Leading-wildcard search is unindexed at scale; measured and documented.
- Membership role changes/removals are not audited (adds are).


## 1.7.0 — Final QA: consent, outcomes, journey and the real palette

### Added

- Consent withdrawal now has consequences: future sessions are cancelled, re-booking is refused,
  the participant's contact consent is updated, and interview plus participant audit events are
  written. Prior evidence and feedback are retained and the consent history stays append-only.
- Outcome measurement: `Outcome` model, schemas, endpoints, migration `c8e3a1d5f204`, seed data,
  `/outcomes` screen, nav entry, project-journey column and server-derived status rules. A measured
  status without an actual result is rejected; a result without a target is `inconclusive`.
- Participant profile feedback history with real relationships, plus per-interview insight counts
  derived from evidence links.
- `GET /projects/{id}/journey` and a Board/Timeline view on project detail. Nine stages are derived
  from records; cards link to those records. There is no decorative drag-and-drop.
- `frontend/src/styles/notion.css` implements the approved white/`#F7F7F5` palette, Inter typography,
  `#347A69` actions and `#7565B5` interpretation surfaces. Emerald remains as an overridden
  historical layer.
- Route-level code splitting for every screen except the shell/dashboard.
- `workflows.spec.ts` and backend tests for consent withdrawal, outcomes and the journey; screenshot
  set expanded to 27 images, including mobile and tablet.

### Fixed

- Seeded outcome windows were reversed, so every result update failed with HTTP 400. Seed dates are
  now chronological and a regression test asserts it.
- Past journey milestones were hard-coded as `upcoming`; status is now derived against today.
- Section cards were unnamed for assistive technology; they now expose an accessible name.
- The approved palette's secondary text failed AA on the light rail; the text token is `#6f6e6a`
  (documented deviation), and axe is green again.

### Verified

- 122 backend tests, clean typecheck, clean production build, 24 Playwright tests against the Docker
  build, axe on 13 primary screens, four responsive widths, Docker persistence across restart.

### Known open

- Project-level authorization remains workspace-wide (P0).
- Leading-wildcard search is unindexed at scale; measured and documented.

## 1.6.0 — Evidence traceability

### Added

- Evidence can be derived from **any** feedback source, not only an interview:
  `POST /feedback/{id}/evidence` copies the customer statement verbatim and snapshots the source
  type, collection method, research depth, reference, verification state and collection date.
- `contextual` joins `supporting` and `contradictory` as a relationship classification. The
  classification lives on the association row, so one quote can support one finding, contradict
  another and merely add context to a third.
- `insight_evidence` now records a rationale, optional researcher confidence, tags, the author and
  an `updated_at` timestamp. Re-classifying is a `PATCH`; the evidence row is never touched.
- Grouped reads and reverse navigation: `GET /insights/{id}/evidence`,
  `GET /evidence/{id}/insights`, `GET /insights/{id}/traceability` and
  `GET /decisions/{id}/traceability`.
- Insight page: three separated evidence groups, provenance per item, quality counts that keep
  quantity separate from quality, an explicit **unsubstantiated** state, and contradiction made
  visible rather than filtered out.
- Add-evidence workflow with search, source-type and verification filters, statement preview,
  multi-select, classification, rationale, optional confidence and tags.
- Evidence page lists every insight that uses the item, grouped by classification, with the
  researcher's reason and author.
- Decision page shows the reasoning chain back to customer statements, including contradictions
  carried through from linked insights and explicit gaps.
- Traceability CSV export (`/exports/traceability.csv`): one row per relationship, UTF-8 BOM,
  formula-injection safe, no personal contact fields, audited.
- Alembic revision `b7d2f4a91c03` with upgrade/downgrade tests, and 17 new backend tests
  (108 total). Five Playwright traceability journeys plus axe coverage of the new screens and the
  add-evidence dialog (20 browser tests total).

### Fixed

- **All existing evidence-to-insight and evidence-to-decision links would have been deleted by the
  upgrade.** On SQLite, adding a foreign key rebuilds `evidence`, and the implicit delete cascades
  into both link tables. The migration now backs the children up and restores them; the test
  asserts links and statements survive a full upgrade → downgrade → upgrade cycle.
- **`SEED_ON_STARTUP` was never honoured.** Docker came up with an empty workspace, so
  demonstration entry had no user and every browser test failed at sign-in. The lifespan hook now
  seeds idempotently.
- **An existing Docker volume could not start the current code.** `create_all` cannot add columns,
  so the first insert failed with "table evidence has no column named feedback_record_id" and a
  demo reset left the workspace empty. A SQLite compatibility guard adds the missing columns and
  backfills timestamps; `tests/test_schema_upgrade.py` reproduces the legacy database.
- Unlinking evidence is now audited with the actor and the classification; previously a
  contradiction could be removed silently.
- Evidence and feedback deletion now write an audit entry naming the actor.

## 1.5.0 — Unified feedback sources

### Added

- `feedback_records` table and `FeedbackRecord` model covering eight source types: interview,
  written feedback, structured form, short survey, customer support, product review, manual
  entry and CSV import. Each record stores the original words, collection method, source
  reference, collection date, contributor, project, optional participant and interview, and a
  separate researcher interpretation.
- `/api/v1/feedback` CRUD: list with project/source/verification/attribution/search filters,
  create, read, update and audited delete. Writes require the researcher or administrator role
  through the existing server-side policy.
- Explicit research-depth classification (`deep`, `medium`, `limited`, `context`) with a note per
  collection method. A short survey is never presented as equivalent to a moderated interview.
- Verification requires a source reference. Interview sources must link to an interview in the
  same project, and a cancelled interview cannot produce feedback. Unattributed records are
  allowed but labelled everywhere.
- Feedback sources page with source/verification/attribution filters, project filter, a create and
  edit form, one-click verification, and a confirmed delete.
- Feedback sources added as the ninth CSV export, including separate `content` and
  `interpretation` columns.
- Eleven backend tests and a browser journey for create, verify and delete. All primary-screen
  accessibility, smoke and responsive checks now include the new page.
- Five seeded synthetic feedback sources so the demo shows interviews, a survey, support
  feedback, a product review and an import side by side.

### Verified

- Backend: 91 passed.
- Browser: 14 passed, including axe and all nine exports.
- `tsc --noEmit` and `vite build`: clean.

No external support, review or CRM system is connected. Records only exist when someone with
permission creates or imports them, and the deep-link to an external system is never implied.

## 1.4.0 — Executive Emerald redesign and browser-verified exports

### Changed

- The blue-and-white interface was replaced by the Executive Emerald design system: warm canvas
  (`#F7F5EF`), deep emerald chrome (`#103F32`), emerald action (`#176B52`), gold provenance
  marker (`#D6A84F`) and terracotta contradiction accent. Tokens and component refinements live in
  `frontend/src/styles/emerald.css`, loaded after the base stylesheet.
- Typography now pairs a serif display stack for page and brand titles with the existing sans for
  operational UI. Charts use an emerald/teal/gold/terracotta/plum categorical ramp.
- Motion tokens were introduced for fast interaction (140 ms), standard transitions (200 ms) and
  panels (260 ms), with a global `prefers-reduced-motion` override.
- The Claude Code design tooling was not available: neither `ui-ux-pro-max-cli` nor the 21st MCP
  server was installed or connected, so no generated component or design system was consumed.
  This is recorded in `docs/design.md` and the master design system rather than claimed.

### Added

- `design-system/customer-learning-hub/MASTER.md` — palette with contrast pairs, typography,
  layout, components, motion, accessibility rules and page overrides.
- `frontend/e2e/responsive.spec.ts` — every primary screen at 375, 768, 1024 and 1440 px, the
  off-canvas navigation at the small breakpoints, the desktop rail above them, and no page-level
  horizontal overflow.
- `frontend/e2e/exports.spec.ts` — clicks all eight Settings export buttons, waits for the real
  downloads, asserts filenames, the UTF-8 BOM, headers, row counts and provenance labels.

### Fixed

- Sidebar section labels failed axe colour contrast (3.7:1) against the new chrome; the token is
  now `#B9CDC2` (≈6:1) and the accessibility suite passes.
- Stray inline blues on the authentication screen and the progress-bar track were replaced with
  design tokens.
- Browser tests that assumed a client-supplied identity header, a cross-host cookie or a quiet
  signed-out `/auth/me` probe were corrected. They now use explicit signed-in API contexts and
  collect console errors only after sign-in; assertions were not weakened.

### Verified

- Backend: 79 passed.
- Browser: 13 passed, including axe and all exports; screenshots regenerated.
- `tsc --noEmit` and `vite build`: clean.

## 1.3.0 — Credential throttling, CSRF defence and account administration

### Added

- Failed sign-ins are throttled per client address and per account by an in-process sliding
  window (`app/core/ratelimit.py`). A blocked attempt returns `429 rate_limited` with
  `Retry-After` and issues no cookie; a successful sign-in clears the counter. Limits are
  environment-driven (`LOGIN_MAX_FAILURES`, `LOGIN_WINDOW_SECONDS`) and `TRUST_PROXY_HEADERS`
  controls whether `X-Forwarded-For` is believed.
- State-changing requests are refused with `403 csrf_origin_rejected` when the browser reports
  an `Origin`/`Referer` outside `CORS_ORIGINS` (or the request's own host) or an opaque
  `Origin: null`. This closes the CSRF gap alongside `SameSite=Lax`.
- Administrator account management: `GET/POST /users`, `PATCH /users/{id}` and
  `POST /users/{id}/password`, plus the Settings UI to add a person, change a role, deactivate a
  leaver and reset a password. Deactivation and password reset revoke that account's sessions,
  and the last active administrator cannot be demoted or deactivated.
- `tests/test_security.py` (10 tests) pins all of the above.

### Changed

- `GET /users` is administrator-only, because the directory exposes every email address; the
  public `/session` directory still carries the name and role used by owner pickers.
- Error responses may now carry headers (`Retry-After`), which the shared error envelope passes
  through instead of dropping.


## 1.2.0 — Authentication and export correctness

### Added

- Server-side sessions in an HTTP-only cookie, with PBKDF2-HMAC-SHA256 password hashing, an
  `auth_sessions` table and an Alembic revision.
- `auth/register`: claims an empty workspace and creates the first administrator. Closed as soon
  as a user exists.
- `auth/password`: self-service password change that revokes other sessions.
- API-enforced role policy covering every non-public route, not a per-endpoint opt-in.
- Export audit rows, `X-Row-Count`, a UTF-8 BOM for Excel and a `data_origin` column.
- `tests/test_auth.py`, `tests/test_exports.py`; documentation for backup, performance,
  accessibility, troubleshooting, integration and requirement traceability.

### Fixed

- **"Export failed" on every download.** Only the `admin` role could export while demo entry
  signed reviewers in as a researcher, and the client replaced the server message with a generic
  one. Exports are now available to any signed-in member, the real error is surfaced, an empty
  body is treated as a failure, and success is reported only after the file is created.
- **Demonstration entry could mint a session in production.** `auth/demo` now refuses unless
  `DEMO_MODE=true`.
- **Participant records created through the API were labelled synthetic.** They are real records
  and are now stored with `is_synthetic=false`; only the seed sets it true.
- **Demo entry returned 401 instead of working**, because the route was not in the public path
  list. It is public by design and remains gated by demo mode.

### Changed

- Documentation filenames are now the canonical lowercase set required by the brief; the
  numbered discovery set is retained and annotated where it describes the pre-auth prototype.


## 1.1.0 — Prototype hardening

### Fixed

- **Recruitment history was invisible.** The list endpoint returned records without their
  timeline events and resolved actors only from the last editor, so "View timeline" always
  showed "No history recorded yet". The list now returns events and maps every event actor.
- **Interview-driven stage changes left no audit trail.** Scheduling or completing an interview
  changed the recruitment stage directly, skipping the history event. All stage changes now go
  through one service that appends a `RecruitmentEvent`, including `force` paths.
- **Cross-project evidence could be linked after creation.** The create endpoint enforced the
  rule but the link endpoint did not. Linking now rejects evidence from another project with a
  rule-violation error.
- **Project totals were wrong when filtering by business function.** The total was calculated
  before the in-memory JSON filter. Filtering now happens before pagination.
- **Empty interview summary.** The summary was stored and never rendered. The workspace now
  shows and edits it, clearly separated from notes and from customer evidence.
- **Pie chart was inaccessible.** SVG paths exposed names without an image role, failing
  `svg-img-alt`. The chart now has an accessible name and image role.
- **Terminal recruitment stages had no summary card.** Declines, no-responses, cancellations
  and withdrawals are now visible alongside active stages instead of being hidden.

### Added

- Insight editing (title, summary, interpretation, limitations, confidence) from the detail view.
- Evidence review controls and provenance correction with an explicit "clearing a source never
  strengthens the claim" rule.
- Full journey integration test (`backend/tests/test_journey.py`) covering four segments,
  provenance, contradiction, validation, decisions, actions, search and metric agreement.
- Pipeline metric tests and dashboard/analytics agreement tests.
- Browser journey test that verifies the workflow through the real screens.
- `.dockerignore` excludes `.env` files and caches from the build context.

### Verified

- Backend: 42 passed.
- Frontend: typecheck and build clean.
- Browser: 7 passed, including axe accessibility scan.
- Docker: both images build; API and web healthy; nginx proxy returns 200.

## 1.0.0 — Initial prototype

- Evidence-first research workflow, synthetic seed, FastAPI + React stack, Compose stack,
  initial documentation set and browser smoke tests.
