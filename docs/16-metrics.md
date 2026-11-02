# Metrics

The analytics screen reports eleven measurements, each carrying a **basis**: `calculated`,
`observed`, or `pending_baseline`. That field is the point of the screen. A number without its
basis is an opinion in a chart.

Everything below is what the API returns today on the seeded dataset
(`GET /api/v1/analytics`, `GET /api/v1/dashboard`).

## Calculated from records in this workspace

| Metric | Seeded value | Definition | Why it is measured this way |
| --- | --- | --- | --- |
| Research reuse rate | 50% (2/4) | Share of insights linked to a later decision — a second decision, or one linked ≥14 days after the insight was written | Reuse, not volume, is what separates research from a report. The 14-day rule prevents a decision that cited an insight on the same afternoon from counting as reuse |
| Decisions backed by customer evidence | 75% (3/4) | Decisions with ≥1 linked insight or evidence / all decisions | The register exposes the ones without; this number makes the gap impossible to ignore |
| Findings traceable to source evidence | 100% (4/4) | Insights with ≥1 linked evidence / all insights | Traceability is the product promise, so it gets a number |
| Follow-up action completion | 29% (2/7), 0 of 2 on time | Completed actions / all actions, plus an on-time note | Volume of actions is meaningless; completion and lateness are not |
| Time from evidence capture to decision | 20 days (median) | Median days between earliest linked evidence and the decision | Shorter is not automatically better — the definition says so, because a fast decision may rest on too little |
| Recruitment response rate | 75% (9/12) | Participants who replied / participants actually invited | Only invited people are in the denominator; declines count as responses, because a clear no is more useful than silence |

## Observed counts

| Metric | Seeded value | Note shown in the product |
| --- | --- | --- |
| Interviews completed | 7 | "Volume is a workload signal, not evidence of understanding." |
| Evidence records captured | 13 (1 without full provenance) | Provenance gaps are counted next to the total, never hidden |
| Unresolved research questions | 8 of 12 | A study can close with questions deliberately unanswered |

## Pending baseline — deliberately not shown as numbers

| Metric | Displayed as | Definition text |
| --- | --- | --- |
| Research coordination time | **Not measured** | "The product does not yet capture this, and estimating it would be guesswork." Target: a four-week logging baseline |
| How representative a study is | **Not calculated** | "A percentage would imply statistical confidence the sample does not have." Use segment coverage instead |
| Commercial impact (repeat purchase, revenue) | **Not attributable** | "Repeat purchase has many causes. Attributing a change to research activity would require a controlled experiment per decision" |

Each gap carries a `how_to_collect` suggestion, so "not measured" is a plan rather than a shrug.

## Segment coverage, not sample scores

`segment_distribution` reports participants, interviews and evidence per segment
(`first_time_buyer`, `repeat_buyer`, `lapsed_buyer`, `household_buyer`, `unknown`). The seeded
data shows the honest failure a small team has: one `unknown` evidence record and lapsed buyers
over-represented in evidence relative to their participant count.

The dashboard shows the same table with a written reading of what it means, because a bar chart
of five small numbers invites over-interpretation.

## What the product refuses to report

- **An "impact score".** No combination of these records justifies one.
- **Interviews per week as a success metric.** It is a workload signal, labelled as such.
- **Statistical significance.** Ten participants cannot support it, and a p-value would be used
  as a weapon in a meeting.
- **Attribution of revenue or repeat purchase to research.** Stated on the screen itself.
- **A satisfaction or NPS figure for the research team.** Nobody asked, and it would be gamed.

## Dashboard signals

The overview shows six stat cards plus two "are we learning something useful" indicators:

| Signal | Source | Warning state |
| --- | --- | --- |
| Active research projects | Projects not archived/completed | — |
| Interviews completed / upcoming | Interview status + scheduled date | — |
| Participants contacted | Recruitment stages past `invited` | — |
| Response rate | replied / invited, with denominator | Sample warning when the denominator is small |
| Insights awaiting review | `draft` + `under_review` | Amber when > 0 |
| Decisions with evidence | decisions with ≥1 link / all decisions | — |
| Open actions | not `completed` | Amber with overdue count |
| Evidence records | Sum across segments | — |

The response-rate card is the one worth copying elsewhere: the API returns the numerator,
denominator and a `definition` string, so the UI cannot render a bare percentage. Small-sample
warnings are likewise computed server-side, not guessed in the browser.

## How a team would use this

1. **Weekly:** insights awaiting review, overdue actions. Ten minutes.
2. **Monthly:** reuse rate and decisions-with-evidence. If reuse is low, the problem is the
   insight format or the decision process, not the research volume.
3. **Quarterly:** pick one `pending_baseline` metric and start measuring it properly. The
   measurement-gaps list is ordered by how cheaply it could be collected.

The metric that would change behaviour most is coordination time, and it is exactly the one
that cannot be computed from these records — which is why it is listed as a baseline project
rather than estimated.
