# Final independent recruiter evaluation

Simulated assessment by a senior FDE recruiter. It is based on the running application, the
repository, the executed tests and the screenshots — not on the previous delivery report, which
contained claims that did not survive inspection. This is not a guarantee of a real hiring outcome.

## Verdict

**Recommend selection — 80/100 at the first audit; re-scored 86/100 after the release pass.**

> **Update, 7 November 2026.** The P0 reservation in this assessment has been addressed:
> `ProjectMembership` (viewer/editor/project_owner), an additive migration with a least-privilege
> backfill, a central authorization service, scoped lists/dashboard/analytics/search/exports, a
> membership API and 16 adversarial HTTP tests now exist. The revised scorecard raises Architecture
> 7→9, Backend quality 8→9, Workflow correctness 12→14 and Testing 4→5, but leaves a deduction for
> unindexed search, partial membership auditing, the implicit admin bypass and the absence of frontend
> unit tests: **86/100**. Statements below that say cross-project isolation is absent describe the
> earlier state and are superseded by `authorization-and-permissions.md`.

The candidate built a coherent research system rather than a collection of screens. The strongest
signal is not feature count; it is the refusal to fake certainty: unevidenced decisions are labelled,
small samples are disclosed, outcomes cannot be marked achieved without a result, and consent
withdrawal has real consequences. The main reservation is architectural: there is still no
project-level authorization boundary, which is a P0 for any multi-client enterprise deployment. A
second, smaller reservation is unindexed substring search at scale.

## Scorecard

| Dimension | Weight | Score | Evidence |
| --- | --- | --- | --- |
| Business problem understanding | 10 | 9 | The product is organised around the research-to-decision chain, not around CRUD entities. The overview asks whether anything reached a decision. |
| Requirement discovery | 10 | 8 | Consent lifecycle, provenance, contradictory evidence and outcome measurement are treated as domain requirements. Some briefing claims (palette, test counts) were false and had to be corrected. |
| Workflow correctness | 15 | 12 | Project → recruitment → consent → session → feedback → evidence → insight → decision → action → outcome works through real APIs. Cross-project isolation is absent. |
| Customer experience | 10 | 8 | Consistent workspace, compact typography, useful empty/error states, honest labels. The board requires horizontal scrolling at 1440 px, which is expected for nine stages but not ideal. |
| Product thinking | 10 | 9 | Async feedback is labelled as shallower than interviews; contextual-only evidence cannot present an insight as supported; "inconclusive" exists instead of forcing a binary. |
| Architecture | 10 | 7 | Clear modular monolith, typed contracts, additive migration, derived journey service. No membership model; search strategy does not scale. |
| Backend quality | 10 | 8 | Role-enforced writes, append-only consent, audit events, server-derived outcomes, 122 passing tests. Project scoping remains workspace-wide. |
| Frontend quality | 10 | 8 | Route-level splitting, real API data, accessible labels, responsive layouts. The visual layer had to be rebuilt to match the approved design. |
| Data integrity | 5 | 5 | Constraints, migrations, seed invariants and regression tests; the reversed-window bug was found and fixed. |
| Debugging | 5 | 4 | The candidate reproduced the outcome 400, traced it to seed dates, fixed the cause and added a test; also corrected timeline state derivation. |
| Testing | 5 | 4 | 122 backend, 24 Playwright, axe and four responsive widths. No frontend unit tests; project isolation has no adversarial read tests because the feature does not exist. |
| Communication / honesty | 5 | 4 | Reports now separate verified, unverified and unimplemented work. The initial documentation was overstated, which is itself a credibility risk. |
| Ownership | 5 | 4 | Fixed real defects beyond the brief, verified Docker, documented remaining gaps instead of hiding them. |

Total: **80 / 100**.

## The ten questions

**1. Does it solve the intended business problem?**
Yes. It preserves the customer's words, separates interpretation, keeps contradictory evidence, links
findings to decisions and actions, measures whether the expected change happened, and now separates
teams with project membership. It still does not provide tenant isolation above the workspace.

**2. Can a real research team use it?**
A small team can run the full loop today with synthetic or manually entered data. It cannot connect to
a real commerce or support system, send real outreach or record audio; project membership is now
enforced. The remaining limits are disclosed rather than simulated as complete.

**3. Are the workflows coherent?**
Yes. The same records appear on the project journey, the customer profile, the insight detail and the
decision chain. The journey is derived from the database, so it cannot drift from the records.

**4. Are there hidden operational gaps?**
Two are material: a retention/deletion policy after consent withdrawal and unindexed search. Project
authorization is implemented (with the documented admin bypass); the retention policy is explicitly a
product/legal decision the prototype does not make; search is measured and bounded.

**5. Are there fake or incomplete features?**
No fake outcome results, no decorative drag-and-drop, no static board, no invented metrics. Some
capabilities are incomplete (SSO, real outreach, audio, hosted deployment) and are labelled as such.
The previous report's redesign and test-count claims were false; the current report corrects them.

**6. Can the candidate defend the architecture?**
Yes. The modular monolith, centralized access service, append-only consent and derived journey are
defensible choices for this size. A reviewer should probe the implicit admin ownership and the lack of
membership audit events, both documented.

**7. Does it demonstrate independent problem-solving?**
Yes. The candidate found and fixed a seed bug that broke outcome recording, corrected hard-coded
timeline states, measured the search plan instead of adding a useless index, and rebuilt the visual
layer to the actual approved tokens.

**8. What would make an evaluator reject the submission?**
Claiming tenant isolation because project membership exists; claiming WCAG conformance from axe alone;
claiming Docker or deployment success without running it; or leaving earlier false claims
uncorrected. Those are now explicit limitations.

**9. What should be fixed before submission?**
1. ~~Implement `project_memberships` and enforce it on every read and write; add adversarial tests.~~
   Done in the release pass.
2. Add the FTS5 trigram (or PostgreSQL trigram) search path with before/after measurements.
3. Add a frontend unit/component test layer; Playwright alone leaves form-level logic thinly covered.
4. Add explicit retention/deletion behaviour for withdrawn consent, or state that it is an
   organisational policy outside the product.
5. Audit membership role changes and removals (adds are already logged).

**10. Would you recommend selecting this candidate?**
Yes, with the conditions above. The work shows product judgment and engineering honesty beyond a
typical portfolio submission. The P0 authorization gap is the difference between "strong demo" and
"enterprise-ready", and it should be the first topic in the interview.

## Evidence reviewed

- `backend/tests/` — 122 passing tests, including consent withdrawal, outcomes, journey and
  cross-project relationship refusal.
- `frontend/e2e/` — 24 passing Playwright tests against the Docker build, including axe and four
  viewport widths.
- `docs/screenshots/` — 27 screenshots captured after real data loaded, including the new journey,
  outcomes, profile and consent dialog.
- `compose.yaml` — both images built, both containers healthy, write survived a backend restart.
- `git log` — no redesign commit exists; the theme claim was corrected in this pass.

## What would move the score to 90+

Membership audit events, an indexed search path with measurements, and a small component test layer.
Nothing in the current design prevents those; they are scope, not dead ends.

## Re-score after the release pass

| Dimension | Old | New | Why |
| --- | --- | --- | --- |
| Workflow correctness | 12 | 14 | Cross-project workflows now refuse unauthorized records and links |
| Architecture | 7 | 9 | Explicit membership model, centralized enforcement, additive backfill |
| Backend quality | 8 | 9 | 16 adversarial tests and consistent scoping of aggregates and exports |
| Testing | 4 | 5 | Adversarial authorization coverage, including revocation |
| Other dimensions | unchanged | unchanged | — |
| **Total** | **80** | **86** | Remaining deductions: search, audit gaps, frontend unit tests, admin bypass |
