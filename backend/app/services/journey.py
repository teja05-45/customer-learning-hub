"""Derived learning-journey view for one research project.

Nothing here is stored: every card and timeline entry is read from the records
the team already created, so the board cannot drift away from the data. The
board is a navigational view; status transitions still happen on the entity's
own page, which is where permissions and validation live.
"""

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BusinessAction,
    Decision,
    Evidence,
    FeedbackRecord,
    Insight,
    Interview,
    Outcome,
    RecruitmentRecord,
    ResearchProject,
)
from app.schemas.journey import (
    JourneyCard,
    JourneyStage,
    JourneyTimelineItem,
    ProjectJourney,
)

JOURNEY_STAGES = (
    ("discovery", "Discovery", "The business question and its research questions"),
    ("recruitment", "Recruitment", "Who was selected, invited and responded"),
    ("sessions", "Sessions", "Conversations and their consent state"),
    ("feedback", "Feedback", "Written, imported and asynchronous sources"),
    ("evidence", "Evidence", "What customers actually said, with provenance"),
    ("insights", "Insights", "Reviewed findings and contradictions"),
    ("decisions", "Decisions", "What the business chose to do, and why"),
    ("actions", "Actions", "Named owners and due dates"),
    ("outcomes", "Outcomes", "Whether the expected change actually happened"),
)


def _stage_status(count: int, complete: bool, active: bool) -> str:
    if count == 0:
        return "not_started"
    if complete:
        return "complete"
    return "in_progress" if active else "waiting"


def _card(
    *,
    id_: str,
    code: str,
    title: str,
    subtitle: str,
    status: str,
    href: str,
    at: datetime | date | None = None,
    overdue: bool = False,
) -> JourneyCard:
    return JourneyCard(
        id=id_,
        code=code,
        title=title,
        subtitle=subtitle,
        status=status,
        href=href,
        at=at,
        overdue=overdue,
    )


def build_journey(db: Session, project: ResearchProject) -> ProjectJourney:
    today = date.today()
    questions = list(project.questions)
    recruitment = db.execute(
        select(RecruitmentRecord).where(RecruitmentRecord.project_id == project.id)
    ).scalars().all()
    interviews = db.execute(
        select(Interview).where(Interview.project_id == project.id).order_by(
            Interview.scheduled_at.asc().nulls_last()
        )
    ).scalars().all()
    feedback = db.execute(
        select(FeedbackRecord).where(FeedbackRecord.project_id == project.id).order_by(
            FeedbackRecord.collected_at.desc()
        )
    ).scalars().all()
    evidence = db.execute(
        select(Evidence).where(Evidence.project_id == project.id).order_by(Evidence.captured_at.desc())
    ).scalars().all()
    insights = db.execute(
        select(Insight).where(Insight.project_id == project.id).order_by(Insight.created_at.desc())
    ).scalars().all()
    decisions = db.execute(
        select(Decision).where(Decision.project_id == project.id).order_by(Decision.created_at.desc())
    ).scalars().all()
    decision_ids = [d.id for d in decisions]
    actions = (
        db.execute(
            select(BusinessAction)
            .where(BusinessAction.decision_id.in_(decision_ids))
            .order_by(BusinessAction.due_date.asc().nulls_last())
        ).scalars().all()
        if decision_ids
        else []
    )
    outcomes = (
        db.execute(
            select(Outcome)
            .where(Outcome.decision_id.in_(decision_ids))
            .order_by(Outcome.measurement_end.asc().nulls_last())
        ).scalars().all()
        if decision_ids
        else []
    )

    stages: list[JourneyStage] = []

    stages.append(
        JourneyStage(
            key="discovery",
            label="Discovery",
            description="The business question and its research questions",
            count=len(questions),
            status=_stage_status(len(questions), all(q.is_resolved for q in questions), True),
            items=[
                _card(
                    id_=q.id,
                    code=f"Q{index + 1}",
                    title=q.text,
                    subtitle=q.resolution_note or ("Answered" if q.is_resolved else "Open question"),
                    status="complete" if q.is_resolved else "open",
                    href=f"/projects/{project.id}",
                    at=project.start_date,
                )
                for index, q in enumerate(questions[:8])
            ],
        )
    )

    terminal_recruitment = {"completed", "declined", "withdrawn", "cancelled", "no_response"}
    stages.append(
        JourneyStage(
            key="recruitment",
            label="Recruitment",
            description="Who was selected, invited and responded",
            count=len(recruitment),
            status=_stage_status(
                len(recruitment),
                all(r.stage in terminal_recruitment for r in recruitment),
                any(r.stage not in terminal_recruitment for r in recruitment),
            ),
            items=[
                _card(
                    id_=r.id,
                    code=f"REC-{r.id[:4].upper()}",
                    title=r.next_action or "No next action recorded",
                    subtitle=f"Stage: {r.stage.replace('_', ' ')}"
                    + (f" · invited {r.invited_at.date().isoformat()}" if r.invited_at else ""),
                    status=r.stage,
                    href="/recruitment",
                    at=r.updated_at,
                )
                for r in recruitment[:8]
            ],
        )
    )

    stages.append(
        JourneyStage(
            key="sessions",
            label="Sessions",
            description="Conversations and their consent state",
            count=len(interviews),
            status=_stage_status(
                len(interviews),
                all(i.status in {"completed", "cancelled"} for i in interviews),
                any(i.status in {"planned", "scheduled", "in_progress"} for i in interviews),
            ),
            items=[
                _card(
                    id_=i.id,
                    code=i.code,
                    title=i.title,
                    subtitle=f"{i.status.replace('_', ' ')} · consent {i.consent_status}",
                    status=i.status,
                    href=f"/interviews/{i.id}",
                    at=i.scheduled_at,
                )
                for i in interviews[:8]
            ],
        )
    )

    stages.append(
        JourneyStage(
            key="feedback",
            label="Feedback",
            description="Written, imported and asynchronous sources",
            count=len(feedback),
            status=_stage_status(len(feedback), True, False),
            items=[
                _card(
                    id_=f.id,
                    code=f.code,
                    title=f.content[:120] + ("…" if len(f.content) > 120 else ""),
                    subtitle=f"{f.source_type.replace('_', ' ')} · {f.verification_status.replace('_', ' ')}",
                    status=f.verification_status,
                    href=f"/feedback?focus={f.id}",
                    at=f.collected_at,
                )
                for f in feedback[:8]
            ],
        )
    )

    stages.append(
        JourneyStage(
            key="evidence",
            label="Evidence",
            description="What customers actually said, with provenance",
            count=len(evidence),
            status=_stage_status(
                len(evidence),
                all(e.review_status == "reviewed" for e in evidence),
                any(e.review_status != "reviewed" for e in evidence),
            ),
            items=[
                _card(
                    id_=e.id,
                    code=e.code,
                    title=e.content[:120] + ("…" if len(e.content) > 120 else ""),
                    subtitle=f"{e.evidence_type.replace('_', ' ')} · {e.provenance_status} provenance",
                    status=e.review_status,
                    href=f"/evidence/{e.id}",
                    at=e.captured_at,
                )
                for e in evidence[:8]
            ],
        )
    )

    stages.append(
        JourneyStage(
            key="insights",
            label="Insights",
            description="Reviewed findings and contradictions",
            count=len(insights),
            status=_stage_status(
                len(insights),
                all(i.status in {"validated_internal", "archived"} for i in insights),
                any(i.status in {"draft", "under_review", "needs_more_research"} for i in insights),
            ),
            items=[
                _card(
                    id_=i.id,
                    code=i.code,
                    title=i.title,
                    subtitle=f"{i.status.replace('_', ' ')} · {i.confidence} confidence",
                    status=i.status,
                    href=f"/insights/{i.id}",
                    at=i.validated_at or i.created_at,
                )
                for i in insights[:8]
            ],
        )
    )

    stages.append(
        JourneyStage(
            key="decisions",
            label="Decisions",
            description="What the business chose to do, and why",
            count=len(decisions),
            status=_stage_status(
                len(decisions),
                all(d.status in {"accepted", "rejected"} for d in decisions),
                any(d.status in {"proposed", "under_review", "deferred"} for d in decisions),
            ),
            items=[
                _card(
                    id_=d.id,
                    code=d.code,
                    title=d.title,
                    subtitle=f"{d.status.replace('_', ' ')} · {d.business_function.replace('_', ' ')}",
                    status=d.status,
                    href=f"/decisions/{d.id}",
                    at=d.decision_date,
                )
                for d in decisions[:8]
            ],
        )
    )

    stages.append(
        JourneyStage(
            key="actions",
            label="Actions",
            description="Named owners and due dates",
            count=len(actions),
            status=_stage_status(
                len(actions),
                all(a.status == "completed" for a in actions),
                any(a.status in {"in_progress", "blocked", "not_started"} for a in actions),
            ),
            items=[
                _card(
                    id_=a.id,
                    code=a.code,
                    title=a.title,
                    subtitle=f"{a.status.replace('_', ' ')} · due {a.due_date.isoformat() if a.due_date else 'not set'}",
                    status=a.status,
                    href="/actions",
                    at=a.due_date,
                    overdue=bool(a.due_date and a.due_date < today and a.status != "completed"),
                )
                for a in actions[:8]
            ],
        )
    )

    measured = {"achieved", "not_achieved", "inconclusive"}
    stages.append(
        JourneyStage(
            key="outcomes",
            label="Outcomes",
            description="Whether the expected change actually happened",
            count=len(outcomes),
            status=_stage_status(
                len(outcomes),
                all(o.status in measured for o in outcomes),
                any(o.status in {"planned", "measurement_pending"} for o in outcomes),
            ),
            items=[
                _card(
                    id_=o.id,
                    code=o.code,
                    title=o.name,
                    subtitle=f"{o.status.replace('_', ' ')} · target {o.target_value if o.target_value is not None else 'not set'}{(' ' + o.unit) if o.unit else ''}",
                    status=o.status,
                    href=f"/outcomes?focus={o.id}",
                    at=o.measurement_end,
                    overdue=bool(
                        o.measurement_end and o.measurement_end < today and o.status not in measured
                    ),
                )
                for o in outcomes[:8]
            ],
        )
    )

    timeline: list[JourneyTimelineItem] = []

    def add(
        at: datetime | date | None,
        kind: str,
        title: str,
        detail: str = "",
        href: str | None = None,
        state: str = "past",
    ) -> None:
        if at is None:
            return
        timeline.append(
            JourneyTimelineItem(
                at=at,
                kind=kind,
                title=title,
                detail=detail,
                href=href,
                state=state,
            )
        )

    add(project.start_date, "project", "Project started", project.name, f"/projects/{project.id}")
    add(
        project.deadline,
        "milestone",
        "Project deadline",
        "",
        f"/projects/{project.id}",
        "upcoming" if project.deadline and project.deadline > today else "past",
    )
    for r in recruitment:
        add(r.invited_at, "recruitment", "Invitation recorded", r.stage.replace("_", " "), "/recruitment")
        add(r.responded_at, "recruitment", "Response recorded", r.stage.replace("_", " "), "/recruitment")
    for i in interviews:
        add(i.scheduled_at, "session", f"{i.code} scheduled", i.title, f"/interviews/{i.id}")
        add(i.completed_at, "session", f"{i.code} completed", i.title, f"/interviews/{i.id}")
    for f in feedback:
        add(f.collected_at, "feedback", f"{f.code} collected", f.source_type.replace("_", " "), "/feedback")
    for e in evidence:
        add(e.captured_at, "evidence", f"{e.code} captured", e.evidence_type.replace("_", " "), f"/evidence/{e.id}")
    for i in insights:
        add(i.created_at, "insight", f"{i.code} drafted", i.title, f"/insights/{i.id}")
        add(i.validated_at, "insight", f"{i.code} validated", i.title, f"/insights/{i.id}")
    for d in decisions:
        add(d.decision_date, "decision", f"{d.code} decided", d.title, f"/decisions/{d.id}")
    for a in actions:
        overdue = bool(a.due_date and a.due_date < today and a.status != "completed")
        due_state = "overdue" if overdue else ("upcoming" if a.due_date and a.due_date > today else "past")
        add(a.due_date, "action", f"{a.code} due", a.title, "/actions", due_state)
        add(a.completed_at, "action", f"{a.code} completed", a.title, "/actions")
    for o in outcomes:
        start_state = "upcoming" if o.measurement_start and o.measurement_start > today else "past"
        add(o.measurement_start, "outcome", f"{o.code} measurement starts", o.name, "/outcomes", start_state)
        overdue = bool(
            o.measurement_end and o.measurement_end < today and o.status not in measured
        )
        end_state = "overdue" if overdue else ("upcoming" if o.measurement_end and o.measurement_end > today else "past")
        add(
            o.measurement_end,
            "outcome",
            f"{o.code} measurement due",
            o.name,
            "/outcomes",
            end_state,
        )
        add(o.recorded_at, "outcome", f"{o.code} result recorded", o.name, "/outcomes")

    timeline.sort(key=lambda item: (item.at if isinstance(item.at, datetime) else datetime.combine(item.at, datetime.min.time())))

    warnings: list[str] = []
    if not insights:
        warnings.append("No insights yet: the project has not turned evidence into a reviewed finding.")
    if decisions and all(d.evidence_sufficient is False for d in decisions):
        warnings.append("Every recorded decision is marked as lacking sufficient evidence.")
    unmeasured = [o for o in outcomes if o.status in {"planned", "measurement_pending"}]
    if unmeasured:
        warnings.append(
            f"{len(unmeasured)} outcome(s) are planned or pending. The loop is not closed until a result is recorded."
        )
    if not outcomes and decisions:
        warnings.append("No outcome is planned for the recorded decisions, so their effect cannot be judged.")

    return ProjectJourney(
        project_id=project.id,
        project_name=project.name,
        project_status=project.status,
        generated_at=datetime.now(timezone.utc),
        stages=stages,
        timeline=timeline[:200],
        warnings=warnings,
    )
