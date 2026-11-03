# Tasks

Status as delivered. "Verified" means covered by an executed check, not merely written.

## Completed

| Area | Task | Verified by |
| --- | --- | --- |
| Foundation | FastAPI app, settings, SQLAlchemy models, Alembic revision, seed | App starts; pytest fixture |
| Foundation | Standard error envelope and validation handler | `test_unknown_ids_return_404_envelope`, validation tests |
| Projects | Create/read/update/archive, questions, segments, owner, filters | `test_project_create_and_read`, journey |
| Projects | Correct total when filtering by business function | API behaviour; pagination test |
| Participants | Directory, create, edit, eligibility, purchase context, history | `test_participant_creation_never_stores_contact_details` |
| Recruitment | Ten-stage pipeline with validated transitions | `test_recruitment_transitions_and_history` |
| Recruitment | Append-only history, including interview-driven changes | `test_scheduling_and_completing_an_interview_writes_history` |
| Recruitment | Distinct participant counting and response denominator | `test_pipeline.py` |
| Recruitment | Segment coverage from actual records | `test_segment_coverage_is_derived_from_records` |
| Interviews | Schedule, reschedule, cancel, complete, guide, consent, notes, summary | `test_interview_lifecycle_and_recording_consent_gate` |
| Interviews | Recording consent gate, recording off by default | Same test; `test_evidence_*` |
| Evidence | Five evidence types, provenance, review status, interpretation separation | `test_evidence_without_provenance_is_flagged` |
| Evidence | Review action and provenance correction in the UI | Playwright journey |
| Insights | Create, edit, link/unlink, contradictory role, validation review | Journey; insight tests |
| Insights | Cross-project evidence rejected | `test_insight_rejects_evidence_from_another_project` |
| Decisions | Register, rationale, limitations, evidence links, internal judgement label | Decision tests; journey |
| Actions | Create, edit status, owner, due date, priority, overdue | `test_overdue_actions_are_derived_and_clear_on_completion` |
| Dashboard | Derived metrics, timeline, segments, activity, outstanding work | `test_dashboard_numbers_are_derived_not_hardcoded` |
| Analytics | Basis-labelled metrics, reuse detail, measurement gaps | `test_analytics_labels_metric_basis` |
| Analytics | Agreement with the dashboard | `test_dashboard_and_analytics_report_the_same_quantities` |
| Search | Seven entity types, navigation, related research | Journey; search tests |
| UX | Loading, empty, error, retry, toasts, confirmations, accessibility | Playwright smoke + axe |
| UX | Executive Emerald redesign across all screens and both entry/navigation shells | `docs/design.md`, regenerated screenshots, axe |
| UX | Responsive layout verified at 375/768/1024/1440 plus the auth screen | `responsive.spec.ts` |
| Exports | All eight Settings downloads exercised in a browser and parsed | `exports.spec.ts` |
| Delivery | Docker images, Compose stack, health checks, volume | Compose verification |
| Delivery | 79 backend tests, 13 browser tests, clean typecheck/build | Final verification run |
| Docs | Product, architecture, data, API, security, operations, plan, defects | This documentation set |

## Remaining (prioritised)

| Priority | Task | Why it matters | Effort |
| --- | --- | --- | --- |
| P0 | Authentication and server-side role enforcement | Cannot host without it | 1 sprint |
| P0 | PostgreSQL deployment path | SQLite is single-writer | 2–3 days |
| P1 | Code-split the frontend bundle | 988 kB single chunk warns on build | 1 day |
| P1 | Paginate recruitment, interviews, insights, decisions, actions | Lists currently load fully | 2–3 days |
| P1 | Immutable audit log for deletions | Contradictions can be deleted in this prototype | 2 days |
| P2 | Decision outcome review date | Closes the "did it work?" gap | 3 days |
| P2 | Reuse by business function | Single reuse rate hides team behaviour | 1 day |
| P2 | Export formats beyond CSV (PDF brief) | Handover artefact for stakeholders | 2 days |
| P3 | Component-level tests | Faster feedback than full browser runs | 2 days |
| P3 | Screenshot regression snapshots | Detect unintended visual drift | 1 day |

## Explicitly out of scope

Real outreach, audio capture, CRM/calendar integration, LLM summarisation, statistical
confidence, multi-tenant organisation management, billing.
