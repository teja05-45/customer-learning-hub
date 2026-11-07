# Project workflow explanation

This document explains the Customer Learning Hub the way I would explain it in an interview: what the
problem is, how the system is put together, how a piece of customer evidence becomes a measured
business outcome, and which decisions I would defend or revisit.

## 1. In one paragraph

Customer research in most organisations leaks. Findings live in slide decks, quotes are separated from
the decision they informed, contradictory evidence is quietly dropped, and nobody checks whether the
change worked. Customer Learning Hub is a research-operations workspace that keeps one chain intact:
a research project recruits real (here synthetic) customers, records consent, captures interviews or
lighter feedback, turns the raw material into reviewed evidence and insights, connects those insights
to a decision with a named owner and an action, and then measures whether the expected change actually
happened. The product is designed to refuse to flatter weak evidence: small samples are labelled,
unattached decisions are marked as internal judgement, and an outcome cannot be "achieved" without an
actual result.

## 2. Who uses it and what each person needs

| Person | Workspace role | Needs |
| --- | --- | --- |
| Lead researcher / research manager | `researcher` (often project owner) | Plan studies, protect evidence quality, decide who can see a study |
| Researcher | `researcher` | Recruit, schedule, capture evidence, draft insights |
| Product / category manager | `business_owner` | Turn findings into decisions and own follow-through |
| Customer experience / support | `cx` | Read evidence and contribute feedback sources |
| Executive | `ceo` | Read the portfolio and outcomes |
| Workspace administrator | `admin` | Configure the workspace, manage accounts, export |

Two different questions are separated:

- **What kind of work may this person do?** — workspace role (researcher writes research, business
  owner writes decisions, CX does not write, admin configures).
- **Which projects may they do it in?** — project membership (`viewer`, `editor`, `project_owner`).

A request must satisfy both. That is the core authorization design.

## 3. The domain in one picture

```
ResearchProject
  ├── ResearchQuestion
  ├── ProjectMembership ── User
  ├── RecruitmentRecord ── Participant
  ├── Interview ── ConsentRecord
  ├── FeedbackRecord ── (promotes to) Evidence
  ├── Evidence ── InsightEvidence ── Insight
  └── Decision ── DecisionInsight ── Insight
        ├── BusinessAction
        └── Outcome
```

Everything hangs off a project, except participants (workspace-level people) and decisions/insights
that were recorded before being attached. Those orphans are readable only by their owner or an admin
until they are attached — they cannot be used as a back door around project scope.

## 4. The workflow, step by step

### Step 1 — Define the study
A researcher creates a project with an objective, business functions, target segments, dates and the
questions the study must answer. Creating a project makes the creator its `project_owner`, so the
person accountable for the study can immediately add collaborators.

*Design choice:* questions live inside the project rather than in a global backlog. A question that is
not attached to a study is a wish, not research.

### Step 2 — Find customers
The customer directory is searchable by segment, eligibility and purchase context. The profile
aggregates everything known about that person across studies: recruitment history, interviews, evidence
counts, feedback sources and insight links.

*Design choice:* participants are workspace-level because the same person can appear in several
studies. Access is derived from the studies they appear in, not from a `project_id` column on the
person.

### Step 3 — Recruit and consent
Recruitment is a pipeline (`selected → invited → responded → scheduled → completed`, or
`declined`/`no_response`) with append-only stage history and a defined response-rate denominator.

Consent is the most sensitive part. It is append-only: withdrawing adds a record; it never edits the
grant away. Withdrawal has real consequences — future sessions are cancelled, re-booking is blocked,
the participant is flagged, and audit events are written. Previously collected evidence is retained,
because withdrawal stops future contact; it is not a retroactive erasure. A production retention
policy is explicitly out of scope and documented as such.

### Step 4 — Capture the conversation
An interview can be scheduled, rescheduled, cancelled or completed; recording needs a recorded consent.
Asynchronous sources (surveys, support tickets, reviews, imports, written feedback) go into the same
register with a depth label, because a survey is not an interview and should not be presented as one.

### Step 5 — Evidence, not conclusions
Raw material becomes evidence with a provenance snapshot, a type (quote, observation, behaviour, data,
document), a review state and an audit trail. Evidence can support, contradict or contextualise an
insight. Contradictory evidence is a first-class citizen.

*Design choice:* the customer's words and the researcher's interpretation are separate records. An
insight is not "the evidence"; it is a claim linked to evidence with a rationale, a confidence and
stated limitations.

### Step 6 — Insight
An insight carries a statement, confidence, limitations, segments and links to evidence with a role and
a rationale. If the only links are contextual, the UI does not present it as supported.

### Step 7 — Decision and action
A business owner records a decision: problem, rationale, limitations, status. If it has no linked
customer evidence, it is labelled **internal judgement**. Actions have an owner, due date, priority and
status; overdue is derived. A decision may be workspace-level until it is attached to a project.

### Step 8 — Measurement
An outcome has a metric, baseline, target, direction, measurement window, owner and data source. Status
is derived, never hand-set: no result → pending; result plus target → achieved / not achieved;
result without a target → inconclusive; a measured status without a result is rejected. The loop is
closed on the project journey and in analytics, including the gaps where measurement is still missing.

## 5. How the pieces are built

- **Backend:** FastAPI + SQLAlchemy 2.0 + Pydantic, a modular monolith. Routers per domain, schemas at
  the boundary, services for derived logic (journey, dashboard, analytics, serialization), Alembic for
  schema changes.
- **Authorization:** a single `services/access.py` answers "may this user act on this project, at what
  level?" Endpoints call `assert_project_read/write/manage`; list-style reads use
  `visible_project_ids`. The workspace-role middleware remains the first gate. Centralizing this is what
  prevents a new endpoint from inventing a weaker rule.
- **Frontend:** React + TypeScript + Vite. `ProjectProvider` holds the visible projects and the role in
  the selected one; screens are route-lazy-loaded. Bootstrap supplies behaviour, `notion.css` supplies
  the approved visual system; the UI hides controls a role cannot use, but never relies on that.
- **Data:** one SQLite database; demo seed only when explicitly enabled. Migrations are additive. The
  membership migration backfills least privilege rather than granting everyone everything.
- **Tests:** pytest against real HTTP sessions and a temporary database; Playwright against the running
  stack; axe for accessibility; visual checks at four widths.

## 6. Decisions I would defend

1. **Intersection, not replacement.** Workspace roles still decide *what* work is allowed; membership
   decides *where*. Replacing roles with project roles would have broken the existing domain rules.
2. **Admins are implicit owners.** Prevents lockout and reflects how a workspace administrator works.
   The cost is that this is not tenant isolation; a real multi-tenant product needs a layer above.
3. **Least-privilege backfill.** The migration grants only owners, admins and demonstrable
   contributors. The easy alternative — grant everyone everything — would have preserved the
   vulnerability under a new table name.
4. **403, not 404, for a project you cannot access.** Clearer for a single-organisation product; a
   multi-tenant SaaS should prefer 404 to avoid confirming existence.
5. **Withdrawal stops contact, not history.** Erasing lawfully collected evidence is a policy decision,
   not something a prototype should silently do. The limitation is stated.
6. **Derived statuses.** Outcome status, overdue actions and journey stages are computed from records,
   so they cannot drift from the data.
7. **No decorative interactivity.** The journey board is read-only because status changes belong to the
   entity endpoint with its validation. Drag-and-drop would have been a demo trick with weaker rules.

## 7. What I would do next

- Tenant/workspace isolation above project membership (the admin bypass is the remaining boundary
  question).
- Audit events for membership changes (add is logged; role change/removal are not yet).
- A retention/deletion workflow after consent withdrawal, with legal review.
- Indexed search (FTS5 trigram or PostgreSQL `pg_trgm`); the measured full scan is fine at demo size
  but does not scale.
- Frontend component tests; the current frontend verification is end-to-end only.
- Real integrations (support/commerce import) and outreach — deliberately simulated or absent today.

## 8. Eight-minute demo

1. Sign in as **Priya Menon** (researcher) — project, questions, recruitment, sessions.
2. Capture evidence and show a contradictory item; link it to an insight and state the limitation.
3. Sign in as **Rohan** (business owner) — decision and action from that insight.
4. Record the outcome result — show the status is derived.
5. Sign in as **Asha** (CEO) — read-only across projects.
6. Sign in as **Vikram** (CX, editor on one study only) — open a study he has no grant on: `403` and the
   access-denied screen.
7. As Priya, revoke Vikram's membership; reload as Vikram — the project is gone from his list.

## 9. Honest summary

The chain is real and tested, including the security boundary. The remaining gaps are named: no
multi-tenant isolation, no retention automation, no indexed search, no frontend unit tests, and no
external integrations. The project is a coherent single-team product, not a finished SaaS.
