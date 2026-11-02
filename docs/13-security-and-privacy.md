# Security and privacy

A research tool holds what customers said. That is the most sensitive asset here, and the
prototype treats data minimisation as the primary control rather than building a wall it cannot
maintain.

## What is stored

| Stored | Not stored |
| --- | --- |
| Synthetic participant display names and codes | Email, phone, address, government id |
| Segment, purchase frequency, order count, product category | Order numbers, transaction ids, account ids |
| Typed interview notes and verbatim quotes (invented) | Audio, video, transcripts from a real recording |
| Consent decisions per type, with who recorded them | Consent documents, signatures, identity verification |
| Researcher names and roles (invented colleagues) | Passwords, tokens, SSO identities |

There is no column anywhere in the schema for contact data. That is a design decision, not an
oversight: a participant directory that cannot hold an email cannot leak one. The API rejects a
participant payload containing `email` or `phone` by ignoring the unknown fields, and
`test_participant_creation_never_stores_contact_details` asserts the value never appears in the
record or in search results.

## Threat model, in the order that matters for this product

| Threat | Likelihood | Impact | Current state |
| --- | --- | --- | --- |
| Quote attributed to the wrong person | Medium | High — reputational, possibly a consent breach | Provenance fields, interview/participant foreign keys, evidence type separation |
| Claim presented as customer evidence when it was internal judgement | High | High | `evidence_sufficient` on decisions, evidence typed `researcher_interpretation`, honesty notes |
| Unauthorised access to the workspace | High (no auth) | High | **Not mitigated** — see [AUTH.md](AUTH.md) |
| Synthetic data mistaken for real customer data | Medium | Medium | Banner, footer note, `is_synthetic` column, `X-Data-Origin` header, README and docs repeated |
| Person quoted without consent to quote | Medium | High | `consent_records` per type; recording blocked without granted consent |
| SQL injection | Low | High | SQLAlchemy expressions throughout; no raw SQL string interpolation |
| XSS through stored text | Low | Medium | React escapes by default; no `dangerouslySetInnerHTML` anywhere |
| Data retained longer than agreed | Medium | Medium | `retention_months` setting exists but is **not enforced** |
| Loss of the SQLite file | Medium | Medium | Named volume; no automated backup |
| Model or vendor leaking data | None | — | No LLM, no external API, no analytics, no third-party script |

## Controls that exist

- **No third-party requests from the browser.** No fonts, no analytics, no CDN. The app works
  offline once loaded.
- **No raw SQL.** Every query goes through SQLAlchemy; user input reaches the database only as
  bound parameters.
- **Validation at the boundary.** Pydantic models with length limits and enums on every
  request body; FastAPI returns a structured 422 rather than a 500.
- **Consent before recording.** `recording_enabled` cannot be set true unless a
  `recording` consent record is `granted`; the API refuses with an explanatory error.
- **Audit trail.** Every mutation writes an `activity_logs` row with actor, entity and a
  human-readable summary.
- **Labelled exports.** CSV files carry `is_synthetic=true` and an export timestamp so a file
  cannot be mistaken for production data after it leaves the app.
- **Deterministic demo reset.** A reset requires `confirm: true` and the literal phrase
  `RESET`; it is a POST, not a link, so it cannot be triggered by a prefetched URL.
- **No secrets in the repository.** No `.env` file is committed; `.env.example` contains only
  non-sensitive defaults.

## Controls that do not exist (and would block production)

1. **Authentication and authorisation** — everything is public to anyone with network access.
2. **Transport security** — Docker serves plain HTTP; TLS terminates nowhere in this stack.
3. **CSRF protection** — no cookies exist yet, so nothing to protect; the moment session
   cookies arrive, this becomes required.
4. **Rate limiting** — a script could hammer the reset endpoint.
5. **Retention enforcement** — the setting is displayed, not applied. A real implementation
   needs a scheduled job that deletes evidence and consent records past the window, with a
   dry-run and an audit entry.
6. **Backups and restore testing** — SQLite on a Docker volume, no schedule.
7. **Encryption at rest** — whatever the host filesystem provides.
8. **Data subject request handling** — deleting one participant would need to cascade across
   evidence, insights and decisions while preserving the research record. Not built.

## Privacy design choices worth defending

- **Contact details are not modelled.** Recruitment is tracked as stages and outcomes; the
  channel is a label such as "support ticket". This is what a research tool actually needs and
  removes the largest privacy liability in the product.
- **Customer words and researcher interpretation are separate columns.** A summary can never be
  displayed as a quote. This is a correctness control as much as a privacy one.
- **Consent is per type, not one checkbox.** Someone may agree to be interviewed and decline to
  be quoted. The data model can express that, and the UI shows it.
- **Contradictions are kept.** Deleting inconvenient evidence would be the easiest way to make
  a dashboard look good; the schema makes it a link role instead.
- **Nothing is attributed to a real person.** Every record is synthetic, which is what makes it
  safe to host publicly for review — provided the banner is believed.

## If this goes to production tomorrow

Minimum viable change list, in order:

1. SSO or email+password with server-side sessions ([AUTH.md](AUTH.md)).
2. TLS and a hardened proxy in front of nginx.
3. Role checks on every mutating router.
4. Retention job plus a documented deletion path for a participant.
5. Automated backups with a tested restore.
6. Log shipping with actor attribution out of the database and into a system that retains it.

Until then, the honest statement is the one in the UI: this is a demonstration containing
invented data, with no security boundary behind the role picker.
