"""Executive dashboard aggregation.

Every number here is derived from rows in the database. Nothing is hardcoded.
Where a metric has a judgement call behind it (response rate, research reuse)
the definition travels with the value so the UI can show it.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ActivityLog,
    BusinessAction,
    Decision,
    Evidence,
    Insight,
    InsightEvidence,
    Interview,
    Participant,
    RecruitmentRecord,
    ResearchProject,
    ResearchQuestion,
)
from app.schemas.dashboard import (
    ActivityItem,
    DashboardResponse,
    LearningSignals,
    ResponseRate,
    SegmentPoint,
    StatusCount,
    TimelinePoint,
)
from app.services.common import as_aware, month_key, month_sequence
from app.services.serializers import user_map
from app.services.serializers import (
    REUSE_WINDOW_DAYS,
    action_out,
    insight_is_reused,
    insight_summary,
    interview_summary,
    project_summary,
)

ACTIVE_STATUSES = ("draft", "planning", "recruiting", "in_progress", "analysis")
CONTACTED_STAGES = ("invited", "responded", "scheduled", "completed", "declined", "no_response", "withdrawn")

RESPONSE_DEFINITION = (
    "Invited participants who replied (accepted, scheduled, declined or withdrew) divided by participants "
    "who were actually invited through the controlled Ops process. Participants only identified or selected "
    "are excluded from the denominator."
)
REUSE_DEFINITION = (
    f"An insight counts as reused when it is linked to two or more decisions, or when a decision was linked "
    f"at least {REUSE_WINDOW_DAYS} days after the insight was created."
)
DATA_NOTE = (
    "All people, conversations and outcomes in this workspace are synthetic demonstration data generated for "
    "the prototype. No real customer was contacted and no Everyday Goods system is connected."
)


def _count(db: Session, stmt) -> int:
    return db.execute(stmt).scalar_one()


def _visible(column, project_ids: set[str] | None) -> list:
    """Extra WHERE clauses for project scope. None means 'workspace-wide'."""
    return [] if project_ids is None else [column.in_(project_ids)]


def build_dashboard(
    db: Session, months: int = 6, project_ids: set[str] | None = None
) -> DashboardResponse:
    now = datetime.now(timezone.utc)

    active_projects = _count(
        db,
        select(func.count(ResearchProject.id)).where(
            ResearchProject.status.in_(ACTIVE_STATUSES), *_visible(ResearchProject.id, project_ids)
        ),
    )
    interviews_completed = _count(
        db,
        select(func.count(Interview.id)).where(
            Interview.status == "completed", *_visible(Interview.project_id, project_ids)
        ),
    )
    upcoming_rows = (
        db.execute(
            select(Interview)
            .where(
                Interview.status.in_(("planned", "scheduled")),
                *_visible(Interview.project_id, project_ids),
            )
            .order_by(Interview.scheduled_at.asc())
        )
        .scalars()
        .all()
    )
    upcoming = [i for i in upcoming_rows if as_aware(i.scheduled_at) and as_aware(i.scheduled_at) >= now]

    invited = _count(
        db,
        select(func.count(RecruitmentRecord.id)).where(
            RecruitmentRecord.invited_at.is_not(None),
            *_visible(RecruitmentRecord.project_id, project_ids),
        ),
    )
    responded = _count(
        db,
        select(func.count(RecruitmentRecord.id)).where(
            RecruitmentRecord.responded_at.is_not(None),
            *_visible(RecruitmentRecord.project_id, project_ids),
        ),
    )
    response_rate = ResponseRate(
        value=round(responded / invited, 4) if invited else None,
        display=f"{round(responded / invited * 100)}%" if invited else "No invitations yet",
        numerator=responded,
        denominator=invited,
        definition=RESPONSE_DEFINITION,
        sample_warning=(
            f"Based on only {invited} invitation(s). Treat this as a signal about recruitment effort, "
            "not as a customer-base statistic."
            if 0 < invited < 12
            else None
        ),
    )

    participants_contacted = _count(
        db,
        select(func.count(func.distinct(RecruitmentRecord.participant_id))).where(
            RecruitmentRecord.stage.in_(CONTACTED_STAGES),
            *_visible(RecruitmentRecord.project_id, project_ids),
        ),
    )

    insights_awaiting_review = _count(
        db,
        select(func.count(Insight.id)).where(
            Insight.status.in_(("draft", "under_review")), *_visible(Insight.project_id, project_ids)
        ),
    )

    decision_rows = (
        db.execute(select(Decision).where(*_visible(Decision.project_id, project_ids))).scalars().all()
    )
    decisions_with_evidence = len([d for d in decision_rows if d.evidence_links or d.insight_links])

    action_stmt = select(BusinessAction)
    if project_ids is not None:
        action_stmt = action_stmt.where(
            BusinessAction.decision_id.in_(select(Decision.id).where(Decision.project_id.in_(project_ids)))
        )
    action_rows = db.execute(action_stmt).scalars().all()
    open_actions = [a for a in action_rows if a.status != "completed"]
    overdue = [a for a in open_actions if a.due_date and a.due_date < date.today()]

    insight_rows = (
        db.execute(select(Insight).where(*_visible(Insight.project_id, project_ids))).scalars().all()
    )
    with_evidence = 0
    reused = 0
    for insight in insight_rows:
        link_count = _count(
            db, select(func.count(InsightEvidence.id)).where(InsightEvidence.insight_id == insight.id)
        )
        if link_count:
            with_evidence += 1
        if insight_is_reused(db, insight):
            reused += 1

    total_insights = len(insight_rows)
    unresolved = _count(
        db,
        select(func.count(ResearchQuestion.id)).where(
            ResearchQuestion.is_resolved.is_(False),
            *_visible(ResearchQuestion.project_id, project_ids),
        ),
    )
    unevidenced_decisions = len([d for d in decision_rows if not d.evidence_links and not d.insight_links])

    learning = LearningSignals(
        findings_with_evidence=with_evidence,
        findings_total=total_insights,
        findings_coverage_display=(
            f"{with_evidence} of {total_insights} findings link to source evidence" if total_insights else "No findings yet"
        ),
        decisions_supported=decisions_with_evidence,
        decisions_total=len(decision_rows),
        insights_reused=reused,
        insights_reuse_display=(
            f"{reused} of {total_insights} findings reused after the project closed" if total_insights else "No findings yet"
        ),
        unresolved_questions=unresolved,
        overdue_actions=len(overdue),
        unevidenced_decisions=unevidenced_decisions,
    )

    # --- timeline -----------------------------------------------------------
    window = month_sequence(months, now)
    buckets = {key: {"interviews": 0, "evidence": 0, "insights": 0} for key, _ in window}
    for interview in db.execute(
        select(Interview).where(
            Interview.status == "completed", *_visible(Interview.project_id, project_ids)
        )
    ).scalars():
        when = as_aware(interview.completed_at or interview.scheduled_at)
        if when and month_key(when) in buckets:
            buckets[month_key(when)]["interviews"] += 1
    for ev in db.execute(select(Evidence).where(*_visible(Evidence.project_id, project_ids))).scalars():
        when = as_aware(ev.captured_at)
        if when and month_key(when) in buckets:
            buckets[month_key(when)]["evidence"] += 1
    for insight in insight_rows:
        when = as_aware(insight.created_at)
        if when and month_key(when) in buckets:
            buckets[month_key(when)]["insights"] += 1
    timeline = [
        TimelinePoint(month=key, label=label, **buckets[key]) for key, label in window
    ]

    # --- segments -----------------------------------------------------------
    segment_points: list[SegmentPoint] = []
    if project_ids is None:
        participant_counts = dict(
            db.execute(select(Participant.segment, func.count(Participant.id)).group_by(Participant.segment)).all()
        )
    else:
        participant_counts = dict(
            db.execute(
                select(Participant.segment, func.count(func.distinct(Participant.id)))
                .join(RecruitmentRecord, RecruitmentRecord.participant_id == Participant.id)
                .where(RecruitmentRecord.project_id.in_(project_ids))
                .group_by(Participant.segment)
            ).all()
        )
    interview_counts = dict(
        db.execute(
            select(Participant.segment, func.count(Interview.id))
            .join(Participant, Participant.id == Interview.participant_id)
            .where(*_visible(Interview.project_id, project_ids))
            .group_by(Participant.segment)
        ).all()
    )
    evidence_counts = dict(
        db.execute(
            select(Evidence.segment, func.count(Evidence.id))
            .where(*_visible(Evidence.project_id, project_ids))
            .group_by(Evidence.segment)
        ).all()
    )
    for segment in sorted(set(participant_counts) | set(evidence_counts) | set(interview_counts)):
        segment_points.append(
            SegmentPoint(
                segment=segment,
                participants=participant_counts.get(segment, 0),
                interviews=interview_counts.get(segment, 0),
                evidence=evidence_counts.get(segment, 0),
            )
        )

    decision_status = [
        StatusCount(status=status, count=count)
        for status, count in db.execute(
            select(Decision.status, func.count(Decision.id))
            .where(*_visible(Decision.project_id, project_ids))
            .group_by(Decision.status)
        ).all()
    ]
    action_status_stmt = select(BusinessAction.status, func.count(BusinessAction.id))
    if project_ids is not None:
        action_status_stmt = action_status_stmt.where(
            BusinessAction.decision_id.in_(select(Decision.id).where(Decision.project_id.in_(project_ids)))
        )
    action_status = [
        StatusCount(status=status, count=count)
        for status, count in db.execute(action_status_stmt.group_by(BusinessAction.status)).all()
    ]

    recent_insights = (
        db.execute(
            select(Insight)
            .where(*_visible(Insight.project_id, project_ids))
            .order_by(Insight.created_at.desc())
            .limit(5)
        )
        .scalars()
        .all()
    )
    recent_activity_rows = (
        db.execute(
            select(ActivityLog)
            .where(*_visible(ActivityLog.project_id, project_ids))
            .order_by(ActivityLog.created_at.desc())
            .limit(10)
        )
        .scalars()
        .all()
    )
    actor_refs = user_map(db, {a.actor_id for a in recent_activity_rows})
    outstanding = sorted(
        open_actions, key=lambda a: (a.due_date is None, a.due_date or date.max)
    )[:6]
    project_rows = (
        db.execute(
            select(ResearchProject)
            .where(ResearchProject.status.in_(ACTIVE_STATUSES), *_visible(ResearchProject.id, project_ids))
            .order_by(ResearchProject.deadline.asc().nulls_last())
            .limit(4)
        )
        .scalars()
        .all()
    )

    return DashboardResponse(
        generated_at=now,
        active_projects=active_projects,
        interviews_completed=interviews_completed,
        interviews_upcoming=len(upcoming),
        participants_contacted=participants_contacted,
        response_rate=response_rate,
        insights_awaiting_review=insights_awaiting_review,
        decisions_with_evidence=decisions_with_evidence,
        decisions_total=len(decision_rows),
        open_actions=len(open_actions),
        overdue_actions=len(overdue),
        learning=learning,
        timeline=timeline,
        segments=segment_points,
        decision_status=decision_status,
        action_status=action_status,
        recent_insights=[insight_summary(db, i) for i in recent_insights],
        upcoming_interviews=[interview_summary(db, i) for i in upcoming[:5]],
        recent_activity=[
            ActivityItem(
                id=a.id,
                entity_type=a.entity_type,
                entity_id=a.entity_id,
                entity_label=a.entity_label,
                summary=a.summary,
                verb=a.verb,
                actor=actor_refs.get(a.actor_id or ""),
                created_at=a.created_at,
                project_id=a.project_id,
            )
            for a in recent_activity_rows
        ],
        outstanding_actions=[action_out(db, a) for a in outstanding],
        projects=[project_summary(db, p) for p in project_rows],
        data_note=DATA_NOTE,
    )
