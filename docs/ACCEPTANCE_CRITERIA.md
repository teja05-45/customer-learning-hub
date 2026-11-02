# Acceptance Criteria

Status is based on executed checks. "Verified" names the test or manual check used.

## Projects

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| A1 | Existing projects load and the loading state resolves | Pass | Playwright smoke; `/projects` API 200 |
| A2 | Search by name or objective works | Pass | API `q` filter; UI search |
| A3 | Status/priority filters work and totals agree | Pass | Pipeline/pagination tests; UI filter chips |
| A4 | Project details open from the list and by deep link | Pass | Playwright smoke deep link |
| A5 | Empty state appears when filters match nothing | Pass | UI inspection; EmptyState branch |
| A6 | Failed request shows an error and retry | Pass | Playwright aborts `/dashboard`; ErrorState |
| A7 | Create, edit, archive, questions and segments persist | Pass | `test_project_create_and_read`, journey |

## Recruitment

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| B1 | Dashboard and recruitment counts agree | Pass | `test_metrics.py`; `test_pipeline.py` |
| B2 | Every stage is represented, including terminal stages | Pass | Pipeline cards now include all ten |
| B3 | Status transitions persist and invalid ones are rejected | Pass | `test_recruitment_transitions_and_history` |
| B4 | Stage history is visible after reload | Pass | `test_recruitment_history_survives_list_view` |
| B5 | Segment coverage is calculated from actual records | Pass | `test_segment_coverage_is_derived_from_records` |
| B6 | Response-rate denominator is defined and correct | Pass | `test_selected_participants_are_not_counted_as_contacted` |
| B7 | Distinct participants are not double-counted | Pass | `test_distinct_participants_are_counted_once_across_projects` |

## Interviews

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| C1 | Interviews load; filters work | Pass | Playwright smoke; API tests |
| C2 | Scheduling and rescheduling work | Pass | `test_interview_lifecycle_and_recording_consent_gate` |
| C3 | Completion updates status, timestamp and recruitment | Pass | Journey; pipeline test |
| C4 | Cancelled interviews remain visible | Pass | Cancelled status retained; list filter |
| C5 | Detail workspace opens with guide, consent and evidence | Pass | Playwright journey |
| C6 | Recording requires recorded consent; no audio captured | Pass | Consent gate test |
| C7 | Summary is captured and visible | Pass | Journey UI assertion |

## Evidence and insights

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| D1 | Five evidence types are distinguishable | Pass | Schema enum; UI labels |
| D2 | Customer statement and researcher interpretation are separate | Pass | Evidence model; journey |
| D3 | Missing provenance stays visible and cannot be upgraded silently | Pass | `test_evidence_without_provenance_is_flagged` |
| D4 | Provenance can be corrected; clearing it re-flags the record | Pass | Playwright journey |
| D5 | Supporting and contradictory evidence can both be linked | Pass | Journey |
| D6 | Insight validation requires evidence | Pass | `test_insight_requires_evidence_before_validation` |
| D7 | Insights can be edited | Pass | Playwright journey |
| D8 | Cross-project evidence cannot be linked | Pass | `test_insight_rejects_evidence_from_another_project` |

## Decisions and actions

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| E1 | Decision records problem, rationale, owner, date, limitations | Pass | Schema; journey |
| E2 | Decisions link insights and/or evidence | Pass | `test_decision_links_and_action_creation` |
| E3 | Unevidenced decisions are labelled, not blocked | Pass | `test_decision_without_evidence_is_warned_not_hidden` |
| E4 | Actions have owner, due date, priority and status | Pass | `test_decision_links_and_action_creation` |
| E5 | Overdue actions are derived and clear on completion | Pass | `test_overdue_actions_are_derived_and_clear_on_completion` |
| E6 | Action status changes persist | Pass | Journey |

## Dashboard, analytics, search

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| F1 | Metrics are calculated from records | Pass | `test_dashboard_numbers_are_derived_not_hardcoded` |
| F2 | Dashboard and analytics agree | Pass | `test_dashboard_and_analytics_report_the_same_quantities` |
| F3 | Metric definitions are visible | Pass | UI; API `definition` field |
| F4 | Empty datasets and pending baselines are handled | Pass | Analytics basis labels; empty states |
| F5 | Loading and error states work | Pass | Playwright; UI branches |
| F6 | Search finds insight and evidence and navigates | Pass | Journey; Playwright |
| F7 | Related research suggestions work | Pass | `test_search_finds_insight_and_related_work` |

## Security, quality and delivery

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| G1 | No contact fields accepted or stored | Pass | Data-minimisation test |
| G2 | Demo role entry is labelled as non-authentication | Pass | Session notice test |
| G3 | CSV exports are labelled synthetic and formula-safe | Pass | Export test; `_csv_safe` |
| G4 | No secrets or `.env` in the image or repository | Pass | `.dockerignore`; `.gitignore` |
| G5 | Backend tests pass | Pass | 46 passed |
| G6 | Frontend typecheck and build pass | Pass | `tsc --noEmit`, `vite build` |
| G7 | Browser journey and accessibility checks pass | Pass | 7 Playwright tests |
| G8 | Docker Compose starts and both services are healthy | Pass | Compose verification |
| G9 | Documentation matches implementation | Pass | This documentation set |
| G10 | Production authentication implemented | **Not met — documented gap** | `AUTH.md`, `SECURITY.md` |
