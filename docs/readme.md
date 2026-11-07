# Documentation Index

Two sets exist. The **canonical set** below is the current reference and matches the
implementation. The **original discovery set** (numbered files) records the thinking from the
first build and is retained for context; where they disagree, the canonical set wins.

## Canonical set

| Document | Read it for |
| --- | --- |
| [prd](prd.md) | Business problem, users, requirements, non-goals |
| [architecture](architecture.md) | Module boundaries, decisions, deployment shape |
| [hld](hld.md) | System components, relationships, data flows |
| [lld](lld.md) | Module responsibilities, validation, error handling |
| [tech_stack](tech_stack.md) | Pinned versions and deliberate omissions |
| [design](design.md) | Palette, typography, components, states, accessibility |
| [database](database.md) | ERD, tables, constraints, indexes, migrations |
| [data_dictionary](data_dictionary.md) | Column-level reference generated from the models |
| [api](api.md) | Endpoint reference, auth requirements, vocabularies |
| [auth](auth.md) | Password sessions, role matrix, known gaps |
| [security](security.md) | Threat model, data protection, prerequisites |
| [testing](testing.md) | Suites, commands, executed results, gaps |
| [deployment](deployment.md) | Docker, Windows setup, environment, migrations |
| [backup_recovery](backup_recovery.md) | Backup and restore procedure with a verified run |
| [operations](operations.md) | Runbook, incidents, rollback, handover |
| [performance](performance.md) | Measured local latency and its limits |
| [accessibility](accessibility.md) | Implemented behaviour and how it is checked |
| [troubleshooting](troubleshooting.md) | Real failure modes and their fixes |
| [integration](integration.md) | Integration status and the contract for adding one |
| [implementation_plan](implementation_plan.md) | Delivery phases, dependencies, risks |
| [tasks](tasks.md) | Delivered work and prioritised remaining work |
| [roadmap](roadmap.md) | Now / next / later |
| [changelog](changelog.md) | What changed in each release |
| [decisions](decisions.md) | Architecture decision records |
| [risks](risks.md) | Risk register and open questions |
| [acceptance_criteria](acceptance_criteria.md) | Every criterion with verification status |
| [requirements_traceability](requirements_traceability.md) | Requirement → UI → API → data → test |
| [git_commit_plan](git_commit_plan.md) | Intended units and commit rules |
| [DEFECT_REGISTER](DEFECT_REGISTER.md) | Confirmed defects and gaps |
| [final-qa-baseline](final-qa-baseline.md) | Measured starting point and claim discrepancies |
| [workflow-validation-matrix](workflow-validation-matrix.md) | Every workflow with UI, API, data, permissions and evidence |
| [page-by-page-qa](page-by-page-qa.md) | Every route, interaction, defect and screenshot |
| [bug-fix-register](bug-fix-register.md) | Reproductions, root causes, fixes and open P0s |
| [final-delivery-report](final-delivery-report.md) | Current delivery record and actual results |
| [final-recruiter-evaluation](final-recruiter-evaluation.md) | Independent scorecard and recommendation |
| [STAGE_COMPLETION_REPORT](STAGE_COMPLETION_REPORT.md) | Historical delivery report |

## Original discovery set

The numbered files (`01-product-brief.md` … `20-three-week-plan.md`) are the first-build record.
Several of them state that the API has no authentication; that was true then and is not true now.
Treat `auth.md`, `security.md` and `acceptance_criteria.md` as authoritative.

## Suggested reading order

1. `../README.md` — run it in two minutes.
2. `prd.md` — why it exists.
3. `architecture.md` then `hld.md` — how it is built.
4. `auth.md` and `security.md` — who may do what, and what is still missing.
5. `acceptance_criteria.md`, `testing.md` and `final-qa-baseline.md` — what was actually verified, and what the starting point really was.
6. `workflow-validation-matrix.md` and `bug-fix-register.md` — end-to-end status and remaining P0s.
7. `09-demo-script.md` — follow along with the app open.

## Maintaining this set

Update the canonical document in the same commit as the behaviour change. The acceptance criteria
and testing documents must state only checks that were executed; a defect moves out of
`DEFECT_REGISTER` only after its verification passes. Documentation that describes functionality
which is not implemented is treated as a defect.
