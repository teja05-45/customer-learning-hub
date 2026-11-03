# Design

The product uses the **Executive Emerald** design system. The source of truth is
`design-system/customer-learning-hub/MASTER.md`; the implementation is split between
`frontend/src/styles/app.css` (base component rules) and `frontend/src/styles/emerald.css`
(Executive Emerald tokens and refinements, imported after the base sheet). Pages consume tokens;
they do not define their own palette.

## Palette

| Token | Value | Use |
| --- | --- | --- |
| Primary | `#176B52` | Primary actions, links, verified state, active navigation |
| Deep primary / chrome | `#124B3B` / `#103F32` | Sidebar, login aside, pressed primary |
| Primary wash | `#EAF2ED` | Selected navigation, quiet emerald surfaces |
| Canvas | `#F7F5EF` | Page background |
| Surface | `#FFFFFF` | Cards, tables, dialogs |
| Text | `#252923` | Primary text |
| Secondary text | `#5F655C` | Descriptions, metadata (5.5:1 on canvas) |
| Tertiary text | `#6A6F65` | Definitions, captions (5.1:1 on white) |
| Border | `#E7E5DC` | Dividers and card edges |
| Gold | `#D6A84F` / ink `#7A5210` | Current-location marker, provenance, attention |
| Terracotta | `#D97757` / text `#B44A32` | Contradiction and destructive emphasis |
| Success | `#1D7A57` | Completed, validated |
| Warning | `#B57F2A` | Thin evidence, overdue, sample warnings |
| Info | `#2F6B7A` | Observation and neutral information |

The supplied secondary tone `#74796F` measures ≈4.46:1 on white and is therefore not used for
normal text; `#6A6F65` replaces it for text while the original remains available as a decorative
tone. Gold is never used for small text on light surfaces — `#7A5210` is the text form. These
contrast decisions are documented in the master design system and checked by axe in
`frontend/e2e/a11y.spec.ts`.

## Typography and spacing

- Page and brand titles use a serif display stack (`ui-serif`, Iowan Old Style, Palatino,
  Georgia); the working UI uses the system sans stack. Serif never appears in tables, buttons,
  labels or numbers.
- Page title 30 px/600 with −0.018em tracking, collapsing to 24 px below 620 px. Card title
  13.5 px/640, body 14 px, table body 13 px, definitions 11.5 px.
- 4 px spacing scale; page padding 26/30 px desktop and 18/14 px below 992 px.
- Radii: 5 px controls, 9 px cards, 12 px dialogs. Nothing above 12 px except status pills.
- Elevation is limited to a 1 px resting shadow and a 30 px overlay shadow. No coloured shadows
  and no gradients except the single login wash and the chart area fill.

## Layout

- 260 px chrome rail, 64 px top bar, content capped at 1440 px.
- The rail collapses to an off-canvas drawer below 992 px; the top bar exposes the menu and
  search controls, and tables scroll inside `.table-wrap` rather than widening the page.
- `grid-4` stat rows, `grid-3` metric cards, `grid-2` paired panels, `grid-sidebar` main +
  context column; all collapse to one column at their breakpoints.
- Every screen opens with a serif title, one-sentence purpose and its actions.

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
