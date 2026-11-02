# Product Requirements — Customer Learning Hub

## 1. Business problem

Everyday Goods sells personal-care products. Its teams run customer conversations, but the
learning from those conversations is hard to coordinate, hard to find later, and easy to
overstate. Six failures recur:

1. Research is commissioned per team, with no shared place to see what is already known.
2. Nobody can tell a customer's words from a researcher's interpretation after the fact.
3. Contradictory evidence is quietly dropped when a finding is written up.
4. Recruitment is a list of willing people, not a view of who is missing.
5. Insights do not reliably reach a decision, and decisions do not reliably produce owners.
6. Numbers shown to leadership ("we spoke to 12 customers") imply more than the sample supports.

The product does not try to automate research. It makes the research record honest, traceable
and reusable.

## 2. Users

| Role | Job to be done | What they need from the product |
| --- | --- | --- |
| Researcher | Run a study end to end | Projects, participants, recruitment, interviews, evidence |
| Business owner | Decide with customer context | Reviewed insights, decision register, owned follow-ups |
| CEO / leadership | See whether learning is used | Honest dashboards, reuse and evidence-coverage signals |
| CX / Ops | Support outreach and scheduling | Assigned recruitment tasks, no contact data in the tool |
| Admin | Keep the workspace healthy | Settings, exports, demo reset, retention configuration |

The prototype uses a demonstration role picker. It is a reviewer convenience, **not**
authentication or authorisation; see `auth.md`.

## 3. Core workflow

```
Research question → Project → Participant recruitment → Interview
        → Evidence (verbatim, observation, interpretation, contradiction)
        → Insight → Decision → Action
```

Each arrow is a stored relationship, not a UI sequence. Deleting or archiving an upstream
record must not silently make a downstream claim look stronger.

## 4. Requirements

### 4.1 Projects
Create from a template or blank; edit scope, questions, owner, segments and dates; archive;
search and filter. Archiving never deletes evidence or insights.

### 4.2 Participants
Synthetic directory with segment, purchase context and eligibility. No email, phone or
address is accepted by the API. Every record is labelled `is_synthetic`.

### 4.3 Recruitment
Ten-stage pipeline: identified, selected, invited, responded, scheduled, completed, declined,
no response, cancelled, withdrawn. Every transition is appended to a history timeline.
Response-rate denominator counts participants who were actually invited.

### 4.4 Interviews
Schedule, reschedule, cancel, complete. Neutral guide attached by default. Consent recorded
separately. Recording is off by default and no audio is captured.

### 4.5 Evidence
Five types: verbatim quote, observation, researcher interpretation, contradictory evidence,
open question. Provenance is mandatory for a record to count as verified; missing provenance
is flagged and confidence is forced to low rather than silently upgraded.

### 4.6 Insights
Create, edit, link and unlink evidence, mark evidence as supporting or contradictory, set
confidence and limitations, and review. Validation requires at least one linked evidence item.
"Validated for internal use" means a person reviewed the evidence — never statistical
representativeness.

### 4.7 Decisions
Business problem, rationale, linked insights/evidence, owner, date, status, limitations.
A decision may be recorded without evidence; it is then labelled an internal judgement rather
than blocked.

### 4.8 Actions
Owner, due date, priority, status (not started, in progress, blocked, completed), overdue
tracking. Actions stay linked to their decision.

### 4.9 Dashboard, analytics and search
All figures are derived from records. Definitions travel with the metric. Metrics with no
baseline are shown as "pending baseline" rather than invented. Search is deterministic keyword
matching across projects, participants, interviews, evidence, insights, decisions and actions.

## 5. Non-goals

- No real customer contact, email sending, audio recording or CRM integration.
- No attribution of revenue or repeat-purchase change to research activity.
- No statistical representativeness claim from a small sample.
- No production authentication in this prototype.

## 6. Success signals

- Evidence coverage: share of insights with at least one linked source.
- Decision traceability: share of decisions with a linked insight or evidence record.
- Research reuse: share of insights used in two or more decisions or reused after 14 days.
- Recruitment honesty: segment gaps visible before a finding is written.
- Follow-up ownership: actions with an owner and a due date, and overdue items visible.

These are calculated in `backend/app/services/dashboard.py` and
`backend/app/services/analytics.py`, and verified in `backend/tests/test_metrics.py`.

## 7. Related documents

`01-product-brief.md`, `03-core-workflows.md`, `acceptance_criteria.md`, `../README.md`.
