# Git Commit Plan

Commits are grouped by delivered unit, not by file. Subjects are one line, conventional-commit
style, with no body and no attribution, matching the repository's existing history.

## Units delivered in the authentication/export release

| Unit | Intended subject |
| --- | --- |
| Password hashing and session token helpers | `feat(auth): hash passwords and store session digests` |
| Server-side session table and migration | `feat(auth): add server-side sessions` |
| Session middleware covering every route | `feat(auth): require a session for API access` |
| Login, logout, me, password change | `feat(auth): implement password login and logout` |
| Role policy for writes | `feat(auth): enforce roles on every write` |
| First-run registration | `feat(auth): let the first administrator claim an empty workspace` |
| Demo entry gated by demo mode | `fix(auth): disable demonstration entry outside demo mode` |
| Test fixtures rebuilt around sessions | `test(auth): sign in through the real login endpoint` |
| Export permission and error surfacing | `fix(exports): resolve failed CSV download` |
| Export audit, encoding, empty state | `feat(exports): audit downloads and preserve unicode` |
| Export regression suite | `test(exports): cover all eight CSV downloads` |
| Documentation reconciliation | `docs: reconcile authentication and export documentation` |
| Generated data dictionary | `docs(database): generate the data dictionary from the models` |
| Verification evidence | `docs: add verification evidence for this release` |
| Release packaging | `build: package the release source archive` |

## Rules applied

1. Existing history is preserved; no rebase, amend or force push.
2. One commit per unit that leaves the tree in a working state; the test suite was green before
   the commit that adds evidence.
3. No empty or repeated commits, and no commit claiming work that is not in the diff.
4. Only the subject line is written; no descriptions, no agent or tool names, no generated
   attribution.

## Actual history

The authoritative record is `git log --oneline`; the count and final subjects are reported in the
handover summary rather than duplicated here, where they would immediately become stale.
