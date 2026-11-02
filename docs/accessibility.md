# Accessibility

Target: WCAG 2.1 level AA for the application chrome and primary workflows. This document
records what is implemented and how it is checked; it does not claim certification.

## Implemented

- **Landmarks and skip link.** Every authenticated screen renders inside `<main id="main">` with a
  `Skip to content` link as the first focusable element. The sidebar is a labelled `<nav>`.
- **Keyboard operation.** All interactive controls are native buttons, links, inputs and selects.
  The global search palette opens with `Ctrl/⌘ + K`, traps focus while open, closes on `Escape`
  and restores focus on close. `aria-keyshortcuts` documents the shortcut.
- **Focus visibility.** A visible `:focus-visible` outline is defined globally rather than removed.
- **Semantic tables.** Data tables use `<thead>`, `<th>` and a caption or labelled section heading;
  the segment chart is exposed as an accessible bar list rather than a decorative SVG.
- **Forms.** Every input has a `<label for>`; validation errors are rendered as text next to the
  field and returned by the API in an `error.details` array keyed by field name.
- **Live feedback.** Toasts and inline notices announce success and failure in text, and the
  destructive reset dialog requires a typed confirmation phrase.
- **Colour and contrast.** Text uses `#252923` on `#F7F5EF` or `#FFFFFF`, with `#74796F` reserved
  for secondary text at sizes that keep contrast above 4.5:1. Status is never conveyed by colour
  alone: pills also carry a label.
- **Motion and zoom.** No animation depends on motion for meaning; layout reflows at 320 px,
  768 px and 1440 px without horizontal scrolling.
- **Empty and error states.** Every list has a written empty state and an error state with a
  retry action, so a screen is never blank.

## Automated checks

`frontend/e2e/a11y.spec.ts` runs axe-core against every primary screen and the search palette and
fails on serious or critical violations. It is part of the Playwright suite.

**Status for this revision:** not executed in this session (the browser suite needs both servers;
the Docker daemon was unavailable). The spec is unchanged and should be run before a demonstration.

## Known gaps

- No screen-reader testing with NVDA/JAWS/VoiceOver has been recorded.
- Dense tables on small screens rely on horizontal scroll inside the table wrapper rather than a
  card-per-row transformation.
- The editorial serif is used only for headings where its contrast ratio has been checked; body
  copy stays in Inter.
- No formal accessibility statement or conformance audit exists.
