# Requirements Traceability

Every requirement from `prd.md` mapped to the screen, endpoint, entity and test that implement
it. Test names refer to files in `backend/tests/` unless stated otherwise.

| # | Requirement | UI | API | Data | Test |
| --- | --- | --- | --- | --- | --- |
| R1 | Define research questions | Project detail | `POST /projects`, `PATCH /projects/{id}/questions` | `research_questions` | `test_project_create_and_read` |
| R2 | Organise research projects | Projects, new project | `GET/POST/PATCH /projects` | `research_projects` | `test_journey` |
| R3 | Manage participants | Participants, detail | `GET/POST/PATCH /participants` | `participants` | `test_participant_creation_never_stores_contact_details` |
| R4 | Import approved participants (CSV) | Participants | `POST /participants/import` | `participants` | `test_participant_import_*` (unit coverage in `test_api.py`) |
| R5 | Recruit participants through defined stages | Recruitment | `POST /recruitment`, `PATCH /recruitment/{id}` | `recruitment_records`, `recruitment_events` | `test_recruitment_transitions_and_history` |
| R6 | Schedule and conduct interviews | Interviews, workspace | `POST/PATCH /interviews` | `interviews`, `interview_guide_questions` | `test_interview_lifecycle_and_recording_consent_gate` |
| R7 | Capture customer evidence | Interview workspace, evidence | `POST /evidence` | `evidence` | `test_evidence_with_provenance_is_verified` |
| R8 | Preserve evidence provenance | Evidence detail | `PATCH /evidence/{id}` | `evidence.provenance`, `provenance_status` | `test_evidence_without_provenance_is_flagged` |
| R9 | Develop and validate insights | Insights, insight detail | `POST/PATCH /insights`, `POST /insights/{id}/evidence` | `insights`, `insight_evidence` | `test_insight_requires_evidence_before_validation` |
| R10 | Keep contradictory evidence | Insight detail | `POST /insights/{id}/evidence` with `role=contradictory` | `insight_evidence.role` | `test_full_journey_produces_traceable_records` |
| R11 | Connect insights to decisions | Decision detail | `POST /decisions/{id}/links` | `decisions`, `decision_insights` | `test_decision_links_and_action_creation` |
| R12 | Assign and track actions | Actions | `POST/PATCH /actions` | `business_actions` | `test_overdue_actions_are_derived_and_clear_on_completion` |
| R13 | Reuse existing research | Search, analytics | `GET /search`, `GET /analytics` | derived from all entities | `test_search_finds_insight_and_related_work` |
| R14 | Measure research operations | Overview, analytics | `GET /dashboard`, `GET /analytics` | derived queries | `test_dashboard_and_analytics_agree` |
| R15 | Maintain an auditable history | Activity lists, timelines | embedded in read models | `activity_logs`, `recruitment_events` | `test_unlinking_is_recorded_in_the_activity_trail` |
| R16 | Authenticate users | Login, sign out | `POST /auth/login`, `/auth/logout`, `GET /auth/me` | `users`, `auth_sessions` | `test_password_login_and_logout` |
| R17 | Authorise writes by role | Role-dependent controls | middleware policy | `users.role` | `test_role_enforcement_on_writes` |
| R18 | Export records as CSV | Settings | `GET /exports/{entity}.csv` | all listed entities | `test_exports.py` (8 cases) |
| R19 | No synthetic data in production | Empty states | seed disabled by default | empty tables | `test_first_run_registration_claims_an_empty_workspace` |
| R20 | Handle empty datasets | Empty states on every list | reads return empty collections | — | `test_empty_dataset_exports_a_header_only_file` |

## Non-functional requirements

| # | Requirement | Evidence |
| --- | --- | --- |
| N1 | Server-side authorisation cannot be bypassed by the client | `test_anonymous_requests_are_rejected`, `test_session_is_not_trusted_from_a_client_supplied_header_without_demo_mode` |
| N2 | Consent cannot be bypassed for recording | `test_interview_lifecycle_and_recording_consent_gate` |
| N3 | Data minimisation (no contact fields) | Schema inspection; `test_participant_creation_never_stores_contact_details` |
| N4 | Spreadsheet formula injection neutralised | `test_exports_neutralise_spreadsheet_formulas` |
| N5 | Migrations reproduce the schema | `alembic upgrade head`; `database.md` |
| N6 | Health endpoint reports database state | `test_health_reports_ok` |
| N7 | Responsive layout, keyboard access, axe checks | `docs/accessibility.md`; `frontend/e2e/a11y.spec.ts` |
| N8 | Deployment documented and reproducible | `deployment.md`; `Dockerfile`s; `compose.yaml` |

## Gaps

- R4 (CSV import) is implemented in the API and exercised by unit coverage; it has no dedicated
  end-to-end browser test.
- No requirement is traced to a formal user-acceptance test with real users. All test data is
  synthetic.
