# Authorization and permissions

Status: **implemented and tested** at the API layer. The browser mirrors the rules for usability; it is
not the security boundary.

## 1. The problem this fixes

The earlier release authenticated users and enforced a workspace role on writes, but every signed-in
user could read every project. A project id was the only thing between an outside contractor and
another team's customer quotes — a classic IDOR/BOLA (insecure direct object reference / broken object
level authorization) gap. It was recorded as QA-10 (P0) and is now closed.

## 2. Two gates, not one

A request must pass **both** gates:

| Gate | Question | Where |
| --- | --- | --- |
| Workspace role | May this kind of user perform this kind of write at all? | `backend/app/core/auth.py` (middleware) |
| Project membership | May this user act on *this* project, at what level? | `backend/app/services/access.py` (`assert_*`) |

Effective permission is the **intersection**. A workspace `business_owner` with `viewer` membership
can read a project but cannot write a decision in it. A workspace `cx` user with `editor` membership
still cannot write, because the workspace gate refuses the method.

Workspace `admin` is an implicit `project_owner` on every project. That is deliberate: administrators
run the workspace and must not be able to lock themselves out. It is also the main residual risk
(see §10).

## 3. Project roles

Stored as text in `project_memberships.role` (adding a role does not rewrite the table).

| Project role | Read | Write research records | Write decisions/actions/outcomes | Manage members / archive |
| --- | --- | --- | --- | --- |
| `viewer` | yes | no | no | no |
| `editor` | yes | yes | yes (if workspace role allows) | no |
| `project_owner` | yes | yes | yes (if workspace role allows) | yes |

Ranking is `viewer < editor < project_owner`. There is exactly one membership row per
(project, user), enforced by `uq_project_membership`.

Workspace write policy (unchanged, and still authoritative):

| Workspace role | Research writes | Decision/action/outcome writes | Settings / users / demo |
| --- | --- | --- | --- |
| `researcher` | yes | no | demo reset only |
| `admin` | yes | yes | yes |
| `business_owner`, `ceo` | no | yes | no |
| `cx` | no | no | no |

## 4. Enforcement points

Every project-scoped endpoint resolves the record first, then calls a helper. Helpers are centralized
so a new route cannot quietly invent a weaker rule.

| Area | Read | Write |
| --- | --- | --- |
| Projects, questions, journey | `assert_project_read` | `assert_project_write` / `assert_project_manage` |
| Participants | `assert_participant_read` | `assert_participant_write` |
| Recruitment, interviews, evidence, feedback, insights | `assert_project_read` (via the record's project) | `assert_project_write` |
| Decisions, actions, outcomes | `assert_entity_read` | `assert_entity_write` |
| Membership list | `assert_project_read` | `assert_project_manage` |
| Project list / dashboard / analytics / search / exports | queries scoped by `visible_project_ids` | n/a (reads) |

### Participants are workspace-level people

A participant has no `project_id` of their own. Access is derived from the records that place them in
a study: recruitment, interviews, evidence and feedback (`participant_project_ids`). A user may read a
participant if they can read **any** project that participant appears in. Editing a shared customer
requires editor standing on at least one of those studies.

### Records with no project

A decision or insight may be recorded before it is attached to a study. Such an orphan is readable and
writable only by a workspace admin or its `owner_id`. This prevents an unattached record from becoming
a back door around project scope. Linking project evidence or an insight adopts the project, and
cross-project links are rejected.

### List, dashboard, analytics, search and exports

These previously ran global queries and leaked counts and names. They now derive their scope from
`visible_project_ids`:

- a non-admin sees only projects they hold a membership on;
- totals, segment counts, overdue counts and analytics bases are computed from the same visible set;
- exports filter by the same ids, so a CSV cannot contain another team's records;
- search returns only entities in visible projects (workspace-level decisions only for admins/owners).

`visible_project_ids` returns `None` for admins (meaning "all") rather than building an `IN` clause
with every project id.

## 5. Membership API

| Method | Path | Who |
| --- | --- | --- |
| `GET` | `/api/v1/projects/{id}/members` | anyone who can read the project |
| `POST` | `/api/v1/projects/{id}/members` | `project_owner` (or admin) |
| `PATCH` | `/api/v1/projects/{id}/members/{membership_id}` | `project_owner` (or admin) |
| `DELETE` | `/api/v1/projects/{id}/members/{membership_id}` | `project_owner` (or admin) |

Adding an existing member updates their role instead of creating a duplicate. The role must be one of
`viewer`, `editor`, `project_owner`. A project must retain at least one `project_owner` membership;
demoting or deleting the last one returns `409`. (Admins remain implicit owners, so this rule protects
the project's own ownership list rather than preventing total lockout.)

Creation of a project grants its creator `project_owner` automatically. Reassigning a project's
`owner_id` grants the new owner `project_owner` as well.

## 6. Status codes

| Situation | Response |
| --- | --- |
| No session | `401 unauthorized` |
| Signed in, no grant on the project | `403 forbidden` — *"You do not have access to this project."* |
| Signed in, grant too weak for the action | `403 forbidden` — *"Your role in this project does not allow changes."* |
| Project does not exist | `404 not found` |
| Cross-project evidence/insight/decision link | `403`/`400` with a rule message |
| Removing the last project owner | `409 conflict` |

`403` is used rather than `404` so the client can distinguish "not yours" from "does not exist". This
does reveal that a project id exists; in this product that is acceptable, because ids are UUIDs and the
projects belong to one organisation. A multi-tenant SaaS would prefer `404` to avoid confirming
existence.

## 7. Frontend behaviour (supplementary)

- `ProjectProvider` loads the visible projects once and exposes the selected project and the user's
  role in it.
- The sidebar project switcher lists only accessible projects.
- Project detail shows an "access" pill; Edit is hidden for viewers, Archive and Members only for
  project owners; a direct visit to an inaccessible project renders `PermissionDenied` on a `403`.
- "New project" is offered only to researchers and admins.
- Settings is admin-only in navigation; the API enforces it regardless.

Hiding a control is a usability decision, never the control itself. The Playwright and pytest suites
call the API directly to prove the server refuses.

## 8. Backfill of existing data

Migration `d4e8f1a2c7b9` is additive and deterministic. It grants:

1. each project's existing `owner_id` → `project_owner`;
2. every active workspace admin → `project_owner` on every project;
3. demonstrable contributors → `editor` on the project(s) where they already worked:
   interview interviewer, evidence capturer, feedback creator, owner of an insight, decision or outcome;
4. nobody else.

It deliberately does **not** grant everyone everything, which would preserve the vulnerability under a
new table name. Users who previously relied on workspace-wide reading now need a grant.

Verified on a copy of the seeded QA database: 15 memberships (10 `project_owner`, 5 `editor`), zero
admins without a membership, zero project owners without one. The copy was deleted afterwards; the
working database was not modified.

## 9. Test evidence

`backend/tests/test_project_authorization.py` — **16 tests**, all passing, covering:

1. an authorized project is readable with the correct role;
2. an unauthorized project cannot be read (project and journey);
3. an unauthorized project cannot be updated or archived;
4. nested participant/recruitment/interview records do not leak;
5. feedback, evidence and insight records from another project are denied;
6. decisions and outcomes from another project are denied;
7. dashboard and analytics counts reflect only visible projects;
8. exports exclude other projects;
9. global search and list endpoints do not leak project names;
10. a cross-project evidence link is rejected;
11. a cross-project decision link is rejected;
12. a viewer cannot write;
13. a researcher cannot use workspace administration (settings/users);
14. a project owner can manage only their own project's members;
15. removing a member revokes access immediately;
16. unauthenticated requests are denied.

The synthetic team is deliberately uneven (admin on all; a researcher editor everywhere; a business
owner with owner/editor/viewer grants and no access to two studies; a CX editor on one study; a CEO
viewer everywhere). Tests use real HTTP sessions, not the frontend.

## 10. Residual risks and explicit limits

- **Admin bypass.** Workspace admins implicitly own every project. This is intentional but means the
  boundary separates team members, not administrators from tenants. A true multi-tenant deployment
  needs workspace/tenant isolation above this layer.
- **No per-record sharing.** There are no share links, guest accounts or field-level permissions.
- **Membership audit is partial.** Adding a member writes an `activity` row; role changes and removals
  do not yet. Adding those events is a small, recommended next step.
- **Participant edit rule is permissive by design.** Editor standing on any study containing a
  participant permits editing their shared profile.
- **Frontend cache.** `ProjectProvider` fetches on load; if a grant is revoked, the UI may show a stale
  control until refresh, but the API refuses the action immediately (proved by test 15).

## 11. How to verify by hand

```bash
cd backend
./.venv/Scripts/python.exe -m pytest tests/test_project_authorization.py -q
```

Then, with the demo running:

1. Sign in as **Vikram** (CX, editor on the shampoo study only) and open a project he has no grant on
   (e.g. the routine campaign): the API returns `403` and the UI shows the access-denied state.
2. Sign in as **Priya** (researcher, owner of the shampoo study) and open Project → Members: she can
   grant/revoke roles there.
3. Sign in as **Asha** (CEO, viewer everywhere): records are readable, write controls are absent, and
   a direct `PATCH` is refused with `403`.
