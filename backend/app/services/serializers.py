"""Maps ORM objects to response models, adding derived counts and warnings.

The warnings are product surface, not decoration: the UI uses them to tell a
user when a conclusion is not yet supported by evidence.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    BusinessAction,
    Decision,
    DecisionEvidence,
    DecisionInsight,
    Evidence,
    Insight,
    InsightEvidence,
    Interview,
    Participant,
    RecruitmentRecord,
    ResearchProject,
    User,
)
from app.schemas.common import Ref
from app.schemas.decision import ActionOut, DecisionSummary, DecisionDetail, ActionRef, DecisionHistoryItem
from app.schemas.evidence import EvidenceLinkOut, EvidenceOut, SOURCE_UNAVAILABLE
from app.schemas.insight import InsightSummary, InsightDetail, DecisionRef
from app.schemas.interview import InterviewSummary, InterviewDetail, ConsentRecordOut, GuideQuestionOut
from app.schemas.participant import ParticipantOut, RecruitmentOut, RecruitmentEventOut
from app.schemas.project import ProjectCounts, ProjectSummary, ProjectDetail

REUSE_WINDOW_DAYS = 14


def _ref(id_: str | None, label: str | None, sublabel: str | None = None) -> Ref | None:
    if not id_ or not label:
        return None
    return Ref(id=id_, label=label, sublabel=sublabel)


def user_map(db: Session, ids: set[str | None]) -> dict[str, Ref]:
    clean = {i for i in ids if i}
    if not clean:
        return {}
    users = db.execute(select(User).where(User.id.in_(clean))).scalars().all()
    return {u.id: Ref(id=u.id, label=u.name, sublabel=u.job_title or u.role) for u in users}


def project_counts_map(db: Session, project_ids: list[str]) -> dict[str, ProjectCounts]:
    counts = {pid: ProjectCounts() for pid in project_ids}
    if not project_ids:
        return counts

    def apply(model, key: str, extra_where=None) -> None:
        stmt = select(model.project_id, func.count(model.id)).where(model.project_id.in_(project_ids))
        if extra_where is not None:
            stmt = stmt.where(extra_where)
        for pid, value in db.execute(stmt.group_by(model.project_id)).all():
            setattr(counts[pid], key, value)

    apply(RecruitmentRecord, "participants")
    apply(Interview, "interviews")
    apply(Interview, "interviews_completed", Interview.status == "completed")
    apply(Evidence, "evidence")
    apply(Insight, "insights")
    apply(Decision, "decisions")

    # Actions hang off decisions, so they are counted through that join.
    action_rows = db.execute(
        select(Decision.project_id, func.count(BusinessAction.id))
        .join(BusinessAction, BusinessAction.decision_id == Decision.id)
        .where(Decision.project_id.in_(project_ids), BusinessAction.status != "completed")
        .group_by(Decision.project_id)
    ).all()
    for pid, value in action_rows:
        counts[pid].open_actions = value
    return counts


def project_summary(db: Session, project: ResearchProject, users: dict[str, Ref] | None = None) -> ProjectSummary:
    users = users or user_map(db, {project.owner_id})
    counts = project_counts_map(db, [project.id])[project.id]
    unresolved = len([q for q in project.questions if not q.is_resolved])

    coverage = segment_coverage(db, project.id)
    targets = set(project.target_segments or [])
    segment_gap = bool(targets) and any(coverage.get(t, 0) == 0 for t in targets)

    return ProjectSummary(
        **project_out_dict(project),
        owner=users.get(project.owner_id or ""),
        counts=counts,
        unresolved_questions=unresolved,
        segment_gap=segment_gap,
    )


def project_out_dict(project: ResearchProject) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "objective": project.objective,
        "description": project.description,
        "status": project.status,
        "priority": project.priority,
        "methodology": project.methodology,
        "owner_id": project.owner_id,
        "business_functions": project.business_functions or [],
        "target_segments": project.target_segments or [],
        "start_date": project.start_date,
        "deadline": project.deadline,
        "archived_at": project.archived_at,
        "completed_at": project.completed_at,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def project_detail(db: Session, project: ResearchProject) -> ProjectDetail:
    summary = project_summary(db, project)
    return ProjectDetail(
        **summary.model_dump(),
        questions=[q for q in project.questions],
    )


def segment_coverage(db: Session, project_id: str, stage_filter: list[str] | None = None) -> dict[str, int]:
    stmt = (
        select(Participant.segment, func.count(RecruitmentRecord.id))
        .join(RecruitmentRecord, RecruitmentRecord.participant_id == Participant.id)
        .where(RecruitmentRecord.project_id == project_id)
        .group_by(Participant.segment)
    )
    if stage_filter:
        stmt = stmt.where(RecruitmentRecord.stage.in_(stage_filter))
    return {segment: count for segment, count in db.execute(stmt).all()}


def participant_out(db: Session, participant: Participant) -> ParticipantOut:
    return ParticipantOut.model_validate(participant)


def recruitment_out(
    db: Session,
    record: RecruitmentRecord,
    users: dict[str, Ref] | None = None,
    include_events: bool = False,
) -> RecruitmentOut:
    users = users or user_map(db, {record.updated_by_id})
    participant = db.get(Participant, record.participant_id)
    project = db.get(ResearchProject, record.project_id)
    now = datetime.now(record.updated_at.tzinfo) if record.updated_at and record.updated_at.tzinfo else datetime.now()
    days = max((now - record.updated_at).days, 0) if record.updated_at else None
    return RecruitmentOut(
        id=record.id,
        project_id=record.project_id,
        participant_id=record.participant_id,
        stage=record.stage,
        next_action=record.next_action,
        notes=record.notes,
        invited_at=record.invited_at,
        responded_at=record.responded_at,
        scheduled_at=record.scheduled_at,
        updated_at=record.updated_at,
        participant=participant_out(db, participant) if participant else None,
        project=_ref(project.id, project.name) if project else None,
        updated_by=users.get(record.updated_by_id or ""),
        days_in_stage=days,
        events=[
            RecruitmentEventOut(
                id=e.id,
                from_stage=e.from_stage,
                to_stage=e.to_stage,
                note=e.note,
                created_at=e.created_at,
                actor=users.get(e.actor_id or "") if e.actor_id else None,
            )
            for e in (record.events if include_events else [])
        ],
    )


def interview_summary(db: Session, interview: Interview, users: dict[str, Ref] | None = None) -> InterviewSummary:
    users = users or user_map(db, {interview.interviewer_id})
    participant = db.get(Participant, interview.participant_id)
    project = db.get(ResearchProject, interview.project_id)
    counts = db.execute(
        select(Evidence.review_status, func.count(Evidence.id))
        .where(Evidence.interview_id == interview.id)
        .group_by(Evidence.review_status)
    ).all()
    by_status = dict(counts)
    return InterviewSummary(
        **_interview_dict(interview),
        participant=participant_out(db, participant) if participant else None,
        project=_ref(project.id, project.name) if project else None,
        interviewer=users.get(interview.interviewer_id or ""),
        evidence_count=sum(by_status.values()),
        evidence_pending_review=by_status.get("unreviewed", 0),
    )


def _interview_dict(interview: Interview) -> dict:
    return {
        "id": interview.id,
        "code": interview.code,
        "project_id": interview.project_id,
        "participant_id": interview.participant_id,
        "recruitment_id": interview.recruitment_id,
        "title": interview.title,
        "objective": interview.objective,
        "scheduled_at": interview.scheduled_at,
        "duration_minutes": interview.duration_minutes,
        "interviewer_id": interview.interviewer_id,
        "status": interview.status,
        "channel": interview.channel,
        "consent_status": interview.consent_status,
        "recording_enabled": interview.recording_enabled,
        "notes": interview.notes,
        "summary": interview.summary,
        "follow_up_questions": interview.follow_up_questions or [],
        "completed_at": interview.completed_at,
        "created_at": interview.created_at,
        "updated_at": interview.updated_at,
    }


def interview_detail(db: Session, interview: Interview) -> InterviewDetail:
    summary = interview_summary(db, interview)
    users = user_map(db, {c.recorded_by_id for c in interview.consent_records})
    evidence = (
        db.execute(
            select(Evidence).where(Evidence.interview_id == interview.id).order_by(Evidence.captured_at.asc())
        )
        .scalars()
        .all()
    )
    return InterviewDetail(
        **summary.model_dump(),
        guide=[
            GuideQuestionOut(
                id=g.id, text=g.text, purpose=g.purpose, order_index=g.order_index, is_leading=g.is_leading
            )
            for g in interview.guide
        ],
        consent_records=[
            ConsentRecordOut(
                id=c.id,
                consent_type=c.consent_type,
                status=c.status,
                note=c.note,
                recorded_at=c.recorded_at,
                recorded_by=users.get(c.recorded_by_id or ""),
            )
            for c in sorted(interview.consent_records, key=lambda c: c.recorded_at)
        ],
        evidence=[evidence_out(db, e, include_links=True) for e in evidence],
    )


def evidence_out(db: Session, ev: Evidence, include_links: bool = True) -> EvidenceOut:
    participant = db.get(Participant, ev.participant_id) if ev.participant_id else None
    interview = db.get(Interview, ev.interview_id) if ev.interview_id else None
    project = db.get(ResearchProject, ev.project_id)
    users = user_map(db, {ev.captured_by_id})

    links: list[EvidenceLinkOut] = []
    if include_links:
        rows = db.execute(
            select(InsightEvidence, Insight)
            .join(Insight, Insight.id == InsightEvidence.insight_id)
            .where(InsightEvidence.evidence_id == ev.id)
        ).all()
        links = [
            EvidenceLinkOut(
                insight_id=insight.id, insight_code=insight.code, insight_title=insight.title, role=link.role
            )
            for link, insight in rows
        ]

    verified = ev.provenance_status == "recorded" and bool((ev.provenance or "").strip())
    warning = None
    if not verified:
        warning = SOURCE_UNAVAILABLE

    return EvidenceOut(
        id=ev.id,
        code=ev.code,
        interview_id=ev.interview_id,
        project_id=ev.project_id,
        participant_id=ev.participant_id,
        evidence_type=ev.evidence_type,
        content=ev.content,
        interpretation=ev.interpretation,
        customer_context=ev.customer_context,
        segment=ev.segment,
        provenance=ev.provenance,
        provenance_status=ev.provenance_status,
        confidence=ev.confidence,
        review_status=ev.review_status,
        captured_at=ev.captured_at,
        captured_by_id=ev.captured_by_id,
        is_verified_source=verified,
        provenance_warning=warning,
        participant=_ref(participant.id, participant.display_name, participant.code) if participant else None,
        captured_by=users.get(ev.captured_by_id or ""),
        interview=_ref(interview.id, interview.code, interview.title) if interview else None,
        project=_ref(project.id, project.name) if project else None,
        insight_links=links,
    )


def insight_is_reused(db: Session, insight: Insight) -> bool:
    rows = db.execute(
        select(DecisionInsight.created_at).where(DecisionInsight.insight_id == insight.id)
    ).scalars().all()
    if len(rows) >= 2:
        return True
    if not rows:
        return False
    created = insight.created_at
    for link_at in rows:
        if created and link_at and (link_at - created) >= timedelta(days=REUSE_WINDOW_DAYS):
            return True
    return False


def insight_summary(db: Session, insight: Insight, users: dict[str, Ref] | None = None) -> InsightSummary:
    users = users or user_map(db, {insight.owner_id})
    project = db.get(ResearchProject, insight.project_id) if insight.project_id else None
    roles = dict(
        db.execute(
            select(InsightEvidence.role, func.count(InsightEvidence.id))
            .where(InsightEvidence.insight_id == insight.id)
            .group_by(InsightEvidence.role)
        ).all()
    )
    decision_count = db.execute(
        select(func.count(DecisionInsight.id)).where(DecisionInsight.insight_id == insight.id)
    ).scalar_one()
    supporting = roles.get("supporting", 0)
    contradictory = roles.get("contradictory", 0)
    return InsightSummary(
        **_insight_dict(insight),
        owner=users.get(insight.owner_id or ""),
        project=_ref(project.id, project.name) if project else None,
        supporting_count=supporting,
        contradictory_count=contradictory,
        evidence_count=supporting + contradictory,
        decision_count=decision_count,
        reuse_flag=insight_is_reused(db, insight),
    )


def _insight_dict(insight: Insight) -> dict:
    return {
        "id": insight.id,
        "code": insight.code,
        "title": insight.title,
        "summary": insight.summary,
        "interpretation": insight.interpretation,
        "research_question": insight.research_question,
        "project_id": insight.project_id,
        "status": insight.status,
        "confidence": insight.confidence,
        "owner_id": insight.owner_id,
        "limitations": insight.limitations,
        "segments": insight.segments or [],
        "validated_at": insight.validated_at,
        "created_at": insight.created_at,
        "updated_at": insight.updated_at,
    }


def insight_detail(db: Session, insight: Insight) -> InsightDetail:
    summary = insight_summary(db, insight)
    evidence = (
        db.execute(
            select(Evidence)
            .join(InsightEvidence, InsightEvidence.evidence_id == Evidence.id)
            .where(InsightEvidence.insight_id == insight.id)
            .order_by(Evidence.captured_at.asc())
        )
        .scalars()
        .unique()
        .all()
    )
    decisions = (
        db.execute(
            select(Decision)
            .join(DecisionInsight, DecisionInsight.decision_id == Decision.id)
            .where(DecisionInsight.insight_id == insight.id)
            .order_by(Decision.created_at.desc())
        )
        .scalars()
        .unique()
        .all()
    )
    warning = None
    if summary.evidence_count == 0:
        warning = "No evidence is linked yet. Treat this as a hypothesis, not a finding."
    elif summary.evidence_count < 3:
        warning = (
            f"Only {summary.evidence_count} evidence item(s) support this. "
            "Small numbers of conversations cannot establish how common a view is."
        )
    elif summary.contradictory_count:
        warning = (
            f"{summary.contradictory_count} contradictory item(s) are attached. "
            "Keep them visible when this insight is used in a decision."
        )

    return InsightDetail(
        **summary.model_dump(),
        evidence=[evidence_out(db, e) for e in evidence],
        decisions=[
            DecisionRef(
                id=d.id,
                code=d.code,
                title=d.title,
                status=d.status,
                business_function=d.business_function,
                decision_date=datetime.combine(d.decision_date, datetime.min.time()) if d.decision_date else None,
            )
            for d in decisions
        ],
        evidence_warning=warning,
    )


def action_out(db: Session, action: BusinessAction, users: dict[str, Ref] | None = None) -> ActionOut:
    users = users or user_map(db, {action.owner_id})
    decision = db.get(Decision, action.decision_id) if action.decision_id else None
    insight = db.get(Insight, action.insight_id) if action.insight_id else None
    today = date.today()
    days_until = (action.due_date - today).days if action.due_date else None
    return ActionOut(
        id=action.id,
        code=action.code,
        title=action.title,
        description=action.description,
        owner_id=action.owner_id,
        due_date=action.due_date,
        priority=action.priority,
        status=action.status,
        decision_id=action.decision_id,
        insight_id=action.insight_id,
        completed_at=action.completed_at,
        created_at=action.created_at,
        updated_at=action.updated_at,
        owner=users.get(action.owner_id or ""),
        decision=_ref(decision.id, decision.title, decision.code) if decision else None,
        insight=_ref(insight.id, insight.title, insight.code) if insight else None,
        is_overdue=bool(days_until is not None and days_until < 0 and action.status != "completed"),
        days_until_due=days_until,
    )


def decision_summary(db: Session, decision: Decision, users: dict[str, Ref] | None = None) -> DecisionSummary:
    users = users or user_map(db, {decision.owner_id})
    project = db.get(ResearchProject, decision.project_id) if decision.project_id else None
    insight_count = db.execute(
        select(func.count(DecisionInsight.id)).where(DecisionInsight.decision_id == decision.id)
    ).scalar_one()
    evidence_total = db.execute(
        select(func.count(DecisionEvidence.id)).where(DecisionEvidence.decision_id == decision.id)
    ).scalar_one()
    contradicting = db.execute(
        select(func.count(DecisionEvidence.id)).where(
            DecisionEvidence.decision_id == decision.id, DecisionEvidence.role == "contradictory"
        )
    ).scalar_one()
    action_rows = db.execute(select(BusinessAction).where(BusinessAction.decision_id == decision.id)).scalars().all()
    open_actions = len([a for a in action_rows if a.status != "completed"])

    warning = None
    if insight_count == 0 and evidence_total == 0:
        warning = (
            "Not linked to any customer evidence. Record this as an internal decision, "
            "not an evidence-backed one."
        )
    elif contradicting:
        warning = (
            f"{contradicting} contradictory item(s) are linked. The decision should explain "
            "why the team proceeded anyway."
        )
    elif insight_count + evidence_total < 2:
        warning = "Evidence base is thin. One item is an anecdote, not a pattern."

    return DecisionSummary(
        **_decision_dict(decision),
        owner=users.get(decision.owner_id or ""),
        project=_ref(project.id, project.name) if project else None,
        insight_count=insight_count,
        evidence_count=evidence_total,
        action_count=len(action_rows),
        open_action_count=open_actions,
        evidence_warning=warning,
        contradicting_count=contradicting,
    )


def _decision_dict(decision: Decision) -> dict:
    return {
        "id": decision.id,
        "code": decision.code,
        "title": decision.title,
        "business_function": decision.business_function,
        "problem_statement": decision.problem_statement,
        "description": decision.description,
        "rationale": decision.rationale,
        "limitations": decision.limitations,
        "project_id": decision.project_id,
        "owner_id": decision.owner_id,
        "decision_date": decision.decision_date,
        "status": decision.status,
        "evidence_sufficient": decision.evidence_sufficient,
        "created_at": decision.created_at,
        "updated_at": decision.updated_at,
    }


def decision_detail(db: Session, decision: Decision) -> DecisionDetail:
    from app.models import ActivityLog

    summary = decision_summary(db, decision)
    evidence = (
        db.execute(
            select(Evidence)
            .join(DecisionEvidence, DecisionEvidence.evidence_id == Evidence.id)
            .where(DecisionEvidence.decision_id == decision.id)
        )
        .scalars()
        .unique()
        .all()
    )
    insights = (
        db.execute(
            select(Insight)
            .join(DecisionInsight, DecisionInsight.insight_id == Insight.id)
            .where(DecisionInsight.decision_id == decision.id)
        )
        .scalars()
        .unique()
        .all()
    )
    actions = db.execute(
        select(BusinessAction).where(BusinessAction.decision_id == decision.id).order_by(BusinessAction.due_date.asc())
    ).scalars().all()
    users = user_map(db, {a.owner_id for a in actions})
    history = db.execute(
        select(ActivityLog)
        .where(ActivityLog.entity_id == decision.id)
        .order_by(ActivityLog.created_at.desc())
        .limit(20)
    ).scalars().all()
    actor_names = user_map(db, {h.actor_id for h in history})

    return DecisionDetail(
        **summary.model_dump(),
        insights=[insight_summary(db, i) for i in insights],
        evidence=[evidence_out(db, e) for e in evidence],
        actions=[
            ActionRef(
                id=a.id,
                code=a.code,
                title=a.title,
                status=a.status,
                owner=users.get(a.owner_id or ""),
                due_date=a.due_date,
                is_overdue=bool(a.due_date and a.due_date < date.today() and a.status != "completed"),
            )
            for a in actions
        ],
        history=[
            DecisionHistoryItem(
                at=h.created_at,
                summary=h.summary,
                actor=(actor_names.get(h.actor_id or "").label if h.actor_id and h.actor_id in actor_names else None),
                verb=h.verb,
            )
            for h in history
        ],
    )
