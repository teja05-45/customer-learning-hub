# Documentation Index

Two sets exist. The **canonical set** below is the current reference and matches the
implementation. The **original discovery set** (numbered files) records the thinking from the
first build and is retained for context; where they disagree, the canonical set wins.

## Canonical set

| Document | Read it for |
| --- | --- |
| [PRD](PRD.md) | Business problem, users, requirements, non-goals, success signals |
| [ARCHITECTURE](ARCHITECTURE.md) | Module boundaries, services, data integrity, trade-offs |
| [HLD](HLD.md) | Containers, flows, non-functional requirements, failure behaviour |
| [LLD](LLD.md) | Functions, algorithms, rule implementations, test seams |
| [TECH_STACK](TECH_STACK.md) | Pinned versions and deliberate omissions |
| [DESIGN](DESIGN.md) | Palette, typography, components, required states, accessibility |
| [DATABASE](DATABASE.md) | ERD, tables, constraints, migrations, seeding |
| [API](API.md) | Endpoint reference, status vocabularies, examples |
| [AUTH](AUTH.md) | Demo identity, why it is not authentication, production path |
| [SECURITY](SECURITY.md) | Data minimisation, consent, validation, threat table |
| [TESTING](TESTING.md) | Suites, commands, actual results, what is not covered |
| [DEPLOYMENT](DEPLOYMENT.md) | Docker, Windows setup, environment, troubleshooting |
| [OPERATIONS](OPERATIONS.md) | Runbook, backup, incidents, rollback, handover |
| [IMPLEMENTATION_PLAN](IMPLEMENTATION_PLAN.md) | Three-week FDE plan, dependencies, ownership |
| [TASKS](TASKS.md) | Delivered work and prioritised remaining work |
| [ROADMAP](ROADMAP.md) | Now / next / later, and what is not planned |
| [CHANGELOG](CHANGELOG.md) | What changed in the hardening release |
| [DECISIONS](DECISIONS.md) | Twelve architecture decisions with consequences |
| [RISKS](RISKS.md) | Risk register, open questions, escalation |
| [ACCEPTANCE_CRITERIA](ACCEPTANCE_CRITERIA.md) | Every criterion with verification evidence |
| [DEFECT_REGISTER](DEFECT_REGISTER.md) | Confirmed defects, gaps, non-reproduced reports |
| [STAGE_COMPLETION_REPORT](STAGE_COMPLETION_REPORT.md) | Delivered scope, results, remaining gaps |

## Original discovery set

| Document | Topic |
| --- | --- |
| [01-product-brief](01-product-brief.md) | Initial product framing |
| [02-users-and-roles](02-users-and-roles.md) | Roles and permissions thinking |
| [03-core-workflows](03-core-workflows.md) | Workflow narrative |
| [04-information-architecture](04-information-architecture.md) | Screens and navigation |
| [05-data-model](05-data-model.md) | Data model rationale |
| [06-api-reference](06-api-reference.md) | Narrative API examples |
| [07-frontend-architecture](07-frontend-architecture.md) | Component structure |
| [08-design-system](08-design-system.md) | Original design tokens |
| [09-demo-script](09-demo-script.md) | Walkthrough for a reviewer |
| [10-data-dictionary](10-data-dictionary.md) | Field-level definitions |
| [11-testing](11-testing.md) | Original test strategy |
| [12-deployment](12-deployment.md) | Original deployment notes |
| [13-security-and-privacy](13-security-and-privacy.md) | Privacy analysis |
| [14-accessibility](14-accessibility.md) | Accessibility rationale |
| [15-tradeoffs](15-tradeoffs.md) | Product and technical trade-offs |
| [16-metrics](16-metrics.md) | Metric definitions and limits |
| [17-limitations-and-next-steps](17-limitations-and-next-steps.md) | Known gaps |
| [18-evaluation-guide](18-evaluation-guide.md) | How to assess the prototype |
| [19-maintenance-runbook](19-maintenance-runbook.md) | Original runbook |
| [20-three-week-plan](20-three-week-plan.md) | Original delivery plan |

## Suggested reading order

1. `../README.md` — run it in two minutes.
2. `PRD.md` — why it exists.
3. `ARCHITECTURE.md` then `HLD.md` — how it is built.
4. `DEFECT_REGISTER.md` and `ACCEPTANCE_CRITERIA.md` — what was actually verified.
5. `AUTH.md`, `SECURITY.md`, `RISKS.md` — honest limits.
6. `09-demo-script.md` — follow along with the app open.

## Maintaining this set

When behaviour changes, update the canonical document in the same commit as the code. The
acceptance criteria and testing documents must state only checks that were executed; a defect
moves from `DEFECT_REGISTER` to `CHANGELOG` only after its verification passes.
