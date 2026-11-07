"""Central project-level authorization.

One module answers the only question that matters for tenant isolation: may this
user act on this project, and at what level? Endpoints call the ``assert_*``
helpers instead of writing their own comparisons, so a new route cannot quietly
invent a weaker rule.

The permission model:

    project role     read   write research   write business   manage members
    viewer            yes         no               no                no
    editor            yes        yes              yes                no
    project_owner     yes        yes              yes               yes

Workspace administrators are implicit ``project_owner`` on every project.
Workspace role still gates *what* may be written (see ``app/core/auth.py``); the
project membership gates *where*. A request must satisfy both.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, UnauthorizedError
from app.models import ProjectMembership, User
from app.models.enums import ProjectRole

ROLE_RANK = {
    ProjectRole.VIEWER.value: 1,
    ProjectRole.EDITOR.value: 2,
    ProjectRole.PROJECT_OWNER.value: 3,
}

# Derived project links, expressed once so list scoping and single-record checks
# cannot drift apart.
PARTICIPANT_PROJECT_MODELS = ("recruitment_records", "interviews", "evidence", "feedback_records")


def is_workspace_admin(user: User) -> bool:
    return user.role == "admin"


def membership_for(db: Session, user_id: str, project_id: str) -> ProjectMembership | None:
    return db.execute(
        select(ProjectMembership).where(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == user_id,
        )
    ).scalar_one_or_none()


def role_for(db: Session, user: User, project_id: str) -> str | None:
    """The effective project role, or None when the user has no grant."""
    if user is None:
        return None
    if is_workspace_admin(user):
        return ProjectRole.PROJECT_OWNER.value
    membership = membership_for(db, user.id, project_id)
    return membership.role if membership else None


def can_read(db: Session, user: User, project_id: str) -> bool:
    return role_for(db, user, project_id) is not None


def can_write(db: Session, user: User, project_id: str) -> bool:
    role = role_for(db, user, project_id)
    return role is not None and ROLE_RANK[role] >= ROLE_RANK[ProjectRole.EDITOR.value]


def can_manage(db: Session, user: User, project_id: str) -> bool:
    role = role_for(db, user, project_id)
    return role is not None and ROLE_RANK[role] >= ROLE_RANK[ProjectRole.PROJECT_OWNER.value]


def visible_project_ids(db: Session, user: User) -> set[str] | None:
    """Project ids this user may read, or None when the user may read all.

    ``None`` rather than the full id list keeps list queries from building an
    ``IN`` clause with every project in the workspace.
    """
    if user is None:
        raise UnauthorizedError("Sign in to use this workspace.")
    if is_workspace_admin(user):
        return None
    return set(
        db.execute(
            select(ProjectMembership.project_id).where(ProjectMembership.user_id == user.id)
        ).scalars()
    )


def _deny(message: str = "You do not have access to this project.") -> None:
    raise ForbiddenError(message)


def require_actor(actor: User | None) -> User:
    if actor is None:
        raise UnauthorizedError("Sign in to use this workspace.")
    return actor


def assert_project_read(db: Session, actor: User | None, project_id: str) -> None:
    user = require_actor(actor)
    if not can_read(db, user, project_id):
        _deny()


def assert_project_write(db: Session, actor: User | None, project_id: str) -> None:
    user = require_actor(actor)
    if not can_write(db, user, project_id):
        _deny("Your role in this project does not allow changes.")


def assert_project_manage(db: Session, actor: User | None, project_id: str) -> None:
    user = require_actor(actor)
    if not can_manage(db, user, project_id):
        _deny("Only a project owner can manage this project's members.")


def require_project_read(db: Session, actor: User | None, project_id: str | None) -> None:
    """For list endpoints that optionally filter by a project."""
    if project_id is not None:
        assert_project_read(db, actor, project_id)


# --------------------------------------------------------------- entity links
def project_of_evidence(db: Session, evidence_id: str) -> str | None:
    from app.models import Evidence

    row = db.get(Evidence, evidence_id)
    return row.project_id if row else None


def project_of_feedback(db: Session, feedback_id: str) -> str | None:
    from app.models import FeedbackRecord

    row = db.get(FeedbackRecord, feedback_id)
    return row.project_id if row else None


def project_of_interview(db: Session, interview_id: str) -> str | None:
    from app.models import Interview

    row = db.get(Interview, interview_id)
    return row.project_id if row else None


def project_of_recruitment(db: Session, recruitment_id: str) -> str | None:
    from app.models import RecruitmentRecord

    row = db.get(RecruitmentRecord, recruitment_id)
    return row.project_id if row else None


def project_of_insight(db: Session, insight_id: str) -> str | None:
    from app.models import Insight

    row = db.get(Insight, insight_id)
    return row.project_id if row else None


def project_of_decision(db: Session, decision_id: str) -> str | None:
    from app.models import Decision

    row = db.get(Decision, decision_id)
    return row.project_id if row else None


def project_of_action(db: Session, action_id: str) -> str | None:
    """An action inherits its project from the decision or insight it serves."""
    from app.models import BusinessAction

    row = db.get(BusinessAction, action_id)
    if row is None:
        return None
    if row.decision_id:
        project = project_of_decision(db, row.decision_id)
        if project:
            return project
    if row.insight_id:
        return project_of_insight(db, row.insight_id)
    return None


def project_of_outcome(db: Session, outcome_id: str) -> str | None:
    from app.models import Outcome

    row = db.get(Outcome, outcome_id)
    return project_of_decision(db, row.decision_id) if row else None


def participant_project_ids(db: Session, participant_id: str) -> set[str]:
    """Every project in which this participant has a research record.

    Participants are workspace-level people, so they must be scoped through the
    records that place them in a study rather than through a column of their own.
    """
    from app.models import Evidence, FeedbackRecord, Interview, RecruitmentRecord

    ids: set[str] = set()
    ids.update(
        db.execute(
            select(RecruitmentRecord.project_id).where(
                RecruitmentRecord.participant_id == participant_id
            )
        ).scalars()
    )
    ids.update(
        db.execute(select(Interview.project_id).where(Interview.participant_id == participant_id)).scalars()
    )
    ids.update(
        db.execute(
            select(Evidence.project_id).where(Evidence.participant_id == participant_id)
        ).scalars()
    )
    ids.update(
        db.execute(
            select(FeedbackRecord.project_id).where(FeedbackRecord.participant_id == participant_id)
        ).scalars()
    )
    return {project_id for project_id in ids if project_id}


def assert_participant_read(db: Session, actor: User | None, participant_id: str) -> None:
    """A participant is readable when the user may read any of their projects."""
    user = require_actor(actor)
    ids = visible_project_ids(db, user)
    participant_projects = participant_project_ids(db, participant_id)
    if ids is None:
        return
    if not participant_projects or not (participant_projects & ids):
        _deny("This customer is not part of a project you can access.")


def assert_participant_write(db: Session, actor: User | None, participant_id: str) -> None:
    """Editing a shared customer requires editor standing on one of their studies."""
    user = require_actor(actor)
    if is_workspace_admin(user):
        return
    if not any(can_write(db, user, project_id) for project_id in participant_project_ids(db, participant_id)):
        _deny("You do not have permission to change this customer.")


def assert_entity_read(
    db: Session, actor: User | None, project_id: str | None, owner_id: str | None = None
) -> None:
    """Deny reads of orphaned or unauthorized records alike.

    A record with no project is workspace-level (an internal judgement recorded
    before it was attached to a study). Workspace administrators and the person
    who owns the record may read it; nobody else can use an unattached record as
    a back door around project scope.
    """
    user = require_actor(actor)
    if project_id is None:
        if is_workspace_admin(user) or (owner_id is not None and owner_id == user.id):
            return
        _deny("This record is not attached to a project you can access.")
    assert_project_read(db, user, project_id)


def assert_entity_write(
    db: Session, actor: User | None, project_id: str | None, owner_id: str | None = None
) -> None:
    user = require_actor(actor)
    if project_id is None:
        if is_workspace_admin(user) or (owner_id is not None and owner_id == user.id):
            return
        _deny("This record is not attached to a project you can change.")
    assert_project_write(db, user, project_id)
