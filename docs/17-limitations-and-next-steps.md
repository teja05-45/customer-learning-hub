# Limitations and next steps

Ordered by risk, not by excitement. Each item names what is missing, what it would cost, and
what it would change.

## Blocking for any real use

### 1. No authentication or authorisation — `AUTH.md`

Anyone who can reach the URL can read, edit and reset everything. Roles exist as data and are
enforced nowhere.

- **Cost:** 3–5 days with an existing identity provider; ~10 days if passwords and resets are
  built in-house.
- **Change:** the prototype becomes shareable with real colleagues.

### 2. No retention enforcement

`retention_months` is displayed and stored; nothing deletes anything. A research record with
customer words in it should age out on a schedule.

- **Cost:** 2 days (scheduled job, dry-run mode, audit entry, tests).
- **Change:** the privacy story stops being aspirational.

### 3. No backups

SQLite on a Docker volume with no snapshot schedule. A laptop dying loses the workspace.

- **Cost:** hours for a cron-based copy; a day to do it properly with restore rehearsal.
- **Change:** the demo survives a reviewer.

## Weakens the product promise

### 4. Evidence capture is slower than it should be

Type, content, interpretation, segment, provenance, confidence — six fields per quote. In a
live interview that is too slow, so people will type into a notes app and paste later, which is
exactly the fragmentation this tool exists to prevent.

- **Next:** a single-line "quick capture" with sensible defaults (segment and interview
  inherited), provenance auto-filled from the interview code, and a review queue for records
  captured without interpretation.
- **Cost:** 3–4 days including the review queue UI.

### 5. No bulk import or merge

An existing spreadsheet of quotes cannot be brought in, and two insights that say the same
thing cannot be merged without losing one's links.

- **Next:** CSV import with a mapping screen and a dry-run, plus an "merge insights" action that
  moves evidence links and archives the duplicate.
- **Cost:** a week.

### 6. Search cannot tolerate a typo or a synonym

Deterministic substring matching is honest but brittle: "shampo" returns nothing, "scent" does
not find "smell".

- **Next:** PostgreSQL `pg_trgm` for fuzzy matching and a small curated synonym list; keep
  results explainable, no embeddings.
- **Cost:** 2–3 days.

### 7. Charts are not accessible

Both dashboard charts have no text alternative for screen-reader users.

- **Next:** a visually hidden data table per chart, plus `prefers-reduced-motion` handling.
- **Cost:** half a day.

### 8. Mobile is responsive, not designed

The layout collapses correctly and passes the overflow check, but no screen was designed for a
phone. Interviews happen on phones; the interview workspace would be the first to fix.

- **Cost:** 3 days for the two screens that matter (interview workspace, decision detail).

## Correctness and operations

### 9. The Alembic migration is not exercised in CI

`alembic upgrade head` was run against a fresh SQLite file; PostgreSQL behaviour is untested.

- **Next:** a compose profile with Postgres and a migration test in CI.

### 10. No PostgreSQL test matrix

JSON columns and `NULLS LAST` are the two places SQLite and PostgreSQL diverge in this schema.

### 11. Logs are not shipped anywhere

Structured lines go to stdout; in Docker they are readable with `docker compose logs` and are
lost on rotation.

### 12. No rate limiting

The demo reset endpoint is a POST with a confirmation phrase, but nothing stops a script from
calling it repeatedly.

## Deliberately not planned

| Item | Why not |
| --- | --- |
| Audio recording and transcription | Adds a media retention problem, a consent surface and a vendor decision — its own project, not an increment |
| Email or SMS sending | Recruitment would need deliverability, unsubscribe handling and a compliance review; stages are tracked on purpose |
| LLM summarisation of interviews | Would put generated text next to customer quotes and blur the exact distinction the product defends |
| Real customer data import | The schema would need contact fields, which would need the retention and deletion work above first |
| A native mobile app | The web app is responsive; a native app multiplies the surface for no new capability |
| Gamification (streaks, leaderboards) | Research quality is not a game, and the analytics screen already refuses vanity metrics |

## The next four increments

| Increment | Contains | Outcome |
| --- | --- | --- |
| **A. Safe to host** (1 week) | Auth (SSO or password), role checks, retention job, backups | Can be used by the real team |
| **B. Faster capture** (1 week) | Quick capture, review queue, CSV import | The tool survives a live interview week |
| **C. Trustworthy data** (3 days) | Postgres in CI, migration test, fuzzy search | Scales past the demo dataset |
| **D. Login-free review** (2 days) | Shareable read-only insight and decision links with expiry | Business owners stop asking for screenshots |

Increment A is the only one that is not optional.

## What is genuinely good and should not be traded away

- Evidence, interpretation and decision as separate layers.
- Contradictory evidence kept as a first-class link.
- Decisions labelled as internal judgement without shame or disguise.
- Metrics that say "not measured" instead of guessing.
- One deterministic seed shared by the demo, the reset and the tests.

Everything in the list above is an addition. None of it requires relaxing these five.
