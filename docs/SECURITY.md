# Security and Data Protection

## Scope statement

This is a portfolio prototype. It handles **synthetic data only**, connects to no customer
system, sends no email, captures no audio and stores no contact details. It is not safe to
expose on the public internet as-is because there is no authentication or authorisation.

## Data minimisation

- The participant schema accepts no email, phone or address. Extra fields sent to the API are
  ignored by Pydantic, not stored, and therefore cannot leak through search or export.
- `contact_route` describes *how* a controlled Ops process would reach someone (for example
  "Controlled export batch #12"), never the contact value itself.
- Interviews store notes and a summary, not audio or transcript files.
- Recording is disabled by default, no audio is captured, and the recording flag cannot be
  enabled without a granted `recording` consent record (enforced server-side in two endpoints).

## Consent

`consent_records` stores participation, recording, quoting and internal-sharing decisions with
status, actor, timestamp and note. Consent is append-only: changing a decision adds a record
rather than rewriting history. The interview's derived `consent_status` reflects participation.

## Validation and integrity

- All input is validated by Pydantic schemas: lengths, enums, bounded integers and dates.
- Business rules are enforced server-side, not only in React: transition maps, insight
  validation requiring evidence, cross-project evidence rejection, recording consent gate,
  deadline-after-start-date, duplicate link protection.
- Database foreign keys are enabled on SQLite; cascades and `SET NULL` behaviour are explicit.
- Transactions commit once per successful request; failures roll back.

## Output safety

- CSV exports neutralise spreadsheet formula injection by prefixing cells beginning with
  `=`, `+`, `-`, `@`, tab or carriage return, and label every file/row `is_synthetic`.
- JSON responses are typed; no HTML is rendered from user content without React escaping.
- Error messages do not include stack traces or SQL.

## Configuration and secrets

- Configuration is environment-driven (`app/core/config.py`) with safe defaults.
- No API keys exist in the repository or the frontend bundle. There is no LLM integration.
- `.env` files are gitignored; `.env.example` documents variable names only.
- Docker Compose passes only non-secret demo settings.

## Logging

Structured logs include request outcome and seed status. They intentionally exclude participant
names, evidence text, notes and contact routes. Activity summaries are business-facing audit
entries, not a debug log.

## Threats considered

| Threat | Mitigation | Residual risk |
| --- | --- | --- |
| Presenting synthetic data as real research | Persistent demo banner, `is_synthetic` flags, export labels, documentation | Reviewer could screenshot without context |
| Claiming statistical representativeness | No representativeness metric; warnings on small samples; insight validation is explicitly internal | A human can still overstate in a slide |
| Unattributed claim becoming "evidence" | Missing provenance forces flagged status and low confidence | A user can type a false provenance string |
| Deleting contradictory evidence | UI warns; deletion is explicit and confirmed; insight count drops visibly | No immutable audit trail in this prototype |
| PII entering the system | Schema rejects contact fields | Free-text notes could contain names typed by a user |
| Unauthorised access | None — demo only | **Must add authentication before deployment** |
| CSV formula injection | Cell prefixing | Other export formats not implemented |

## Production prerequisites

1. Authentication (OIDC or equivalent) and server-side role enforcement.
2. Per-organisation data scoping and an audit-retention policy.
3. Encrypted transport and storage; secrets in a managed secret store.
4. Rate limiting and request-size limits at the edge.
5. A real retention/deletion job aligned with `retention_months` in settings.
6. Immutable audit logging for evidence deletion and decision changes.
7. Privacy review of free-text fields and a documented data-classification policy.

See `AUTH.md`, `13-security-and-privacy.md` and `RISKS.md`.
