# Users and roles

> **Status (2 November 2026).** This document is retained as the original discovery record.
> Password authentication, server-side sessions and API-enforced roles are now implemented;
> statements below that the API has no authentication, or that `X-Demo-User-Id` grants
> identity, no longer describe the code. See [auth.md](auth.md) and [security.md](security.md).

The prototype seeds seven fictional people across five roles. They are switchable from the
demonstration entry screen — one click, no password. That switch is a **UI convenience, not
authentication**: every API request is served with the same permissions regardless of who is
selected. See [auth.md](auth.md).

## The five roles

| Role | Purpose in the product | What they primarily look at |
| --- | --- | --- |
| `researcher` | Runs the study end to end | Projects, recruitment, interview workspace, evidence, insights |
| `business_owner` | Consumes insight and makes the call | Insights awaiting review, decisions, own actions |
| `cx` | Supports assigned coordination work | Recruitment stages, interview scheduling, customer-experience decisions |
| `ceo` | Organisation-level view | Overview, decisions with and without evidence, overdue actions |
| `admin` | Keeps the workspace clean | Settings, exports, demo reset, users |

## Seeded people

| Person | Role | Job title | Why they exist in the demo |
| --- | --- | --- | --- |
| Priya Menon | Researcher | Customer Research Coordinator | The primary user. Owns projects, runs interviews, writes insights. |
| Rohan Iyer | Business owner | Head of Growth | Owns the shampoo repeat-purchase question; receives the size-test decision. |
| Dev Patel | Business owner | Brand & Marketing Lead | Owns the campaign-perception study and its copy decision. |
| Nisha Kulkarni | Business owner | Product & Category Lead | Owns product experience and packaging decisions. |
| Vikram Shetty | CX | Customer Experience Lead | Owns the fulfilment and delivery-exception thread. |
| Asha Menon | CEO | Chief Executive Officer | Reads the overview; asks whether research is used. |
| Arjun Desai | Admin | Operations & Data Support | Manages settings, exports and the demo dataset. |

## What each role is trying to do

### The researcher (Priya)

- Know which study needs attention this week, and what is blocking it.
- Get from a participant to a completed interview without re-entering data.
- Type a quote once, and have it attached to the right interview, participant and segment.
- Draft an insight with the evidence already linked, and see contradictions rather than lose
  them.

Pain avoided: the four-document workflow where the quote, the recording link, the participant
ID and the summary all live in different places.

### The business owner (Rohan, Dev, Nisha)

- See findings that are ready for a decision, with the evidence one click away.
- Register a decision and be honest about whether the evidence supports it.
- Leave with an action that has an owner and a date.

Pain avoided: being handed a 40-slide deck and asked to "sign off" on a direction with no way
to check what customers actually said.

### The CX lead (Vikram)

- See recruitment commitments that affect customers.
- Connect delivery or support failures to the research that describes them.
- Keep the customer-facing decision honest when evidence is thin.

Pain avoided: research findings that never reach the people who talk to customers.

### The CEO (Asha)

- Answer "are we learning anything, and are we using it?" in one screen.
- See where decisions were made without evidence — without blaming individuals.
- See which actions are late.

Pain avoided: research activity reported as a volume metric (interviews conducted) that says
nothing about whether the business changed.

### The admin (Arjun)

- Export a labelled CSV for a meeting.
- Reset the demo between reviewers.
- Keep retention settings visible even though they are not enforced in the prototype.

## Role modelling in code

The API exposes `GET /api/v1/session` returning the seeded people so the entry screen can list
them, and every mutating endpoint accepts an optional `X-Demo-User-Id` header which is used
**only to attribute activity in the audit log**. Nothing is filtered by role, and no endpoint
returns 403 based on role. This is stated on the login screen, in the API description and in
[13-security-and-privacy.md](13-security-and-privacy.md) so no reviewer mistakes it for an
access-control implementation.
