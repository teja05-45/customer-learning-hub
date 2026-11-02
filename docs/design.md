# Design

The existing professional light-theme identity is retained. This document records the tokens
and the interaction rules the implementation follows.

## Palette

| Token | Value | Use |
| --- | --- | --- |
| Primary | `#2563EB` | Primary actions, active navigation, selected filters |
| Navy | `#172554` | Sidebar and high-emphasis headings |
| Background | `#F8FAFC` | Page background |
| Surface | `#FFFFFF` | Cards, tables, modals |
| Text | `#0F172A` | Primary text |
| Secondary text | `#64748B` | Metadata, definitions |
| Border | `#E2E8F0` | Card and table dividers |
| Success | `#16A34A` | Completed, validated, verified |
| Warning | `#D97706` | Thin evidence, sample warnings, overdue |
| Danger | `#DC2626` | Blocked, rejected, destructive actions |

Tokens are defined once in `frontend/src/styles/app.css` as CSS custom properties
(`--clh-primary`, `--clh-text`, …). Components reference tokens rather than raw hex values,
with chart colours passed to Recharts from the same palette family.

## Typography and spacing

- System UI stack; page title 24–26px/650, card title 13.5px/650, body 13px, definition 11.5px.
- Spacing follows a 4px scale exposed as utility classes (`mt-1`…`mt-3`, `gap-2`, `stack-2`).
- Numbers in tables use a monospace class (`mono`) so columns align.
- No gradients, no decorative animation. The only motion is the loading spinner and skeleton
  shimmer, both of which communicate state.

## Layout

- Fixed sidebar (collapsible on narrow screens) plus a content column capped at a readable
  width; tables scroll horizontally inside `.table-wrap` rather than widening the page.
- `grid-4` stat rows, `grid-3` metric cards, `grid-2` paired panels, `grid-sidebar` main +
  context column. These collapse to a single column under the Bootstrap `lg` breakpoint.
- Every primary screen has a page header with title, one-sentence purpose and actions.

## Components

`components/ui.tsx` provides `Pill`, `SectionCard`, `PageHeader`, `StatCard`, `EmptyState`,
`ErrorState`, `LoadingBlock`, `TableSkeleton`, `Notice`, `Spinner`, `HonestyNote`, `MetaItem`
and `ProgressBar`. `EvidenceCard` renders customer words and researcher interpretation in
visually distinct blocks. `ConfirmDialog` gates destructive actions.

## Required page states

| State | Pattern |
| --- | --- |
| Loading | `TableSkeleton` for lists, `LoadingBlock` for detail panels |
| Empty | `EmptyState` with a reason and, where useful, the next action |
| Error | `ErrorState` with the server message and a Retry button |
| Refreshing | Inline "Refreshing…" label; previous data remains visible |
| Success | Toast; no `alert()` anywhere in the codebase |
| Destructive | `ConfirmDialog` naming the consequence, never a browser confirm |

## Forms

- Labels are always visible; required fields carry a `*` and the API validates again.
- Server field errors are displayed next to the field via `fieldErrors()`.
- Selects use controlled state; date inputs use native `date`/`datetime-local` controls.
- Modal footers put the primary action last and disable it while a request is in flight.

## Honesty as a design rule

Warnings are visible, not hidden in tooltips: sample-size warnings, thin evidence,
contradictory evidence, unverified provenance, pending-baseline metrics and "Not measured"
values all have explicit visual treatment. The demo banner is persistent. Synthetic data is
labelled on screen and in every CSV export header/row.

## Accessibility

- Skip link to `#main`; the main landmark is focusable.
- The command palette is `role="dialog" aria-modal="true"` with a focus trap, Escape to close
  and focus restoration to the trigger.
- Icon-only buttons have `aria-label`s; charts expose an accessible name and image role.
- Colour is never the only signal: statuses also carry text labels.
- Target: no serious or critical axe violations on primary screens (enforced in
  `frontend/e2e/a11y.spec.ts`).

See `08-design-system.md` and `14-accessibility.md` for the original rationale.
