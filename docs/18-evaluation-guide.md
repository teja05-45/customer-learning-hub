# Evaluation guide

> **Status (2 November 2026).** This document is retained as the original discovery record.
> Password authentication, server-side sessions and API-enforced roles are now implemented;
> statements below that the API has no authentication, or that `X-Demo-User-Id` grants
> identity, no longer describe the code. See [auth.md](auth.md) and [security.md](security.md).

For a reviewer with 20 minutes. Each question names what to click and what a good answer looks
like — and, where relevant, what the prototype does *not* do.

Start at `http://localhost:8081`, pick **Priya Menon**, and reset the demo first
(Settings → Reset).

---

## 1. Can I get from a business claim to a customer's words?

**Do:** Insights → "Price is not the first explanation customers offer" → open the linked
evidence **EV-0007** → follow the interview link.

**Good answer:** two clicks from the claim to the quote, and the quote carries the interview
code, participant code, segment and provenance. The researcher's interpretation sits in its own
field, never in the same paragraph as the quote.

**Red flag if:** the quote and the interpretation share a field, or the source is "interview
notes" with no id.

---

## 2. Can I tell which decisions had no customer evidence?

**Do:** Decisions → filter "No customer evidence". Then open DEC-003.

**Good answer:** the register shows the decision exists, its owner, its rationale, and the fact
that no customer source is linked. It is labelled an internal judgement, not hidden.

**Also check:** DEC-001 links two insights and two evidence records but is still marked
`evidence_sufficient = false` — links and sufficiency are separate judgements.

---

## 3. Does the product survive a contradiction?

**Do:** Evidence → filter type **Contradictory**.

**Good answer:** EV-0006 exists ("I did buy it again actually…"), it is typed as contradictory
evidence, and an insight can link it with role `contradictory` rather than dropping it.

**Red flag if:** contradictions can only be expressed as a normal quote, or are deleted.

---

## 4. Are the analytics honest?

**Do:** Analytics → read the metrics, then the "Measurement gaps" panel.

**Good answer:** every metric states its basis (`calculated`, `observed`,
`pending_baseline`). Three metrics are deliberately not numbers, and the page says research
cannot be credited with repeat-purchase or revenue changes.

**Red flag if:** an "impact score", an ROI figure, or a significance claim appears.

---

## 5. Does the workflow actually connect end to end?

**Do:** Project → participant → recruitment stage → interview → evidence → insight → decision
→ action. Follow one thread (the shampoo study).

**Good answer:** every hop is a click, every record names its parent, and the action has an
owner and a due date. Nothing requires re-entering a name that already exists.

**Check the API, too:** `GET /api/v1/dashboard` returns counts that match what you can count by
hand.

---

## 6. Is anything faked?

**Do:** Read the entry screen, the sidebar banner, Settings → Data, and download any CSV.

**Good answer:** the role picker is labelled a demonstration convenience; the banner and footer
say the data is synthetic; every CSV row carries `is_synthetic=true` and `exported_at`.

**Be sceptical of:** a login form. There isn't one, deliberately — see
[auth.md](auth.md).

---

## 7. Would a researcher actually use it?

**Do:** Interviews → open INT-0005 (scheduled) → look at the workspace: guide questions with
purposes, consent per type, notes, evidence captured in the session.

**Honest answer:** the workspace is usable but slower than typing into a document, because
capture asks for six fields per quote. That trade-off is deliberate (structure over speed) and
named as the fourth limitation in
[17-limitations-and-next-steps.md](17-limitations-and-next-steps.md). If a reviewer says "too
slow in a live interview", they are right, and the fix is already specified.

---

## 8. Is it built, or is it a mock?

**Do:**

```bash
cd backend && .venv/Scripts/python -m pytest -q      # 21 passed
cd frontend && npm run typecheck && npm run build    # clean
cd frontend && E2E_BASE_URL=http://localhost:8081 npx playwright test e2e/smoke.spec.ts
```

Then edit a record in the UI and confirm it appears in `GET /api/v1/dashboard` and in the
activity trail.

**Good answer:** the tests drive the real API and the real production bundle; no mocking layer
exists.

---

## 9. Could this be maintained by someone else?

**Do:** open `backend/app/services/dashboard.py`, `frontend/src/pages/DashboardPage.tsx`, and
`docs/05-data-model.md`.

**Good answer:** the SQL is readable, the page is a composition of primitives, and the data
model document explains *why* the schema is shaped this way. `docs/` has 21 documents including
this one, a runbook and a three-week plan.

---

## 10. What would you do next?

Ask the reviewer to pick one from
[17-limitations-and-next-steps.md](17-limitations-and-next-steps.md). A useful answer names
authentication as blocking and one of the capture-speed or search items as the next product
increment.

---

## Scorecard

| Dimension | Evidence to look for |
| --- | --- |
| Product thinking | Three-layer separation, contradictory evidence, internal-judgement labelling, pending-baseline metrics |
| Craft | 21 API tests, 4 e2e tests, 18 screenshots, 21 docs, `docker compose up` works |
| Honesty | No fake auth, no invented metrics, limitations written down and linked from the product |
| Usability | Every screen has loading/empty/error states; keyboard path works; no horizontal scroll |
| Scope discipline | 15 screens, 17 tables, no audio, no email, no LLM, and a document explaining each exclusion |
