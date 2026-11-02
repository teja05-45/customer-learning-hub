# Product brief

## The problem

Everyday Goods sells household and personal-care products. The team already talks to
customers — a researcher runs eight interviews about a shampoo that people do not buy twice,
someone in CX hears the same complaint three times in a week, a campaign lands and nobody is
sure why. The learning exists. It just does not survive.

Three failures repeat:

1. **The evidence disappears.** Quotes live in a document, a slide deck and someone's notes.
   Six weeks later the claim "customers found the scent too strong" cannot be traced back to
   which customers, in which study, at what point in the conversation.
2. **Interpretation is dressed up as fact.** A researcher's summary and a customer's actual
   words are stored in the same paragraph. Readers cannot tell which is which.
3. **Decisions float free of research.** A decision gets made in a meeting, an insight is
   cited afterwards to justify it, and the link is invisible. Nobody can say which decisions
   had customer evidence and which were internal judgement.

## The promise

> Turn customer conversations into decisions you can defend.

The prototype keeps three things separate and joins them explicitly:

- **What the customer said** — verbatim quote, observation, or researcher interpretation,
  each labelled as one of the three, each attached to an interview and a participant.
- **What we concluded** — an insight, with the evidence behind it linked many-to-many, plus
  confidence, limitations and a review status.
- **What we decided** — a decision that links to insights and evidence, or explicitly records
  that it rests on internal judgement rather than research.

Every screen is designed so a reader can answer: *where did this claim come from, and who
owns the next step?*

## Who it is for

A ten-person consumer business with one researcher and no research-operations team. The
primary user is that researcher. The secondary users are the business owners who consume the
output and the CEO who wants to know whether research is being used. See
[02-users-and-roles.md](02-users-and-roles.md).

## In scope for this prototype

- Project and research-question planning, including four templates.
- Participant directory with segment and purchase context, deliberately without contact data.
- A recruitment pipeline with ten stages and an explicit next action per participant.
- Interview scheduling, consent capture, a guided interview workspace, note taking.
- Evidence capture with provenance, type separation and segment tagging.
- Insight drafting with evidence linking, confidence, limitations and review.
- A decision register that links to sources or records their absence.
- Follow-up actions with owner, due date and status.
- A dashboard, learning analytics, global search, CSV export, and a demo reset.

## Out of scope, on purpose

| Not built | Why |
| --- | --- |
| Authentication and permissions | The brief is a demonstration; pretending to have security would be worse than being explicit. See [auth.md](auth.md). |
| Audio recording or transcription | Consent, storage and retention for audio is a separate product problem; the prototype stores typed notes only. |
| Email or SMS sending | Recruitment stages are tracked, not dispatched. No channel integration, no deliverability, no unsubscribe handling. |
| Real customer data or integrations | No Everyday Goods system is touched. All people, conversations and outcomes are invented. |
| Statistical analysis | With ten synthetic participants, significance testing would be theatre. The app reports coverage and counts, not p-values. |
| Attribution of revenue or repeat purchase | Research cannot be credited with a commercial outcome from these records. The analytics screen says so instead of guessing. |
| Mobile app, offline mode, real-time collaboration | Out of scope for a three-week prototype; the web app is responsive instead. |

## What success looks like

For the reviewer, in one session:

- Trace a business decision back to a customer quote in under a minute.
- See, on the dashboard, how many decisions have evidence behind them and how many do not.
- Notice that the product says "pending baseline" where it does not know a number, rather
  than inventing one.
- Finish believing the team could run next week's study in this tool rather than in four
  documents and a spreadsheet.

## Constraints honoured

- **Runs from a clean machine** with `docker compose up --build`, no manual seeding.
- **Synthetic data only**, deterministic and dated relative to "now" so the demo never looks
  stale.
- **Honest surfaces** — every uncertain number is labelled, every missing capability is
  documented rather than faked.
