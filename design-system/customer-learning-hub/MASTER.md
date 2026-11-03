# Customer Learning Hub — Master Design System

**Direction:** Executive Emerald
**Product:** Customer Learning Hub (Everyday Goods)
**Industry:** Enterprise SaaS · Customer research · Business intelligence
**Audience:** CEO, researchers, business owners, customer-experience teams
**Platform:** Desktop-first responsive web, 375–1440 px
**Stack:** React 18 + TypeScript, Bootstrap 5 utilities, hand-authored CSS tokens

This document is the source of truth. Pages consume these tokens and components; they do not
invent local palettes, type scales or motion values. The implementation lives in
`frontend/src/styles/app.css` (base component rules) and `frontend/src/styles/emerald.css`
(Executive Emerald token and component layer). A page may add a layout rule, never a new
colour.

---

## 1. Design intent

The product's job is to make customer evidence trustworthy. The interface therefore has to feel
like a considered research instrument, not a marketing dashboard:

- **Editorial, not decorative.** A serif display face gives page titles the weight of a report;
  the working UI stays in a neutral sans so dense tables remain legible.
- **Warm paper, deep ink.** The canvas is warm off-white (`#F7F5EF`), not blue-grey; the chrome
  is deep emerald (`#103F32`), which reads as considered and institutional.
- **One accent family.** Emerald carries action and confirmation. Gold marks provenance,
  attention and the current location. Terracotta is reserved for contradiction and destruction.
- **Evidence is never styled as opinion.** Customer statements and researcher interpretation use
  different surfaces, labels and border colours.
- **Honest emptiness.** Zero-data states are designed, not hidden.

Explicitly rejected: generic blue-and-white dashboards, glassmorphism, gradient hero cards,
oversized rounded rectangles, random accent colours, emoji as icons, fabricated statistics and
animation that delays a business action.

---

## 2. Colour tokens

### 2.1 Core palette

| Token | Hex | Role | Contrast check |
| --- | --- | --- | --- |
| `--clh-primary` | `#176B52` | Primary action, active state, links | 6.4:1 on white (AA) |
| `--clh-primary-ink` | `#124B3B` | Hover/pressed primary, deep chrome | 9.1:1 on white |
| `--clh-primary-soft` | `#EAF2ED` | Selected nav, quiet emerald wash | — |
| `--clh-chrome` | `#103F32` | Sidebar, login aside | 8.8:1 with cream text |
| `--clh-bg` | `#F7F5EF` | Application canvas | — |
| `--clh-surface` | `#FFFFFF` | Cards, tables, dialogs | — |
| `--clh-surface-muted` | `#FBFAF6` | Table head, inset panels | — |
| `--clh-text` | `#252923` | Primary text | 13.4:1 on canvas |
| `--clh-text-secondary` | `#5F655C` | Descriptions, metadata | 5.5:1 on canvas (AA) |
| `--clh-text-tertiary` | `#6A6F65` | Definitions, captions | 5.1:1 on white (AA) |
| `--clh-border` | `#E7E5DC` | Dividers, card borders | — |
| `--clh-border-strong` | `#D5D2C6` | Input borders, emphasis | — |
| `--clh-gold` | `#D6A84F` | Current-location marker, provenance accent | 4.6:1 on chrome |
| `--clh-gold-ink` | `#7A5210` | Gold text on light surfaces | 6.9:1 on `#FBF3E4` |
| `--clh-terracotta` | `#D97757` | Contradiction, destructive emphasis (fill) | — |
| `--clh-danger` | `#B44A32` | Error text, destructive action text | 5.3:1 on white (AA) |
| `--clh-success` | `#1D7A57` | Verified, completed, accepted | 5.3:1 on white (AA) |
| `--clh-warning` | `#B57F2A` | Thin evidence, overdue | 4.5:1 on white |
| `--clh-info` | `#2F6B7A` | Observation, neutral information | 6.0:1 on white (AA) |

### 2.2 Pairings that are allowed

| Surface | Text/icon | Purpose |
| --- | --- | --- |
| `#103F32` chrome | `#F6F2E6` | Navigation labels |
| `#103F32` chrome | `#9FB7AB` | Section labels, secondary chrome text |
| `#176B52` | `#FFFFFF` | Primary buttons |
| `#EAF2ED` | `#124B3B` | Active navigation, selected filters |
| `#FBF3E4` | `#7A5210` | Warning notices and pills |
| `#FBEDE8` | `#8C3A26` | Contradiction and destructive notices |
| `#EDF6F1` | `#14603F` | Verified/success pills |

Never place white text on gold or terracotta for body copy. Gold is an accent, not a text
background.

### 2.3 Contrast decisions

The supplied secondary text `#74796F` measures ≈4.46:1 on white, just under WCAG AA for normal
text. It is retained only as a non-text decorative tone; the text token is `#6A6F65` (≈5.1:1).
Gold `#D6A84F` is likewise never used for small text on light surfaces — `#7A5210` is the text
form. These refinements were verified with the relative-luminance formula, and automated axe
checks run in the Playwright suite.

---

## 3. Typography

| Role | Family | Size / weight / tracking |
| --- | --- | --- |
| Page title | `ui-serif, "Iowan Old Style", "Palatino Linotype", Georgia, serif` | 30 px / 600 / −0.018em |
| Brand | same serif | 14.5 px / 600 / 0.005em |
| Section/card title | system sans | 13.5 px / 640 / −0.01em |
| Body | system sans | 14 px / 400 / 0 |
| Table body | system sans | 13 px / 400 |
| Label / meta | system sans | 11–12 px / 600, uppercase only for column heads and eyebrow labels |
| Numerals | system sans, `font-variant-numeric: tabular-nums` | as context |

The serif is used only for page and brand titles. It is not used for buttons, tables, labels or
numbers: mixing serif into dense operational UI reduces scan speed.

Line height: 1.5 body, 1.25 titles, 1.45 definitions. Maximum description width 76ch.

---

## 4. Spacing, radius and elevation

- 4 px base scale: 4, 8, 12, 16, 20, 24, 32, 40, 56.
- Page padding: 26 px / 30 px desktop, 18 px / 14 px below 992 px.
- Radius: 5 px controls, 9 px cards, 12 px dialogs. Nothing above 12 px except status pills.
- Elevation: `0 1px 1px rgba(37,41,35,.04)` resting card, `0 10px 30px rgba(37,41,35,.12)` for
  overlays only. No coloured shadows.
- Borders carry structure; shadows only separate floating layers.

---

## 5. Layout

- 260 px fixed chrome rail, 64 px top bar, content column capped at 1440 px.
- The rail collapses to an off-canvas drawer below 992 px; the top bar exposes the trigger and
  the search control.
- Grids: `grid-4` for stat rows, `grid-3` for metric triples, `grid-2` for paired panels,
  `grid-sidebar` (1.9fr / min 280 px) for main + context.
- Tables scroll inside `.table-wrap`; the page itself must never scroll horizontally.
- Every screen starts with a title, a one-sentence purpose and its actions.

---

## 6. Components

| Component | Rule |
| --- | --- |
| `SectionCard` | White surface, 1 px border, 9 px radius, header row separated by a hairline |
| `PageHeader` | Serif title, sans description, actions top-right, wraps below 620 px |
| `StatCard` | Label, tabular value, definition; warning variant uses gold border, never red |
| `Pill` | 11 px, 600, 18 px line height; colour plus text, never colour alone |
| `Notice` | 12.5 px, icon + title + body; danger uses `role="alert"` |
| `EmptyState` | Muted icon tile, reason, next action; no illustration |
| `ErrorState` | Terracotta icon, server message, explicit Retry |
| `EvidenceCard` | Left border encodes type; statement and interpretation are separate blocks |
| `ConfirmDialog` | Consequence sentence, optional typed phrase, primary action last |
| `GlobalSearch` | Modal dialog, 660 px, focus trap, Escape, focus restoration |
| `DataTable` | Uppercase 10.5 px head, 11/14 px cells, row hover, tabular numerals |

### Evidence semantics

| Evidence type | Accent | Meaning |
| --- | --- | --- |
| Verbatim quote | `--clh-primary` | Customer's own words |
| Observation | `--clh-info` | Researcher saw it happen |
| Researcher interpretation | `--clh-purple` | Explicitly not customer words |
| Contradictory evidence | `--clh-warning` | Must remain visible |
| Open question | `--clh-text-tertiary` | Unresolved |

A quote is never rendered in the same block as an interpretation, and an interpretation is always
labelled as such.

---

## 7. Motion

| Token | Value | Use |
| --- | --- | --- |
| `--clh-motion-fast` | 140 ms | Hover, press, nav, row highlight |
| `--clh-motion` | 200 ms | Tabs, dropdowns, cards changing state |
| `--clh-motion-panel` | 260 ms | Dialogs, drawers, command palette |
| `--clh-ease` | `cubic-bezier(.2,.7,.3,1)` | All entrances and state changes |

Rules:

- Animate only opacity, transform, background and border colour. Never width/height of content.
- No animation on data load that hides the data; skeletons communicate loading.
- `prefers-reduced-motion: reduce` collapses every duration to 0.01 ms and disables the skeleton
  shimmer. This is implemented globally in `emerald.css`, not per page.
- No looping decorative animation.

---

## 8. Accessibility

- Skip link is the first focusable element; `main` has `tabindex="-1"`.
- Visible focus: 2 px `--clh-primary` outline, 2 px offset. Never remove outline without a
  replacement.
- Dialog focus trap and restoration in the search palette; Escape closes.
- Colour is never the sole carrier of meaning: every status pill has text, every chart has a
  labelled legend and accessible name.
- Minimum target size 24×24 px; primary controls 32 px.
- Contrast targets: 4.5:1 normal text, 3:1 large text and graphical objects. Verified pairs are
  listed in §2.1.
- Tables use real `th`/`td`; icon-only buttons carry `aria-label`.

---

## 9. Page-specific overrides

Only two overrides are permitted; everything else uses the master:

1. **Authentication** (`LoginPage`) — the aside uses the chrome colour and a single gold radial
   wash. No other page uses that wash.
2. **Analytics / Overview charts** — a five-colour categorical ramp derived from the palette:
   emerald, teal, gold, terracotta, deep plum. The ramp exists only inside chart components and
   must not leak into UI chrome.

Any new page that needs a different colour must add a token here first.

---

## 10. Implementation map

| Concern | File |
| --- | --- |
| Base component CSS | `frontend/src/styles/app.css` |
| Emerald tokens + component layer | `frontend/src/styles/emerald.css` |
| Shared primitives | `frontend/src/components/ui.tsx` |
| Evidence rendering | `frontend/src/components/EvidenceCard.tsx` |
| Shell and navigation | `frontend/src/layouts/AppShell.tsx` |
| Charts | `DashboardPage.tsx`, `AnalyticsPage.tsx` |
| Verification | `frontend/e2e/a11y.spec.ts`, `frontend/e2e/responsive.spec.ts`, `docs/screenshots/` |

## 11. Provenance and honest status

This system was authored against the public guidance of the UI UX Pro Max design-intelligence
skill and the 21st.dev component ecosystem. Neither tool was executed in this environment:

- `ui-ux-pro-max-cli` / `uipro` was **not** installed, so no generated skill files were available
  to read. Installation instructions are recorded in `docs/design.md`.
- The 21st MCP server was **not** connected and no API key was supplied, so no hosted component
  was generated. The interface is built from the project's existing React primitives, restyled
  against the tokens above.

No component in this repository was imported from 21st.dev. No claim of MCP generation is made.
