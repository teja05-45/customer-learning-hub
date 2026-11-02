# Roadmap

## Now (delivered prototype)

- Evidence-first research workflow from question to owned action.
- Ten-stage recruitment pipeline with visible segment gaps and append-only history.
- Interview workspace with consent and a server-enforced recording gate.
- Insight review with supporting and contradictory evidence kept visible.
- Decision register that labels internal judgement instead of blocking it.
- Derived dashboard and analytics with metric definitions and pending baselines.
- Deterministic global search with related-research suggestions.
- Docker Compose stack, synthetic seed, 42 backend tests and 7 browser tests.

## Next (0–3 months, before any wider rollout)

1. **Authentication and authorisation** — OIDC/SSO, server-side role checks, session cookies.
   This is the blocker for hosting. See `AUTH.md`.
2. **PostgreSQL** — managed instance, Alembic in the deploy pipeline, connection pooling.
3. **Audit-grade history** — immutable events for evidence deletion, decision changes and
   consent withdrawal; exportable audit view.
4. **Performance and pagination** — push aggregation into SQL, paginate every list, split the
   frontend bundle.
5. **Decision outcome review** — a review date and recorded observed outcome per decision, so
   the business can learn whether the decision worked.
6. **Reuse by team** — attribute decision links to a business function and report reuse per
   function rather than one aggregate rate.

## Later (3–12 months)

- **Coordination baseline**: a one-off time-logging exercise to make "less coordination" a
  measurable claim rather than an opinion.
- **Customer-base comparison**: an aggregate, contact-free segment mix from commerce data to
  compare study coverage against the real base (requires a data-sharing agreement).
- **Peer review workflow**: a second reviewer and a quality checklist outcome per insight.
- **Guided analysis**: optional clustering or summarisation as a *drafting aid*, clearly
  labelled, with provenance retained and no automatic promotion to evidence.
- **Mobile capture**: offline-friendly note capture during interviews, still without audio.
- **Multi-workspace**: organisation scoping if more than one brand adopts the tool.

## Not planned

- Sending real invitations or recording audio.
- Attributing revenue or repeat-purchase change to research activity without a controlled
  experiment.
- Representativeness scoring from small samples.
- Becoming a survey platform; this tool preserves depth, not volume.

## Sequencing logic

Authentication and PostgreSQL are prerequisites for any hosted use. Outcome review and reuse
by team create the evidence needed to justify the tool commercially. Everything else improves
the practice but does not unblock adoption.
