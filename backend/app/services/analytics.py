"""Learning-effectiveness analytics.

Every metric carries its basis so the reader can tell an observed measurement
from a calculated one, an illustrative value, or something that cannot be
stated until the business establishes a baseline. Nothing here attributes a
commercial outcome (repeat purchase, revenue) to this tool.
"""

from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    BusinessAction,
    Decision,
    DecisionInsight,
    Evidence,
    Insight,
    InsightEvidence,
    Interview,
    Participant,
    RecruitmentRecord,
    ResearchProject,
    ResearchQuestion,
)
from app.schemas.dashboard import AnalyticsMetric, AnalyticsResponse, MeasurementGap, SegmentPoint, StatusCount
from app.services.common import as_aware
from app.services.serializers import REUSE_WINDOW_DAYS, insight_is_reused

HONESTY_NOTE = (
    "Metrics marked 'calculated' come from records in this workspace. 'Pending baseline' means the business "
    "has not yet agreed how to measure it, so no value is shown. This tool cannot attribute changes in repeat "
    "purchase or revenue to research activity: those outcomes have multiple causes."
)


def _pct(numerator: int, denominator: int) -> str:
    if not denominator:
        return "No data yet"
    return f"{round(numerator / denominator * 100)}% ({numerator}/{denominator})"


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def _visible(column, project_ids: set[str] | None) -> list:
    return [] if project_ids is None else [column.in_(project_ids)]


def build_analytics(db: Session, project_ids: set[str] | None = None) -> AnalyticsResponse:
    insights = db.execute(select(Insight).where(*_visible(Insight.project_id, project_ids))).scalars().all()
    decisions = db.execute(select(Decision).where(*_visible(Decision.project_id, project_ids))).scalars().all()
    action_stmt = select(BusinessAction)
    if project_ids is not None:
        action_stmt = action_stmt.where(
            BusinessAction.decision_id.in_(select(Decision.id).where(Decision.project_id.in_(project_ids)))
        )
    actions = db.execute(action_stmt).scalars().all()

    reused = [i for i in insights if insight_is_reused(db, i)]
    with_evidence = [
        i
        for i in insights
        if db.execute(select(func.count(InsightEvidence.id)).where(InsightEvidence.insight_id == i.id)).scalar_one()
    ]
    evidenced_decisions = [d for d in decisions if d.evidence_links or d.insight_links]
    completed_actions = [a for a in actions if a.status == "completed"]
    on_time = [
        a
        for a in completed_actions
        if a.due_date and as_aware(a.completed_at) and as_aware(a.completed_at).date() <= a.due_date
    ]

    # Time from evidence capture to the decision that used it.
    gaps: list[float] = []
    for decision in evidenced_decisions:
        insight_ids = [link.insight_id for link in decision.insight_links]
        if not insight_ids:
            continue
        first_evidence = db.execute(
            select(func.min(Evidence.captured_at))
            .join(InsightEvidence, InsightEvidence.evidence_id == Evidence.id)
            .where(InsightEvidence.insight_id.in_(insight_ids))
        ).scalar()
        decision_at = as_aware(decision.created_at)
        evidence_at = as_aware(first_evidence)
        if decision_at and evidence_at and decision_at >= evidence_at:
            gaps.append((decision_at - evidence_at).total_seconds() / 86400)

    invitations = db.execute(
        select(func.count(RecruitmentRecord.id)).where(
            RecruitmentRecord.invited_at.is_not(None),
            *_visible(RecruitmentRecord.project_id, project_ids),
        )
    ).scalar_one()
    responses = db.execute(
        select(func.count(RecruitmentRecord.id)).where(
            RecruitmentRecord.responded_at.is_not(None),
            *_visible(RecruitmentRecord.project_id, project_ids),
        )
    ).scalar_one()
    interviews_completed = db.execute(
        select(func.count(Interview.id)).where(
            Interview.status == "completed", *_visible(Interview.project_id, project_ids)
        )
    ).scalar_one()
    evidence_total = db.execute(
        select(func.count(Evidence.id)).where(*_visible(Evidence.project_id, project_ids))
    ).scalar_one()
    unverified = db.execute(
        select(func.count(Evidence.id)).where(
            Evidence.provenance_status != "recorded", *_visible(Evidence.project_id, project_ids)
        )
    ).scalar_one()
    unresolved = db.execute(
        select(func.count(ResearchQuestion.id)).where(
            ResearchQuestion.is_resolved.is_(False), *_visible(ResearchQuestion.project_id, project_ids)
        )
    ).scalar_one()
    questions_total = db.execute(
        select(func.count(ResearchQuestion.id)).where(*_visible(ResearchQuestion.project_id, project_ids))
    ).scalar_one()

    median_gap = _median(gaps)

    metrics = [
        AnalyticsMetric(
            key="research_reuse_rate",
            label="Research reuse rate",
            display=_pct(len(reused), len(insights)),
            basis="calculated",
            definition=(
                "Share of insights linked to a later decision — either two or more decisions, or a decision "
                f"linked at least {REUSE_WINDOW_DAYS} days after the insight was written. It measures whether "
                "past learning is picked up again instead of being re-commissioned."
            ),
            target="Agree a target with the CEO once two quarters of data exist.",
        ),
        AnalyticsMetric(
            key="evidence_linked_decisions",
            label="Decisions backed by customer evidence",
            display=_pct(len(evidenced_decisions), len(decisions)),
            basis="calculated",
            definition=(
                "Decisions with at least one linked insight or evidence record divided by all recorded "
                "decisions. The remaining decisions are recorded as internal judgements on purpose."
            ),
        ),
        AnalyticsMetric(
            key="findings_with_evidence",
            label="Findings traceable to source evidence",
            display=_pct(len(with_evidence), len(insights)),
            basis="calculated",
            definition="Insights with at least one linked evidence record divided by all insights.",
        ),
        AnalyticsMetric(
            key="follow_up_completion",
            label="Follow-up action completion",
            display=_pct(len(completed_actions), len(actions)),
            basis="calculated",
            definition="Actions marked completed divided by all actions created.",
            note=f"{len(on_time)} of {len(completed_actions)} completed actions finished on or before their due date."
            if completed_actions
            else "No actions completed yet.",
        ),
        AnalyticsMetric(
            key="evidence_to_decision_days",
            label="Time from evidence capture to decision",
            display=f"{round(median_gap)} days (median)" if median_gap is not None else "No linked decisions yet",
            basis="calculated",
            definition=(
                "Median days between the earliest linked evidence capture and the decision record, for decisions "
                "that reference insights. A short cycle is not automatically good — it can mean a decision was "
                "made on too little evidence."
            ),
        ),
        AnalyticsMetric(
            key="invitation_response_rate",
            label="Recruitment response rate",
            display=_pct(responses, invitations),
            basis="calculated",
            definition=(
                "Participants who replied divided by participants actually invited through the controlled Ops "
                "process. Identified or selected participants are excluded from the denominator."
            ),
            note="Declines count as responses: a clear no is more useful than silence.",
        ),
        AnalyticsMetric(
            key="interviews_completed",
            label="Interviews completed",
            display=str(interviews_completed),
            basis="observed",
            definition="Completed interview records in the workspace.",
            note="Volume is a workload signal, not evidence of understanding.",
        ),
        AnalyticsMetric(
            key="evidence_captured",
            label="Evidence records captured",
            display=f"{evidence_total} ({unverified} without full provenance)" if evidence_total else "None yet",
            basis="observed",
            definition="Evidence records captured, with the count that is missing complete source context.",
        ),
        AnalyticsMetric(
            key="open_questions",
            label="Unresolved research questions",
            display=f"{unresolved} of {questions_total}" if questions_total else "None recorded",
            basis="observed",
            definition="Research questions not yet marked resolved, with a written resolution note.",
        ),
        AnalyticsMetric(
            key="coordination_time",
            label="Research coordination time",
            display="Not measured",
            basis="pending_baseline",
            definition=(
                "Time spent finding participants, arranging conversations and writing up notes. The product does "
                "not yet capture this, and estimating it would be guesswork."
            ),
            target="Record a one-off baseline workshop: two teams log coordination time for four weeks.",
        ),
        AnalyticsMetric(
            key="study_representativeness",
            label="How representative a study is",
            display="Not calculated",
            basis="pending_baseline",
            definition=(
                "Deliberately not shown. With the volumes this team can realistically run, a percentage would "
                "imply statistical confidence the sample does not have. Use the segment coverage view instead."
            ),
        ),
        AnalyticsMetric(
            key="commercial_impact",
            label="Impact on repeat purchase or revenue",
            display="Not attributable",
            basis="pending_baseline",
            definition=(
                "Repeat purchase has many causes. Attributing a change to research activity would require a "
                "controlled experiment per decision, which is out of scope for this prototype."
            ),
        ),
    ]

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
    segment_distribution = [
        SegmentPoint(
            segment=segment,
            participants=participant_counts.get(segment, 0),
            interviews=interview_counts.get(segment, 0),
            evidence=evidence_counts.get(segment, 0),
        )
        for segment in sorted(set(participant_counts) | set(interview_counts) | set(evidence_counts))
    ]

    decision_funnel = [
        StatusCount(status=status, count=count)
        for status, count in db.execute(
            select(Decision.status, func.count(Decision.id))
            .where(*_visible(Decision.project_id, project_ids))
            .group_by(Decision.status)
        ).all()
    ]
    action_completion_stmt = select(BusinessAction.status, func.count(BusinessAction.id))
    if project_ids is not None:
        action_completion_stmt = action_completion_stmt.where(
            BusinessAction.decision_id.in_(select(Decision.id).where(Decision.project_id.in_(project_ids)))
        )
    action_completion = [
        StatusCount(status=status, count=count)
        for status, count in db.execute(
            action_completion_stmt.group_by(BusinessAction.status)
        ).all()
    ]

    unresolved_rows = db.execute(
        select(ResearchQuestion, ResearchProject)
        .join(ResearchProject, ResearchProject.id == ResearchQuestion.project_id)
        .where(
            ResearchQuestion.is_resolved.is_(False),
            *_visible(ResearchQuestion.project_id, project_ids),
        )
    ).all()

    reuse_detail = []
    for insight in insights:
        link_rows = db.execute(
            select(DecisionInsight, Decision)
            .join(Decision, Decision.id == DecisionInsight.decision_id)
            .where(DecisionInsight.insight_id == insight.id)
        ).all()
        reuse_detail.append(
            {
                "insight_id": insight.id,
                "code": insight.code,
                "title": insight.title,
                "decisions": len(link_rows),
                "reused": insight_is_reused(db, insight),
                "decision_titles": [d.title for _, d in link_rows],
            }
        )

    measurement_gaps = [
        MeasurementGap(
            key="coordination_baseline",
            label="Coordination effort baseline",
            why="Without a before-and-after measure, 'less coordination' is an opinion.",
            how_to_collect="Ask two teams to log hours spent arranging and writing up research for four weeks.",
        ),
        MeasurementGap(
            key="decision_outcomes",
            label="Whether decisions produced the intended effect",
            why="The product records that a decision was made, not whether it worked.",
            how_to_collect="Add a review date to each decision and record the observed outcome in a follow-up entry.",
        ),
        MeasurementGap(
            key="reuse_by_team",
            label="Reuse by team, not just in total",
            why="A single reuse rate hides whether one team benefits while others ignore the library.",
            how_to_collect="Attribute each decision link to the business function and report reuse per function.",
        ),
        MeasurementGap(
            key="customer_base_mix",
            label="Customer base segment mix",
            why="Coverage warnings compare a study against other studies, not against the real customer base.",
            how_to_collect="Ask Operations for an aggregate, contact-free segment mix from the commerce system.",
        ),
        MeasurementGap(
            key="quality_over_volume",
            label="Conversation quality",
            why="Counting interviews rewards activity. Depth and neutrality are not measured at all.",
            how_to_collect="Sample review by a peer using the guide-quality checklist, recorded as a review outcome.",
        ),
        MeasurementGap(
            key="adoption",
            label="Sustainable usage",
            why="A tool used once and abandoned looks successful in a launch review.",
            how_to_collect="Track weekly active teams and the share of decisions with a linked customer source.",
        ),
    ]

    return AnalyticsResponse(
        generated_at=datetime.now(timezone.utc),
        metrics=metrics,
        segment_distribution=segment_distribution,
        decision_funnel=decision_funnel,
        action_completion=action_completion,
        unresolved_questions=[
            {
                "id": q.id,
                "project_id": p.id,
                "project_name": p.name,
                "text": q.text,
                "is_resolved": q.is_resolved,
                "resolution_note": q.resolution_note,
            }
            for q, p in unresolved_rows
        ],
        reuse_detail=sorted(reuse_detail, key=lambda r: (not r["reused"], r["code"])),
        measurement_gaps=measurement_gaps,
        honesty_note=HONESTY_NOTE,
    )
