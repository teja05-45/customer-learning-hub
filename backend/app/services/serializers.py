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
    FeedbackRecord,
    Insight,
    InsightEvidence,
    Interview,
    Participant,
    RecruitmentRecord,
    ResearchProject,
    User,
)
from app.models.enums import feedback_depth
from app.schemas.common import Ref
from app.schemas.decision import ActionOut, DecisionSummary, DecisionDetail, ActionRef, DecisionHistoryItem
from app.schemas.evidence import EvidenceLinkOut, EvidenceOut, SOURCE_UNAVAILABLE
from app.schemas.insight import InsightSummary, InsightDetail, DecisionRef
from app.schemas.traceability import (
    DecisionTraceability,
    DecisionTraceabilityInsight,
    EvidenceGroupOut,
    EvidenceInsightLinkOut,
    EvidenceInsightsResponse,
    InsightEvidenceLinkOut,
    InsightEvidenceResponse,
    InsightTraceability,
    TraceabilityActionOut,
    TraceabilityDecisionOut,
    TraceabilityQuality,
)
from app.schemas.interview import InterviewSummary, InterviewDetail, ConsentRecordOut, GuideQuestionOut
from app.schemas.participant import ParticipantOut, RecruitmentOut, RecruitmentEventOut
from app.schemas.project import ProjectCounts, ProjectSummary, ProjectDetail

REUSE_WINDOW_DAYS = 14

# Interviews store a free-text channel (for example "Video call (simulated)").
# Mapping it to a collection method is a derivation, not a stored fact, so an
# unrecognised channel is reported as unknown rather than guessed.
CHANNEL_METHODS: tuple[tuple[str, str], ...] = (
    ("video", "video_interview"),
    ("phone", "phone_interview"),
    ("in person", "in_person_interview"),
    ("in-person", "in_person_interview"),
    ("written", "written_feedback"),
)


def interview_collection_method(channel: str | None) -> str | None:
    value = (channel or "").lower()
    for needle, method in CHANNEL_METHODS:
        if needle in value:
            return method
    return None


def evidence_provenance(db: Session, ev: Evidence) -> dict:
    """Where this item came from, without inventing what is not recorded.

    Feedback-derived evidence uses the snapshot written at capture time so a
    later correction to the source record cannot silently change how the
    customer's words are presented. Interview evidence is derived from the live
    interview row.
    """
    if ev.source_type:
        method = ev.collection_method
        return {
            "source_type": ev.source_type,
            "collection_method": method,
            "research_depth": ev.research_depth or (feedback_depth(method)[0] if method else None),
            "source_reference": ev.source_reference or "",
            "verification_state": ev.verification_state,
            "collected_at": ev.collected_at,
        }

    if ev.interview_id:
        interview = db.get(Interview, ev.interview_id)
        method = interview_collection_method(interview.channel) if interview else None
        return {
            "source_type": "interview",
            "collection_method": method,
            "research_depth": feedback_depth(method)[0] if method else None,
            "source_reference": interview.code if interview else "",
            "verification_state": "verified" if ev.provenance.strip() else "unverified",
            "collected_at": (
                (interview.completed_at or interview.scheduled_at) if interview else None
            ),
        }

    return {
        "source_type": None,
        "collection_method": None,
        "research_depth": None,
        "source_reference": "",
        "verification_state": ev.provenance_status,
        "collected_at": None,
    }


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
    events = record.events if include_events else []
    actor_ids = {record.updated_by_id} | {event.actor_id for event in events}
    users = users or user_map(db, actor_ids)
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
            for e in events
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
    feedback = db.get(FeedbackRecord, ev.feedback_record_id) if ev.feedback_record_id else None
    project = db.get(ResearchProject, ev.project_id)
    users = user_map(db, {ev.captured_by_id})
    provenance = evidence_provenance(db, ev)

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
        feedback_record_id=ev.feedback_record_id,
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
        source_type=provenance["source_type"],
        collection_method=provenance["collection_method"],
        research_depth=provenance["research_depth"],
        source_reference=provenance["source_reference"],
        verification_state=provenance["verification_state"],
        collected_at=provenance["collected_at"],
        is_attributed=bool(ev.participant_id),
        is_verified_source=verified,
        provenance_warning=warning,
        participant=_ref(participant.id, participant.display_name, participant.code) if participant else None,
        captured_by=users.get(ev.captured_by_id or ""),
        interview=_ref(interview.id, interview.code, interview.title) if interview else None,
        feedback_record=_ref(feedback.id, feedback.code, feedback.source_type) if feedback else None,
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
    contextual = roles.get("contextual", 0)
    return InsightSummary(
        **_insight_dict(insight),
        owner=users.get(insight.owner_id or ""),
        project=_ref(project.id, project.name) if project else None,
        supporting_count=supporting,
        contradictory_count=contradictory,
        contextual_count=contextual,
        evidence_count=supporting + contradictory + contextual,
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
    elif summary.supporting_count == 0 and summary.contextual_count:
        warning = (
            "Only contextual evidence is linked. Context explains the setting; it does not support the "
            "finding."
        )
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


# ------------------------------------------------------- evidence traceability
CLASSIFICATIONS = ("supporting", "contradictory", "contextual")

CHAIN_NOTE = (
    "Feedback source → Evidence → Insight → Decision → Action. Moving backwards along this chain "
    "should always land on the customer's own words."
)


def _insight_links(db: Session, insight_id: str) -> list[InsightEvidence]:
    return db.execute(
        select(InsightEvidence)
        .where(InsightEvidence.insight_id == insight_id)
        .order_by(InsightEvidence.created_at.asc())
    ).scalars().all()


def insight_evidence_link_out(
    db: Session,
    link: InsightEvidence,
    users: dict[str, Ref] | None = None,
    include_evidence_links: bool = False,
) -> InsightEvidenceLinkOut:
    users = users or user_map(db, {link.created_by_id})
    return InsightEvidenceLinkOut(
        relationship_id=link.id,
        classification=link.role,
        # Rows created before the rationale column existed only have the short
        # note. Surfacing it keeps old judgements visible instead of blank.
        rationale=link.rationale or link.note or "",
        confidence=link.confidence,
        tags=list(link.tags or []),
        note=link.note,
        created_by=users.get(link.created_by_id or ""),
        created_at=link.created_at,
        updated_at=link.updated_at,
        evidence=evidence_out(db, link.evidence, include_links=include_evidence_links),
    )


def insight_evidence_response(db: Session, insight: Insight) -> InsightEvidenceResponse:
    links = _insight_links(db, insight.id)
    users = user_map(db, {link.created_by_id for link in links})
    grouped: dict[str, list[InsightEvidenceLinkOut]] = {role: [] for role in CLASSIFICATIONS}
    for link in links:
        if link.role in grouped:
            grouped[link.role].append(insight_evidence_link_out(db, link, users))

    return InsightEvidenceResponse(
        insight_id=insight.id,
        insight_code=insight.code,
        insight_title=insight.title,
        project_id=insight.project_id,
        supporting=EvidenceGroupOut(items=grouped["supporting"], count=len(grouped["supporting"])),
        contradictory=EvidenceGroupOut(
            items=grouped["contradictory"], count=len(grouped["contradictory"])
        ),
        contextual=EvidenceGroupOut(items=grouped["contextual"], count=len(grouped["contextual"])),
        total=len(links),
    )


def traceability_quality(db: Session, links: list[InsightEvidence]) -> TraceabilityQuality:
    roles = {role: 0 for role in CLASSIFICATIONS}
    for link in links:
        if link.role in roles:
            roles[link.role] += 1
    verified = sum(1 for link in links if link.evidence.is_verified_source)
    source_types = {
        (link.evidence.source_type or ("interview" if link.evidence.interview_id else "unknown"))
        for link in links
    }
    unattributed = sum(1 for link in links if not link.evidence.participant_id)
    return TraceabilityQuality(
        total=len(links),
        supporting=roles["supporting"],
        contradictory=roles["contradictory"],
        contextual=roles["contextual"],
        verified=verified,
        unverified=len(links) - verified,
        distinct_source_types=len(source_types) if links else 0,
        unattributed=unattributed,
        unsubstantiated=len(links) == 0,
        has_conflict=roles["contradictory"] > 0,
    )


def insight_traceability(db: Session, insight: Insight) -> InsightTraceability:
    links = _insight_links(db, insight.id)
    quality = traceability_quality(db, links)
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

    action_rows = []
    for decision in decisions:
        action_rows.append(
            (
                decision,
                db.execute(
                    select(BusinessAction)
                    .where(BusinessAction.decision_id == decision.id)
                    .order_by(BusinessAction.due_date.asc())
                )
                .scalars()
                .all(),
            )
        )
    owners = user_map(db, {a.owner_id for _d, actions in action_rows for a in actions})

    warnings: list[str] = []
    if quality.unsubstantiated:
        warnings.append(
            "This insight has no linked evidence. It is unsubstantiated: a hypothesis, not a finding."
        )
    if quality.supporting == 0 and quality.total > 0:
        warnings.append(
            "No evidence is classified as supporting. Context and contradictions cannot carry the finding."
        )
    if quality.contradictory:
        warnings.append(
            f"{quality.contradictory} item(s) contradict this insight. They are kept visible rather than "
            "filtered out."
        )
    if quality.unverified:
        warnings.append(
            f"{quality.unverified} linked item(s) have no recorded source. They cannot be treated as verified "
            "evidence."
        )
    if quality.unattributed:
        warnings.append(
            f"{quality.unattributed} item(s) are unattributed, so they cannot be tied to a participant."
        )

    return InsightTraceability(
        insight=insight_summary(db, insight),
        evidence=insight_evidence_response(db, insight),
        quality=quality,
        decisions=[
            TraceabilityDecisionOut(
                id=decision.id,
                code=decision.code,
                title=decision.title,
                status=decision.status,
                business_function=decision.business_function,
                rationale=decision.rationale,
                decision_date=(
                    datetime.combine(decision.decision_date, datetime.min.time())
                    if decision.decision_date
                    else None
                ),
                evidence_sufficient=decision.evidence_sufficient,
                actions=[
                    TraceabilityActionOut(
                        id=action.id,
                        code=action.code,
                        title=action.title,
                        status=action.status,
                        owner=owners.get(action.owner_id or ""),
                        due_date=action.due_date,
                    )
                    for action in actions
                ],
            )
            for decision, actions in action_rows
        ],
        warnings=warnings,
        chain_note=CHAIN_NOTE,
    )


def evidence_insights(db: Session, evidence: Evidence) -> EvidenceInsightsResponse:
    rows = db.execute(
        select(InsightEvidence, Insight)
        .join(Insight, Insight.id == InsightEvidence.insight_id)
        .where(InsightEvidence.evidence_id == evidence.id)
        .order_by(InsightEvidence.created_at.asc())
    ).all()
    grouped: dict[str, list[EvidenceInsightLinkOut]] = {role: [] for role in CLASSIFICATIONS}
    for link, insight in rows:
        if link.role not in grouped:
            continue
        grouped[link.role].append(
            EvidenceInsightLinkOut(
                relationship_id=link.id,
                classification=link.role,
                rationale=link.rationale or link.note or "",
                confidence=link.confidence,
                tags=list(link.tags or []),
                created_by=user_map(db, {link.created_by_id}).get(link.created_by_id or ""),
                created_at=link.created_at,
                updated_at=link.updated_at,
                insight=insight_summary(db, insight),
            )
        )

    return EvidenceInsightsResponse(
        evidence_id=evidence.id,
        evidence_code=evidence.code,
        supporting=grouped["supporting"],
        contradictory=grouped["contradictory"],
        contextual=grouped["contextual"],
        total=len(rows),
        unattributed=not bool(evidence.participant_id),
        statement_note=(
            "The customer statement below is the original captured text. It is never rewritten by a "
            "classification change."
        ),
    )


def decision_traceability(db: Session, decision: Decision) -> DecisionTraceability:
    insights = (
        db.execute(
            select(Insight)
            .join(DecisionInsight, DecisionInsight.insight_id == Insight.id)
            .where(DecisionInsight.decision_id == decision.id)
            .order_by(Insight.created_at.asc())
        )
        .scalars()
        .unique()
        .all()
    )
    direct = (
        db.execute(
            select(Evidence)
            .join(DecisionEvidence, DecisionEvidence.evidence_id == Evidence.id)
            .where(DecisionEvidence.decision_id == decision.id)
        )
        .scalars()
        .unique()
        .all()
    )

    contradicting: dict[str, Evidence] = {}
    insight_rows: list[DecisionTraceabilityInsight] = []
    for insight in insights:
        links = _insight_links(db, insight.id)
        for link in links:
            if link.role == "contradictory":
                contradicting[link.evidence.id] = link.evidence
        insight_rows.append(
            DecisionTraceabilityInsight(
                insight=insight_summary(db, insight),
                support_count=sum(1 for link in links if link.role == "supporting"),
                contradiction_count=sum(1 for link in links if link.role == "contradictory"),
                context_count=sum(1 for link in links if link.role == "contextual"),
                evidence=[evidence_out(db, link.evidence) for link in links],
            )
        )

    actions = db.execute(
        select(BusinessAction)
        .where(BusinessAction.decision_id == decision.id)
        .order_by(BusinessAction.due_date.asc())
    ).scalars().all()
    owners = user_map(db, {a.owner_id for a in actions})

    gaps: list[str] = []
    if not insights and not direct:
        gaps.append(
            "No insight or evidence is linked. This is an internal judgement, not an evidence-backed "
            "decision."
        )
    for insight in insights:
        if not _insight_links(db, insight.id):
            gaps.append(f"{insight.code} is linked but has no evidence of its own.")
    if contradicting:
        gaps.append(
            f"{len(contradicting)} contradictory item(s) were known. The rationale should say why the "
            "team proceeded anyway."
        )
    if not actions:
        gaps.append("No follow-up action is recorded, so this decision has no owner or due date.")

    return DecisionTraceability(
        decision_id=decision.id,
        decision_code=decision.code,
        decision_title=decision.title,
        insights=insight_rows,
        direct_evidence=[evidence_out(db, ev) for ev in direct],
        actions=[
            TraceabilityActionOut(
                id=action.id,
                code=action.code,
                title=action.title,
                status=action.status,
                owner=owners.get(action.owner_id or ""),
                due_date=action.due_date,
            )
            for action in actions
        ],
        escalated_contradictions=[evidence_out(db, ev) for ev in contradicting.values()],
        gaps=gaps,
        chain=[
            f"Decision {decision.code} · {decision.title}",
            *[f"Insight {i.insight.code} · {i.insight.title}" for i in insight_rows],
            *[f"Action {a.code} · {a.title}" for a in actions],
        ],
        provenance_note=(
            "Every evidence item here can be opened to read the customer's original words and the "
            "source it was collected from."
        ),
    )
