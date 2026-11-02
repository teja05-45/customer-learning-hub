# Design system

The interface has one job: make it obvious what a claim rests on. Every token and component
decision below serves that.

## Character

Calm, dense, unglamorous on purpose. This is a research record that someone reads at 9am
before a decision meeting, not a dashboard that flatters activity. No gradients, no floating
cards on photos, no celebratory animation. Confidence comes from clear provenance, stable
layout and honest numbers.

## Colour

Defined once as CSS custom properties at the top of `frontend/src/styles/app.css`.

| Token | Value | Used for |
| --- | --- | --- |
| `--clh-primary` | `#2563eb` | Primary actions, links, active nav |
| `--clh-navy` | `#172554` | Sidebar surface |
| `--clh-bg` | `#f8fafc` | App background |
| `--clh-surface` | `#ffffff` | Cards, tables, panels |
| `--clh-text` | `#0f172a` | Body text |
| `--clh-text-secondary` | `#475569` | Labels, helper text, table headers |
| `--clh-text-tertiary` | `#64748b` | Meta, muted detail, small print |
| `--clh-sidebar-muted` | `#94a3b8` | Muted text on the navy sidebar only |
| `--clh-border` | `#e2e8f0` | Dividers, table rules |
| `--clh-success` | `#16a34a` | Completed, granted, on track |
| `--clh-warning` | `#d97706` | Due soon, under review, needs attention |
| `--clh-danger` | `#dc2626` | Overdue, flagged, contradictory, missing consent |
| `--clh-info` | `#0284c7` | Neutral information, pending states |
| `--clh-purple` | `#6d28d9` | Decision-level annotations only |

Each status colour has a `-soft` variant used as the badge background, so a badge is readable
without shouting. Colour is never the only signal: every badge shows its word.

**Contrast** (measured, WCAG 2.1 formula): body text on white 17.9:1, secondary 6.9:1,
tertiary 4.8:1, white on navy 14.7:1, white on the primary blue 5.2:1. Badge text on its soft
background ranges 4.8:1 (green, amber, outline) to 8.1:1 (purple), so every badge clears AA
at 11px.

The muted token needed two values, not one: `#94a3b8` is fine on navy (5.7:1) but only 2.6:1
on white. The light surfaces therefore use `#64748b` and the sidebar keeps `#94a3b8`.

## Typography

System sans (`ui-sans-serif`, Segoe UI, Roboto). No webfont download, so first paint is text.

| Element | Size / weight | Notes |
| --- | --- | --- |
| Page title (`h1`) | 26px / 650 | One per screen |
| Card title | 15px / 600 | Section name, not a heading element |
| Body | 14px / 400 | Line height 1.55 |
| Meta and labels | 12–13px / 500 | Secondary colour |
| Codes (`INT-0003`) | 12px mono | Always the same style, always next to the human title |
| Numbers in stat cards | 30px / 650, tabular | Aligned so a column of stats can be scanned |

## Spacing and layout

- 4px base scale: 4, 8, 12, 16, 20, 24, 32, 40.
- Sidebar 252px, top bar 60px, content max width 1440px with 24–32px gutters.
- Cards use 14px radius and the `sm` shadow; nested cards are not allowed — one surface per
  idea.
- Tables sit inside the card, scroll horizontally *inside* it rather than pushing the page.

## Components

| Component | Behaviour |
| --- | --- |
| `PageHeader` | Title, one-line description, meta row, actions on the right |
| `SectionCard` | Title, optional subtitle, optional actions, padded body |
| `StatCard` | Label with icon, large value, one line of context; `warning` variant for overdue work |
| `Pill` | Status badge: word + tone, never colour alone |
| `ProgressBar` | Confidence or completion, paired with a text label |
| `Notice` | Inline guidance; tones info/success/warning/danger |
| `HonestyNote` | The grey "what this does not mean" block used on analytics and decisions |
| `EmptyState` | Named state + the next action |
| `ErrorState` | Server message + retry + error code |
| `LoadingBlock` / `TableSkeleton` | Reserve the layout while loading |
| `ConfirmDialog` | Destructive confirmation with a phrase requirement where risky |
| `EvidenceCard` | One evidence row: type pill, verbatim content, interpretation, segment, provenance |

## Interaction rules

- **Primary action per screen** is one filled button; everything else is secondary or a link.
- **Destructive actions** (delete evidence, unlink a decision source, reset demo) require a
  confirmation dialog; reset additionally requires typing `RESET`.
- **Pending states** disable the trigger and keep its width, so the layout does not jump.
- **Toasts** carry the server's message, not a generic success string, and never auto-dismiss
  before 4 seconds.
- **Focus** is visible on every interactive element (2px ring, 2px offset) and never removed
  without a replacement.

## Content and tone

- Plain verbs: "Record consent", "Link evidence", "Mark reviewed". No "leverage", "unlock",
  "supercharge".
- The product's own doubts are written down: "not yet measured", "pending baseline",
  "internal judgement, not customer research".
- Numbers carry their denominator: "4 of 7 decisions cite customer evidence", never "57%".
- Never claim causality the data cannot support. The analytics screen states plainly that
  research cannot be credited with repeat-purchase or revenue changes.

## What was deliberately not built

- No dark mode: one surface, reviewed once.
- No custom chart library: Recharts defaults, restyled to the palette.
- No icon set beyond `lucide-react` at 16–18px.
- No animation beyond 120ms hover and the toast slide — motion is not information here.
