# Trade-offs and decisions

> **Status (2 November 2026).** This document is retained as the original discovery record.
> Password authentication, server-side sessions and API-enforced roles are now implemented;
> statements below that the API has no authentication, or that `X-Demo-User-Id` grants
> identity, no longer describe the code. See [auth.md](auth.md) and [security.md](security.md).

Every significant choice, what it bought, and what was rejected. Ordered roughly by how much
the project would change if the decision were reversed.

## 1. Evidence, interpretation and decision are three separate layers

**Chosen:** `evidence.content` (what was said), `evidence.interpretation` and `insights.summary`
(what we read into it), `decisions.*` (what we decided) are separate fields and separate
tables.

**Rejected:** one "note" field per interview, and an insight that embeds its quotes as
markdown.

**Bought:** a claim cannot be rendered as a quote by accident; a decision can be audited
against the evidence under it; contradictions can be linked rather than lost.

**Cost:** more clicks when capturing (type, content, interpretation, segment, provenance) and a
schedule of five tables instead of two. Accepted: the product's whole value is this separation.

## 2. No authentication, stated loudly

**Chosen:** a role picker that writes a user id to `localStorage`, with the absence of security
documented on the entry screen, in the API description, and in [AUTH.md](AUTH.md).

**Rejected:** a fake login (any password accepted), UI-only role checks, or spending the three
weeks on auth.

**Bought:** the budget went to the research workflow, which is what is being evaluated. No
reviewer can believe there is protection that is not there.

**Cost:** the prototype cannot be shown with real data, or hosted publicly without a proxy
password. Mitigations and a concrete migration path are in [AUTH.md](AUTH.md).

## 3. SQLite by default, PostgreSQL by configuration

**Chosen:** SQLite file on a Docker volume; `DATABASE_URL` switches to PostgreSQL; Alembic
migration covers both.

**Rejected:** Postgres in Compose from day one.

**Bought:** `docker compose up` needs one container instead of three, no credentials, no
wait-for-database logic, and a demo reset is a file copy.

**Cost:** no concurrent-write story, `NULLS LAST` and JSON columns behave differently, and the
migration has not been exercised against Postgres in CI. Documented in
[12-deployment.md](12-deployment.md).

## 4. Enums as strings, not database enums

**Chosen:** `String(24)` columns with values validated by Pydantic and by Python enums.

**Rejected:** SQL `ENUM` types or `CHECK` constraints per column.

**Bought:** adding a value requires a deploy, not a migration; the same schema runs on SQLite
and PostgreSQL; inserts from a seed script are trivial.

**Cost:** the database will accept an invalid value if it bypasses the API. Accepted for a
prototype; the API is the only writer.

## 5. Denormalised `project_id` on evidence, insights, decisions, actions

**Chosen:** child records carry `project_id` even though it is reachable through the interview
or the insight.

**Rejected:** always joining through parents.

**Bought:** every list filter (`?project_id=`) is one indexed column, and the project detail
page is a handful of cheap queries instead of a join tree.

**Cost:** consistency must be enforced on write, and a future "move evidence to another
project" operation has to update two rows. Verified by
`test_evidence_without_provenance_is_flagged` and the create validators.

## 6. One dashboard endpoint, not eleven resource calls

**Chosen:** `GET /dashboard` returns a flat payload shaped for the overview screen.

**Rejected:** the frontend composing eleven queries with `react-query`.

**Bought:** one request, one loading state, one place where "what the CEO sees" is defined, and
counts that cannot disagree with each other.

**Cost:** the endpoint is screen-shaped, so a second consumer would either reuse it awkwardly
or need its own. Accepted: there is no second consumer.

## 7. Deterministic keyword search, no embeddings

**Chosen:** all words in the query must appear in a searchable column; results grouped by entity
type; suggestions offered when nothing matches.

**Rejected:** Postgres full-text search, a vector store, or an LLM summary of results.

**Bought:** explainable results, no infrastructure, no API key, no chance of a fabricated hit,
and instant response. A reviewer can predict what a query will return.

**Cost:** no stemming, no synonyms, no typo tolerance. "shampoo" finds the study; "shampo"
does not. Documented as a known gap with the upgrade path (pg_trgm).

## 8. Analytics that refuse to attribute causality

**Chosen:** metrics describe coverage and traceability; anything the business has not defined is
marked **pending baseline**; the screen states that research cannot be credited with
repeat-purchase or revenue changes.

**Rejected:** a "research impact score", an ROI estimate, or a chart of revenue against
interviews.

**Bought:** credibility. The numbers can be defended in a meeting, and the empty ones are
visibly empty rather than invented.

**Cost:** the analytics screen looks less impressive than a dashboard full of fabricated
correlations. Accepted deliberately — see [16-metrics.md](16-metrics.md).

## 9. Typed notes, not audio

**Chosen:** the interview workspace stores typed notes, a summary and follow-ups. Recording is
a boolean gated on consent.

**Rejected:** browser audio capture, upload, or transcription.

**Bought:** no storage pipeline, no retention problem for media, no consent complexity beyond a
record, and no risk of a real voice in a demo.

**Cost:** the tool is slower to use in a live interview than a recorder. A real product would
need audio with retention rules; that is named in
[17-limitations-and-next-steps.md](17-limitations-and-next-steps.md).

## 10. Bootstrap + a hand-written layer, not a component library

**Chosen:** `react-bootstrap` for behaviour, `app.css` (~1.4k lines) for identity, ~15
primitives in `ui.tsx`.

**Rejected:** MUI, Ant, shadcn, Tailwind.

**Bought:** no build-time CSS pipeline to configure, full control of the information-dense
layouts this product needs, and a small dependency surface that a reviewer can read.

**Cost:** more CSS written by hand, and no free accessibility polish from a mature library;
several gaps in [14-accessibility.md](14-accessibility.md) would have been closed for free.

## 11. React Query for server state, no global store

**Chosen:** `@tanstack/react-query` with entity-shaped keys and targeted invalidation.

**Rejected:** Redux, Zustand, or hand-rolled context per entity.

**Bought:** caching, background refetch, and a loading/error model that maps directly to the
five-state screens.

**Cost:** invalidation is a manual discipline; forgetting one key leaves a stale panel. The e2e
smoke test's "no console errors" and the flow tests catch the obvious cases.

## 12. Two levels of navigation, fifteen screens

**Chosen:** flat sidebar with two labelled groups.

**Rejected:** nested menus, a workspace switcher, tabs inside tabs.

**Bought:** every destination is one click, and the counts in the sidebar are the same numbers
as the overview.

**Cost:** the sidebar will not scale to fifty screens. Fine for a ten-person team.

## 13. Tests at the seam, not everywhere

**Chosen:** 21 API tests including one full journey, 4 Playwright tests covering all ten
screens plus keyboard navigation, plus screenshot capture. No component unit tests.

**Rejected:** a unit-test pyramid, snapshot tests, mocked API clients.

**Bought:** tests that fail when the product is broken rather than when a component's internals
change, and a suite that runs in seconds.

**Cost:** no fast feedback on component logic; a broken component is caught by an e2e failure
that is slower to diagnose. See [11-testing.md](11-testing.md).

## 14. One documented, deterministic seed

**Chosen:** a single `seed_demo_data()` used by startup, the reset endpoint and the tests, with
dates relative to "now".

**Rejected:** fixtures per test, or a SQL dump.

**Bought:** the demo, the tests and the reset all agree; the dataset never looks stale because
dates are computed at seed time.

**Cost:** the dataset is opinionated and small (~70 rows). Changing a name means updating
documentation that quotes it — accepted, and the demo script does quote it.

## 15. Honest labelling everywhere

**Chosen:** synthetic-data banner, `is_synthetic` in every export, `X-Data-Origin` header,
"internal judgement" labels on decisions, "pending baseline" on unmeasured metrics, and
limitations sections in the product and in the docs.

**Rejected:** a cleaner-looking surface without the caveats.

**Bought:** the prototype can be judged on what it does rather than on what it claims.

**Cost:** slightly more chrome on every screen. The alternative — being trusted once and losing
it — costs more.
