# Information architecture

## Screen map

```
Demonstration entry (/)
└── App shell (persistent sidebar + top bar + command search)
    ├── Overview                     /
    ├── Research
    │   ├── Projects                 /projects
    │   │   ├── New project          /projects/new
    │   │   └── Project detail       /projects/:projectId
    │   ├── Participants             /participants
    │   │   └── Participant detail   /participants/:participantId
    │   ├── Recruitment              /recruitment
    │   └── Interviews               /interviews
    │       └── Interview workspace  /interviews/:interviewId
    ├── Learning
    │   ├── Evidence                 /evidence
    │   │   └── Evidence detail      /evidence/:evidenceId
    │   ├── Insights                 /insights
    │   │   └── Insight detail       /insights/:insightId
    │   └── Analytics                /analytics
    ├── Delivery
    │   ├── Decisions                /decisions
    │   │   └── Decision detail      /decisions/:decisionId
    │   └── Actions                  /actions
    └── Workspace
        └── Settings                 /settings
```

Unknown routes render a "Page not found" screen inside the shell, with a link back to the
overview — not a dead end and not a blank page.

## Navigation rules

- **Two levels only.** Fifteen screens is small enough that every destination is one click
  away; collapsing Learning and Delivery hides the two things the product exists to do.
- **Counts in the sidebar** come from the dashboard payload, so "Insights" shows how many are
  awaiting review, and "Actions" how many are overdue. Counts are the same numbers the
  overview shows — one source of truth.
- **The shell persists.** Filters, the search box and the connected "role" stay mounted while
  the content area changes.
- **The synthetic-data banner** sits above the content and can be hidden in Settings, but the
  footer note and the `is_synthetic` columns in exports remain.

## Cross-linking contract

Every entity screen links to its neighbours so a reader can move from claim to source without
a search:

| From | Links to |
| --- | --- |
| Project | Its questions, participants, interviews, evidence, insights, decisions, actions |
| Participant | Their recruitment records, interviews, evidence |
| Interview | Participant, project, evidence captured, consent records |
| Evidence | Interview, participant, project, the insights it supports or contradicts |
| Insight | Project, linked evidence (with roles), the decisions that used it |
| Decision | Project, linked insights and evidence, its actions, the owner |
| Action | The decision or insight that created it, the owner |

The rule behind the contract: **a claim is never more than two clicks from its source.** If a
screen cannot honour that, it shows the reason (for example an insight with no linked evidence
says "no evidence linked yet" instead of leaving the section out).

## Content hierarchy on a detail screen

1. Title, code, status and the primary action.
2. The one-paragraph reason this record matters (objective, problem statement, summary).
3. The evidence or source block.
4. Provenance and confidence metadata.
5. Activity and history.

## URL and state rules

- URLs are the state for entity selection (`/insights/INS-0001`), so any record can be shared
  in a message and opened directly.
- Filters live in component state, not the URL, except the global search query which lives in
  the search panel. This keeps the URL space predictable for a demo.
- The selected role is the only persisted preference (`localStorage.clh.demoUserId`), so a
  reviewer can refresh mid-demo and stay where they were.

## Empty, loading and error states

| State | Treatment |
| --- | --- |
| Loading | Skeleton rows with a sentence explaining what is being calculated ("Calculating learning signals from the evidence record…") |
| Empty (no records yet) | A named empty state with the next action, never a blank table |
| Empty (filtered to nothing) | "No insights match those filters" plus a clear-filters action |
| Error | The API's own message, a retry button, and the underlying code for support |
| Missing record | "Insight not found" with a link back to the library |

Every screen has all five; none of them fall back to an unhandled spinner or a stack trace.

## Responsive behaviour

- ≥1200px: sidebar expanded, tables full width, dashboard in a 4-column stat grid.
- 768–1199px: sidebar collapses to icons, stat grid becomes 2 columns, tables scroll inside
  their card rather than pushing the page.
- <768px: sidebar becomes an off-canvas drawer, stat cards stack, secondary table columns are
  hidden and detail screens lead with the decision-relevant fields.

The mobile overview is captured in
[screenshots/18-mobile-overview.png](screenshots/18-mobile-overview.png), and the Playwright
suite asserts there is no horizontal page scroll on every primary screen.
