# Integrations

## Status: none configured

This release has **no third-party integration**. That is a deliberate, verified statement: there
is no email provider, calendar sync, object storage, identity provider or LLM call in the code.
`backend/requirements.txt` contains no provider SDK, and the frontend bundle contains no API key.

The product was built so that the workflow does not depend on one:

| Candidate | Why it is not integrated | What the product does instead |
| --- | --- | --- |
| Email (invitations, reminders) | Sending real customer email requires a verified domain, a consent record and a human approval step | Recruitment stages record that an invitation happened; the team sends it through its existing controlled process |
| Calendar (Google/Microsoft) | OAuth app review and per-user tokens are out of scope | Interviews store `scheduled_at`; the UI shows the schedule |
| File storage (S3) | No audio or attachments are captured | Notes and summaries are text fields in the database |
| Identity provider | No tenant exists to configure one | Email + password sessions (`auth.md`) |
| AI assistance | Sending customer quotes to a model is a privacy decision the organisation must make explicitly | Insights are written and validated by people; nothing is auto-validated |

## Adding an integration: required contract

Every future integration must satisfy all of the following before it ships.

1. **Explicit enablement.** A setting such as `RESEND_API_KEY` with no default. When the variable
   is absent the feature is visibly disabled in the UI and the API returns a documented `503`
   `integration_not_configured`, never a silent success.
2. **No automatic outreach.** Invitations, reminders and summaries are only sent after an
   authenticated user confirms the specific recipients and content. Bulk sending is not a default.
3. **Credentials server-side only.** Provider keys live in the backend environment, never in the
   React bundle, the database or a CSV export.
4. **Timeouts and retries.** A bounded timeout (for example 10 s) and at most two retries with
   backoff for idempotent calls. Failures are logged with the provider status, not the payload.
5. **Audit.** Every attempt writes an `activity_logs` row (success or failure) naming the actor and
   the entity, so "we emailed them" is verifiable.
6. **Tests.** At minimum: disabled state, happy path against a stub, timeout path, and permission
   check. No test may require a real provider key.
7. **Data minimisation.** Only the fields the provider needs are sent. Participant contact values
   do not exist in this schema, so an email integration would first require a deliberate privacy
   review and a new, encrypted contact store — not a field bolted onto `participants`.

## Related documents

- `auth.md` — identity provider as the alternative to local passwords.
- `security.md` — data protection and the threat model.
- `prd.md` — out-of-scope items.
