# Three-Week FDE Delivery Plan

One forward-deployed engineer, one customer (Everyday Goods), one clickable prototype. The
goal is a defensible demonstration of the core workflow, not a production MVP. Week 3 includes
buffer because integration defects surface late.

## Week 1 — Make the core workflow real

| Day | Work | Exit criterion | Depends on |
| --- | --- | --- | --- |
| 1 | Customer interviews, current-state map, agree the one workflow to prove | Signed-off problem statement and demo script | Customer access |
| 1–2 | Project scaffold, config, database schema, migration, seed harness | API starts, schema migrated, synthetic seed reproducible | — |
| 2–3 | Project CRUD, questions, segments, owner, archive, search/filter | Create → edit → archive works end to end | Schema |
| 3 | Participant directory with data minimisation and eligibility | Create/edit/filter; no contact fields accepted | Projects |
| 3–4 | Recruitment pipeline, transitions, history, coverage | Every stage reachable, history persisted, denominator defined | Participants |
| 4–5 | Interview scheduling, guide, consent, notes, completion | Schedule → consent → complete advances recruitment | Recruitment |
| 5 | Dashboard v1 from records | No hardcoded counters; definitions shown | Interviews + recruitment |

**Risks this week:** schema churn after seeing real data (mitigate with Alembic from day 2);
scope creep into real outreach (hold the "simulated" line explicitly).

**Ownership:** FDE owns all delivery; customer research lead validates the workflow language
by Thursday; customer ops confirms the controlled-outreach assumption.

## Week 2 — Make the learning traceable and usable

| Day | Work | Exit criterion | Depends on |
| --- | --- | --- | --- |
| 6 | Evidence capture with five types, provenance, confidence, review | Unattributed evidence is flagged, never upgraded | Interviews |
| 6–7 | Insight library, create/edit, link/unlink evidence, contradictory role, validation rule | Validation blocked without evidence; contradictions visible | Evidence |
| 7–8 | Decision register with rationale, limitations, links, internal-judgement label | Unevidenced decisions are allowed and labelled, not blocked | Insights |
| 8 | Actions with owner, due date, priority, status, overdue | Complete/block lifecycle persists; overdue derived | Decisions |
| 9 | Global search and related-research suggestions | Insight and its evidence findable from one query | All entities |
| 9–10 | Analytics with basis labels, reuse detail, measurement gaps | Empty data and pending baselines handled honestly | Dashboard |
| 10 | Integration testing: complete journey script | One script executes all 22 steps without manual repair | Everything above |

**Risks:** metric definitions drifting between screens (mitigate with shared services and
`test_metrics.py`); contradictions being deleted (mitigate with explicit warnings and a
confirmation dialog).

**Ownership:** FDE builds; research lead supplies two real (anonymised) examples to validate
the evidence model; business owner reviews the decision form on day 8.

## Week 3 — Harden, verify, hand over

| Day | Work | Exit criterion | Depends on |
| --- | --- | --- | --- |
| 11 | Defect triage and fixes from integration testing | Confirmed defect register closed or explicitly deferred | Week 2 build |
| 11–12 | Security and privacy verification | Data minimisation, consent gate, CSV injection, no secrets | Stable build |
| 12 | Acceptance testing against `ACCEPTANCE_CRITERIA.md` | Every must-have checked with evidence | Defect fixes |
| 12–13 | Docker verification and Windows runbook | `docker compose up --build` works on a clean machine | Compose files |
| 13 | Documentation and handover pack | README, architecture, API, operations, known limits | Verified build |
| 13–14 | Adoption plan: demo script, champion session, feedback loop | Two teams can run the workflow unaided | Handover |
| 14 | Monitoring and rollback plan | Health check, logs, reset procedure documented | Deployment |
| 15 | Buffer and final review | Demo rehearsed end to end; risks restated | All |

**Risks:** Docker differences on the customer's Windows machines (verify early, document the
port), and demo data being mistaken for research (persistent banner, export labels).

**Ownership:** FDE delivers; customer admin owns the hosted environment; research lead owns
adoption; FDE remains on call for two weeks after handover.

## Dependencies

- Access to at least two researchers and one business owner for validation sessions.
- A decision on the controlled Ops outreach process (the tool records intent, never contacts).
- A hosting decision if the prototype will be shared beyond a laptop.
- Agreement that Week 3 is hardening, not new features.

## Definition of done for the engagement

The customer can run the shampoo journey unaided, explain why an insight is or is not
evidence-backed, find prior research before commissioning new work, and state the known
limitations without prompting. The code base and runbook allow another engineer to continue.

See `TASKS.md`, `ROADMAP.md`, `RISKS.md` and `20-three-week-plan.md`.
