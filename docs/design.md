# Design

The product uses the approved **Notion-inspired workspace** palette. The source of truth is
`frontend/src/styles/notion.css`, loaded after `app.css` and the legacy `emerald.css` layer. Pages
consume tokens; they do not define their own palette. The Emerald layer is retained as history and
is fully overridden — no dark green chrome or cream canvas remains on screen.

## Palette

| Token | Value | Use |
| --- | --- | --- |
| Background | `#FFFFFF` | Page and card surface |
| Sidebar / muted surface | `#F7F7F5` | Chrome rail, table head, inset panels |
| Primary text | `#252525` | Headings and body |
| Secondary text | `#6F6E6A` | Descriptions and metadata |
| Borders | `#E9E9E7` | Dividers and card edges |
| Primary accent | `#347A69` | Primary actions, links, active icon |
| AI accent | `#7565B5` | Researcher interpretation, AI-derived surfaces |
| Hover | `#F1F1EF` | Navigation, rows and quiet controls |
| Font | Inter | All UI and page titles |

**Contrast deviation:** the approved secondary `#787774` measures 4.48:1 on white and about 4.2:1
on `#F7F7F5`, just under WCAG AA 4.5:1 for the 11–13 px labels used here. The text token is
`#6F6E6A`, a two-point darkening that measures ≈4.9:1 on white and ≈4.5:1 on the rail. The approved
value remains documented as the intent; accessibility wins for text. Axe verifies the result in
`frontend/e2e/a11y.spec.ts`.

## Typography and spacing

- Inter (`'Inter', ui-sans-serif, -apple-system, ...`) for page titles, brand, body, tables and
  buttons. No serif display face is used.
- Page title 26 px/640 with −0.025em tracking; card title 13 px/620; body 13.5 px; table body 13 px;
  definitions and metadata 11–12 px.
- 4 px spacing scale; page padding 26/30 px desktop and 18/14 px below 992 px.
- Radii: 4 px controls, 6 px cards, 8–10 px dialogs. Pills are 3 px.
- Elevation is nearly flat: 1 px card border, no resting shadow, one overlay shadow. No coloured
  shadows and no gradients except the single login wash and the chart area fill.

## Layout

- 252 px light rail, 56 px top bar, content capped at 1440 px.
- The rail collapses to an off-canvas drawer below 992 px; the top bar exposes the menu and
  search controls, and tables scroll inside `.table-wrap` rather than widening the page.
- `grid-4` stat rows, `grid-3` metric cards, `grid-2` paired panels, `grid-sidebar` main +
  context column; all collapse to one column at their breakpoints.
- Every screen opens with an Inter title, one-sentence purpose and its actions.
- The nine-column journey board scrolls inside its own container; the page itself never scrolls
  horizontally. There is no drag-and-drop because status changes must pass API validation.

## Motion

| Token | Value | Use |
| --- | --- | --- |
| `--clh-motion-fast` | 140 ms | Hover, press, nav, table rows |
| `--clh-motion` | 200 ms | Dropdowns, tabs, cards changing state |
| `--clh-motion-panel` | 260 ms | Dialogs, command palette, drawers |
| `--clh-ease` | `cubic-bezier(.2,.7,.3,1)` | All entrances and state changes |

Only opacity, transform, background and border colour animate. The sidebar drawer, command
palette, modal, toasts and row hover are the animated surfaces. A global
`prefers-reduced-motion: reduce` block collapses durations and disables the skeleton shimmer.

## Components

`components/ui.tsx` provides `Pill`, `SectionCard`, `PageHeader`, `StatCard`, `EmptyState`,
`ErrorState`, `LoadingBlock`, `TableSkeleton`, `Notice`, `Spinner`, `HonestyNote`, `MetaItem`
and `ProgressBar`. `EvidenceCard` puts the customer's statement and the researcher's
interpretation in separate labelled blocks with different surfaces. The feedback workspace uses
the same rule: `.feedback-card` carries a source-coloured left edge, a quote block, a tinted
interpretation block labelled as not the customer's words, and a provenance block. Its depth
pill is always visible, so a survey is never styled like a moderated interview. `ConfirmDialog`
gates destructive actions and supports a typed confirmation phrase.

## Required page states

| State | Pattern |
| --- | --- |
| Loading | `TableSkeleton` for lists, `LoadingBlock` for detail panels |
| Empty | `EmptyState` with a reason and, where useful, the next action |
| Error | `ErrorState` with the server message and a Retry button |
| Refreshing | Inline "Refreshing…" label; previous data stays visible |
| Success | Toast; no `alert()` anywhere in the codebase |
| Destructive | `ConfirmDialog` naming the consequence |

## Forms

- Labels are always visible; required fields carry `*` and the API validates again.
- Server field errors render next to the field via `fieldErrors()`.
- Selects are controlled; dates use native inputs.
- Primary action is last in a modal footer and disabled while a request is in flight.

## Honesty as a design rule

Warnings stay visible rather than hiding in tooltips: sample-size warnings, thin evidence,
contradictory evidence, unverified provenance, pending-baseline metrics and "Not measured"
values all have explicit treatment. The demo banner is persistent, and synthetic data is labelled
on screen and in every CSV row.

## Accessibility

- Skip link to `#main`; the main landmark is focusable.
- The command palette is `role="dialog" aria-modal="true"` with a focus trap, Escape to close
  and focus restoration to the trigger.
- Icon-only buttons have `aria-label`s; charts expose accessible names.
- Status is never carried by colour alone.
- Target: no serious or critical axe violations on primary screens, enforced in
  `frontend/e2e/a11y.spec.ts`.

## Tooling status

The UI UX Pro Max CLI was not installed in this environment, so no skill-generated files were
read and no generated design system was consumed:

```bash
npm install -g ui-ux-pro-max-cli
uipro init --ai claude
```

The 21st MCP server was not connected and no API key was supplied, so no component was
searched, generated or imported from 21st.dev:

```bash
npx @21st-dev/cli@latest init --client claude
```

The interface is built from the repository's existing React primitives, adapted to the tokens
above. This document and the master design system describe what is actually implemented, not
what the tools might have produced.
