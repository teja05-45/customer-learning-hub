# Risks

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- | --- |
| R1 | Synthetic data is mistaken for real research | Medium | High | Persistent demo banner, `is_synthetic` on every record and export, documentation, demo script language | FDE |
| R2 | A small sample is presented as representative | Medium | High | No representativeness metric; sample warnings on recruitment and insight views; validation labelled internal only | Research lead |
| R3 | Session or credential weakness (no SSO, no rate limiting, no CSRF token) | Medium | Medium | Password sessions and role enforcement are implemented; add rate limiting, TLS and a CSRF token before exposing writes publicly | Customer admin |
| R4 | Contradictory evidence deleted to simplify a story | Medium | High | Explicit warnings, confirmation dialog, evidence counts drop visibly, operations guidance | Research lead |
| R5 | Unattributed note treated as verified evidence | Low | High | Missing provenance forces flagged status and low confidence; provenance warning everywhere | FDE |
| R6 | Dashboard and analytics drift apart | Medium | Medium | Shared service functions; `test_metrics.py` asserts agreement | FDE |
| R7 | Metric definitions change silently | Low | Medium | Definitions returned with metrics; ADR-010; tests pin formulas | FDE |
| R8 | Recruitment history lost on workflow shortcuts | Medium | Medium | Single transition service; interview paths write events; regression tests | FDE |
| R9 | SQLite write contention or volume loss | Low | Medium | Single-user demo; named volume; reset documented; PostgreSQL is next step | Customer admin |
| R10 | Docker port conflicts on reviewer machines | Medium | Low | Web on 8081, documented; API port mapping changeable | FDE |
| R11 | Bundle size causes slow first load | Medium | Low | Known advisory; code-splitting scheduled | FDE |
| R12 | Frontend/backend contract drift | Low | Medium | Shared TypeScript types, API tests, Playwright integration | FDE |
| R13 | Free-text fields contain personal data typed by a user | Medium | Medium | Schema minimisation, guidance, future privacy review and retention job | Customer admin |
| R14 | Adoption stalls after launch | Medium | High | Demo script, champion session, reuse and follow-up metrics visible | Research lead |
| R15 | Tool becomes a survey/volume machine | Low | Medium | Product language and design emphasise depth, contradictions and limitations | FDE |

## Open questions

- Who owns the controlled Ops outreach process, and what does it record?
- Which baseline (coordination time) can realistically be collected in four weeks?
- Will the business accept a decision register that labels some decisions as internal judgement?
- Is a hosted instance required for the interview, or is a local demo acceptable? This decides
  whether authentication must ship first.

## Escalation

Any R1–R5 occurrence is treated as a product incident: correct the record, note it in the
activity log, and review whether a UI or API guard failed. Technical risks R6–R12 are handled
through tests and the roadmap.
