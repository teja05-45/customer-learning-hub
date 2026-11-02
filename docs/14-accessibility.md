# Accessibility

Target: **WCAG 2.1 AA for the screens a keyboard or screen-reader user must complete**, with
the gaps below stated rather than smoothed over. This is a prototype reviewed by a small
panel; it has not been through a formal audit.

## What is implemented

### Structure and semantics

- One `<h1>` per screen, from `PageHeader`. Section titles are styled `div`s, deliberately not
  headings, so the document outline stays shallow and predictable.
- Landmarks: `<aside aria-label="Primary navigation">`, `<nav aria-label="Breadcrumb">`,
  `<main id="main">`, tables as real `<table>` with `<th scope="col">`.
- A **skip link** ("Skip to content") is the first focusable element and moves focus to
  `<main tabindex="-1">`.
- Current page is marked with `aria-current` through `NavLink`.
- The demo banner, honesty notes and data-provenance blocks are plain text, not images.

### Keyboard

- Everything interactive is reachable by Tab; nothing depends on hover.
- The command palette (`Ctrl/⌘+K` or the top-bar button) is a dialog with `role="dialog"`,
  `aria-modal="true"`, autofocus on the input, `Escape` to close, **Tab cycling inside** the
  dialog, and focus returned to the trigger on close.
- `ConfirmDialog` uses `react-bootstrap`'s `Modal`, which traps focus and restores it.
- Visible focus ring (`:focus-visible`, 2px + offset) on every control, including table links
  and icon buttons.

### Colour and contrast

Measured with the WCAG relative-luminance formula:

| Pair | Ratio |
| --- | --- |
| Body text `#0f172a` on white | 17.9:1 |
| Secondary `#475569` on white | 6.9:1 |
| Tertiary `#64748b` on white | 4.8:1 |
| White on sidebar navy `#172554` | 14.7:1 |
| White on primary blue `#2563eb` | 5.2:1 |
| Badge text on soft badge backgrounds | 4.8:1 – 8.1:1 |

Two tokens exist because one could not do both jobs: `#94a3b8` reads acceptably on navy
(5.7:1) but fails on white (2.6:1). Light surfaces use `#64748b`; the sidebar keeps the lighter
tone. This was a genuine defect found while writing the design system down, and it was fixed
rather than documented.

Status is never colour-only: every `Pill` contains its word ("overdue", "granted",
"under review"), and confidence is a word beside the meter.

### Forms and feedback

- Every input has a visible `<label>`; icon-only buttons carry `aria-label`.
- Validation errors render next to the field with the server's message, and the form summary
  is announced in a live region.
- Toasts render in `role="status" aria-live="polite"`, so a screen reader hears the result of an
  action without losing their place.
- Loading states use text ("Calculating learning signals…"), not a bare spinner.

### Motion and zoom

- No animation longer than 120ms, no parallax, no auto-advancing carousel.
- Layout survives 200% zoom: the sidebar collapses, tables scroll inside their card, and no
  text is clipped at 1440×960 or 390×844.

## Tested

| Check | How |
| --- | --- |
| Skip link receives first Tab and moves focus | Playwright (`e2e/smoke.spec.ts`, keyboard test) |
| Palette traps Tab and restores focus on Escape | Same test |
| No horizontal page scroll on all ten primary screens | `expectNoHorizontalOverflow` in the smoke test |
| Contrast ratios | Computed from the CSS tokens (values above) |
| Keyboard walk-through of the shell, search, forms and dialogs | Manual, Chromium |
| Screen-reader spot check | Manual, Windows Narrator: headings, landmarks, table headers and live-region toasts read correctly |

## Not tested, and known gaps

| Gap | Impact | Next step |
| --- | --- | --- |
| No automated axe/Lighthouse run | Regressions can creep in unnoticed | Add `@axe-core/playwright` to the smoke test |
| No screen-reader pass on Safari/VoiceOver or NVDA | Unknown behaviour outside Narrator | Test both before any public release |
| Charts (Recharts) lack a text alternative | The dashboard's two charts are unreadable to a screen reader | Add a visually hidden table or summary per chart |
| Dense tables at 200% zoom | Columns wrap and scroll inside the card, but reading is slower | Add a compact/stacked table mode below 1100px |
| No reduced-motion media query | Motion is minimal, but the toast slide remains | Add `@media (prefers-reduced-motion: reduce)` |
| Colour-blind simulation not run | Badges carry words, so risk is low | Verify with a simulation tool |
| Content is English-only, `lang="en"` set | Only matters if localised | Revisit on localisation |

## Honest summary

A keyboard-only user can log in, move between screens, search, open a record, follow a claim
to its evidence, create an action and read the result of every action. A screen-reader user can
do the same for text content, but cannot read either chart. Nothing in the product is
mouse-only by design; the weakest point is the chart panels and the absence of automated
checks to keep the rest from regressing.
