"""Recruitment pipeline transitions.

One function owns the rule set so a stage can only change in one place, whether
the change comes from the pipeline board, from scheduling an interview or from
completing one. Every transition appends an immutable history event: the whole
point of the pipeline is that a participant's path stays visible after the fact.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import RuleViolationError
from app.models import Participant, RecruitmentEvent, RecruitmentRecord
from app.models.enums import RECRUITMENT_TRANSITIONS, RecruitmentStage

# Stages that mean the participant actually replied.
RESPONDED_STAGES = {"responded", "scheduled", "completed", "declined", "withdrawn"}
# Stages that mean an invitation actually reached the participant.
CONTACTED_STAGES = {"invited", "responded", "scheduled", "completed", "declined", "no_response", "withdrawn"}


def advance_stage(
    db: Session,
    record: RecruitmentRecord,
    to_stage: str,
    *,
    note: str = "",
    actor_id: str | None = None,
    force: bool = False,
) -> RecruitmentEvent | None:
    """Move a recruitment record forward and record why.

    ``force`` exists for workflow side effects that legitimately jump stages —
    booking an interview for someone still marked "selected" moves them to
    "scheduled" — but it never skips the history event. Invalid user-driven
    moves are rejected rather than silently corrected.
    """
    previous = record.stage
    if previous == to_stage:
        return None

    if not force:
        allowed = {s.value for s in RECRUITMENT_TRANSITIONS.get(RecruitmentStage(previous), set())}
        if to_stage not in allowed:
            raise RuleViolationError(
                f"Cannot move from '{previous}' to '{to_stage}'.",
                details={"allowed": sorted(allowed)},
            )

    now = datetime.now(timezone.utc)
    record.stage = to_stage
    record.updated_at = now

    if to_stage == "invited":
        if record.invited_at is None:
            record.invited_at = now
        # Re-inviting a participant starts the response clock again.
        record.responded_at = None
    if to_stage in RESPONDED_STAGES and record.responded_at is None:
        record.responded_at = now
    if to_stage in ("invited", "scheduled", "completed"):
        participant = db.get(Participant, record.participant_id)
        if participant is not None:
            participant.last_research_contact_at = now

    event = RecruitmentEvent(
        recruitment_id=record.id,
        from_stage=previous,
        to_stage=to_stage,
        note=note or f"Moved from {previous.replace('_', ' ')} to {to_stage.replace('_', ' ')}.",
        actor_id=actor_id,
        created_at=now,
    )
    db.add(event)
    return event
