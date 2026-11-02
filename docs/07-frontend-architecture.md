# Frontend architecture

> **Status (2 November 2026).** This document is retained as the original discovery record.
> Password authentication, server-side sessions and API-enforced roles are now implemented;
> statements below that the API has no authentication, or that `X-Demo-User-Id` grants
> identity, no longer describe the code. See [auth.md](auth.md) and [security.md](security.md).

React 18 + TypeScript + Vite 6, Bootstrap 5 through `react-bootstrap`, Recharts for the two
charts, `react-router-dom` 6 for routing, `@tanstack/react-query` 5 for server state.

## Directory layout

```
src/
  app/            App (routes), SessionProvider, ToastProvider
  layouts/        AppShell: sidebar, top bar, search trigger, demo banner
  pages/          20 screens, one per route
  components/     ui.tsx (design-system primitives), EvidenceCard, GlobalSearch, ConfirmDialog
  services/       api.ts — the only place that talks to the network
  types/          index.ts — API response types
  utils/          format.ts — dates, relative time, pluralisation, labels
  styles/         app.css — design tokens and component classes
```

## Data flow

```
page ──► services/api.ts (fetch + ApiError) ──► /api/v1/*
  ▲                    │
  └── react-query cache┘
```

- **One client.** `api.ts` owns the base URL, the `X-Demo-User-Id` header, query
  serialisation, JSON parsing and the error envelope. No page calls `fetch` directly, so
  changing the base URL or adding a header is a one-line change.
- **Query keys are entity-shaped** (`['projects']`, `['project', id]`), and every mutation
  invalidates the entities it could have changed. After linking evidence to an insight the
  insight, the evidence list and the dashboard all refresh.
- **Mutations show intent immediately**: the button enters a pending state, the toast reports
  the server's own message on success, and the API's error message on failure. No generic
  "something went wrong" when the server already said what went wrong.
- **No global store.** The only cross-cutting state is the selected demonstration person
  (`SessionProvider`, persisted in `localStorage`) and toasts. Everything else is server state
  or component state.

## Session handling

Not authentication. `SessionProvider` stores the chosen seeded user id under
`localStorage.clh.demoUserId`; `api.ts` sends it as `X-Demo-User-Id` so the backend can
attribute activity-log entries. The login screen lists the seven people fetched from
`GET /session`, and every screen states that the picker is a demonstration convenience. If
the stored id disappears from the API (for example after a demo reset), the provider clears it
and returns to the entry screen rather than rendering a broken shell.

## Rendering rules

- **Every screen has five states**: loading (skeleton with a sentence about what is being
  calculated), ready, empty, filtered-empty, error. They are components in `ui.tsx`, not
  ad-hoc markup per page, so the wording stays consistent.
- **No layout shift on load.** Skeletons match the height of the content they replace; stat
  cards and tables reserve their rows.
- **Dates are relative where it helps and absolute where it must be.** "Due in 3 days" next to
  the exact date; never a bare relative date on a decision record.
- **Numbers are formatted, not stringified.** Percentages come from the server with their
  numerator and denominator so the UI can show "4 of 7 (57%)" instead of a floating-point
  percentage with no context.

## Components

`ui.tsx` exports the primitives every page composes from: `PageHeader`, `SectionCard`,
`StatCard`, `Pill` (status badges), `ProgressBar` (confidence and completion), `EmptyState`,
`ErrorState`, `LoadingBlock`, `TableSkeleton`, `Notice`, `HonestyNote`, `MetaItem` and
`Spinner`. Status colours, labels and confidence tones are mapped in one place so a new status
value cannot render as an unstyled word on one screen and a badge on another.

`EvidenceCard` renders one evidence row and is the reason evidence looks identical on the
project, interview, evidence-library and insight screens: one component, one reading
experience, no drift between screens.

`GlobalSearch` is a dialog reachable from the top bar and `Ctrl/⌘+K`. It debounces input,
requires two characters, groups results by entity type, and shows the suggestion state when a
query matches nothing.

## Styling

- Tokens (colour, spacing, radius, type scale) are CSS custom properties at the top of
  `app.css`, so the whole product retints from one block.
- Bootstrap supplies layout and behaviour; `app.css` supplies the visual identity. Pages use
  Bootstrap grid classes and the design-system classes, not inline styles.
- Class naming is `block-element` (`stat-card`, `card-header-row`, `evidence-meta`), keeping
  the stylesheet greppable at ~1.4k lines.
- Dark surfaces are used for the sidebar only; content stays light for long reading sessions.

## Accessibility implementation notes

- The shell uses `<nav aria-label="Primary navigation">`, one `<h1>` per screen, and landmark
  elements throughout.
- Focus is trapped in dialogs and restored on close; the command palette returns focus to the
  trigger.
- Status is never conveyed by colour alone — every `Pill` carries its label, and confidence
  is a word (`low`, `medium`, `high`) next to the progress meter.
- Tables use real `<th scope>` headers; interactive rows expose a keyboard-reachable link.

See [14-accessibility.md](14-accessibility.md) for the audit and its limits.

## Build and performance

- `npm run build` runs `tsc -b` then `vite build`; a type error fails the build.
- The production bundle is served by nginx with gzip and immutable caching for hashed assets;
  `index.html` is never cached.
- The overview issues three requests (dashboard, search-ready session, settings) rather than
  eleven, because the dashboard endpoint is shaped for the screen.
- Charts are the largest dependency (Recharts) and are confined to Overview and Analytics.

## Testing hooks

- `data-testid` is used sparingly, only where role and label selectors would be ambiguous.
- Playwright drives the real UI against a real API: no mocking layer exists, so a broken
  contract fails the test.
