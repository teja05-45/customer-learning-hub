"""Deterministic synthetic dataset for the prototype.

Everything here is invented for demonstration. Names are fictional, no contact
details are stored, and no real customer, order or Everyday Goods system is
involved. Dates are relative to the moment the seed runs so the dashboard and
charts always look current.
"""

from app.core.security import DEMO_PASSWORD, hash_password
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import (
    ActivityLog,
    BusinessAction,
    ConsentRecord,
    Decision,
    DecisionEvidence,
    DecisionInsight,
    Evidence,
    FeedbackRecord,
    Insight,
    InsightEvidence,
    Interview,
    InterviewGuideQuestion,
    OrganizationSetting,
    Participant,
    RecruitmentEvent,
    RecruitmentRecord,
    ResearchProject,
    ResearchQuestion,
    User,
)

NOW = datetime.now(timezone.utc)


def _dt(days_ago: int, hour: int = 10, minute: int = 0) -> datetime:
    return (NOW - timedelta(days=days_ago)).replace(hour=hour, minute=minute, second=0, microsecond=0)


def _d(days_ago: int) -> date:
    return (NOW - timedelta(days=days_ago)).date()


SHAMPOO_GUIDE = [
    ("Can you tell me about the last time you purchased this shampoo?", "Open the conversation without assuming a reason for stopping."),
    ("How has the product fitted into your routine since then?", "Explore actual use, not stated preference."),
    ("What happened after you finished the bottle, or stopped using it?", "Surface the real decision point."),
    ("Did anything make you consider another product?", "Let alternatives emerge in the participant's words."),
    ("What else influenced your decision?", "Catch factors the team has not thought of."),
]


def seed_demo_data(db: Session, reset: bool = False) -> dict[str, int]:
    """Insert the synthetic dataset. Idempotent unless ``reset`` is True."""
    if reset:
        _wipe(db)
    elif db.execute(select(func.count(User.id))).scalar_one() > 0:
        return _counts(db)

    users = _seed_users(db)
    participants = _seed_participants(db)
    projects = _seed_projects(db, users)
    recruitment = _seed_recruitment(db, users, projects, participants)
    interviews = _seed_interviews(db, users, projects, participants, recruitment)
    evidence = _seed_evidence(db, users, projects, participants, interviews)
    _seed_feedback(db, users, projects, participants, interviews)
    insights = _seed_insights(db, users, projects, evidence)
    decisions = _seed_decisions(db, users, projects, insights, evidence)
    _seed_actions(db, users, decisions, insights)
    _seed_activity(db, users, projects, insights, decisions, interviews, evidence)
    db.add(
        OrganizationSetting(
            id="default",
            name="Everyday Goods",
            research_lead_id=users["priya"].id,
            recording_default=False,
            retention_months=12,
            show_demo_banner=True,
        )
    )
    db.commit()
    return _counts(db)


def _wipe(db: Session) -> None:
    for model in (
        ActivityLog,
        BusinessAction,
        DecisionEvidence,
        DecisionInsight,
        Decision,
        InsightEvidence,
        Insight,
        Evidence,
        FeedbackRecord,
        ConsentRecord,
        InterviewGuideQuestion,
        Interview,
        RecruitmentEvent,
        RecruitmentRecord,
        ResearchQuestion,
        ResearchProject,
        Participant,
        OrganizationSetting,
        User,
    ):
        db.execute(delete(model))
    db.commit()


def _counts(db: Session) -> dict[str, int]:
    models = {
        "users": User,
        "projects": ResearchProject,
        "participants": Participant,
        "recruitment": RecruitmentRecord,
        "interviews": Interview,
        "evidence": Evidence,
        "feedback": FeedbackRecord,
        "insights": Insight,
        "decisions": Decision,
        "actions": BusinessAction,
        "activity": ActivityLog,
    }
    return {name: db.execute(select(func.count(model.id))).scalar_one() for name, model in models.items()}


def _seed_users(db: Session) -> dict[str, User]:
    people = [
        ("asha", "Asha Menon", "ceo", "Chief Executive Officer", "AM"),
        ("priya", "Priya Menon", "researcher", "Customer Research Coordinator", "PM"),
        ("rohan", "Rohan Iyer", "business_owner", "Head of Growth", "RI"),
        ("dev", "Dev Patel", "business_owner", "Brand & Marketing Lead", "DP"),
        ("nisha", "Nisha Kulkarni", "business_owner", "Product & Category Lead", "NK"),
        ("vikram", "Vikram Shetty", "cx", "Customer Experience Lead", "VS"),
        ("arjun", "Arjun Desai", "admin", "Operations & Data Support", "AD"),
    ]
    users = {}
    # All demo accounts share one password, so hash it once: PBKDF2 is
    # deliberately slow and rebuilding the dataset is a common operation.
    demo_password_hash = hash_password(DEMO_PASSWORD)
    for key, name, role, title, initials in people:
        user = User(
            name=name,
            email=f"{key}.demo@example.test",
            role=role,
            job_title=title,
            initials=initials,
            password_hash=demo_password_hash,
            created_at=_dt(120),
        )
        db.add(user)
        users[key] = user
    db.flush()
    return users


def _seed_participants(db: Session) -> dict[str, Participant]:
    rows = [
        ("priya_sharma", "Priya Sharma", "repeat_buyer", "Every 6–8 weeks", 5, 12, "Shampoo", "eligible", "Happy to be contacted again for product studies."),
        ("rahul", "Rahul Verma", "first_time_buyer", "One purchase", 1, 96, "Shampoo", "eligible", "Bought once during a marketplace promotion."),
        ("ananya", "Ananya Rao", "lapsed_buyer", "One purchase, no repeat", 1, 154, "Shampoo", "eligible", "Reported a product-feel concern through support."),
        ("arjun_reddy", "Arjun Reddy", "household_buyer", "Every 10–12 weeks, multi-item", 7, 21, "Shampoo", "eligible", "Buys for a household of four."),
        ("meera", "Meera Nair", "repeat_buyer", "Every 4–6 weeks", 9, 9, "Body wash", "eligible", "Repeat buyer of body wash and moisturiser."),
        ("kiran", "Kiran Kumar", "first_time_buyer", "One purchase", 1, 63, "Body wash", "limited", "Could not be reached for the last study; two attempts already made."),
        ("divya", "Divya Suresh", "lapsed_buyer", "One purchase, no repeat", 1, 121, "Shampoo", "eligible", "Raised a delivery exception with support."),
        ("sanjay", "Sanjay Patil", "household_buyer", "Every 8 weeks", 6, 30, "Shampoo", "eligible", "Shares purchases with a flatmate."),
        ("farah", "Farah Khan", "repeat_buyer", "Every 5 weeks", 8, 14, "Moisturiser", "eligible", "Sensitive skin; reads ingredient labels."),
        ("nikhil", "Nikhil Joshi", "first_time_buyer", "One purchase", 1, 74, "Shampoo", "ineligible", "Previously declined participation; do not re-contact for this study."),
    ]
    participants = {}
    for index, (key, name, segment, freq, orders, last, category, eligibility, note) in enumerate(rows, start=1001):
        participant = Participant(
            code=f"P-{index}",
            display_name=name,
            segment=segment,
            purchase_frequency=freq,
            orders_count=orders,
            last_purchase_at=_d(last),
            product_category=category,
            eligibility=eligibility,
            eligibility_note=note,
            contact_route=f"Controlled export batch #{index - 990} (handled by Operations; contact values never stored here)",
            contact_consent="granted" if eligibility == "eligible" else "declined",
            notes="Synthetic demo record. No real personal data.",
            created_at=_dt(90 - index),
        )
        db.add(participant)
        participants[key] = participant
    db.flush()
    return participants


def _seed_projects(db: Session, users: dict[str, User]) -> dict[str, ResearchProject]:
    specs = [
        {
            "key": "shampoo_repeat",
            "name": "Why are shampoo buyers not purchasing again?",
            "objective": (
                "Understand what happened after a first shampoo purchase, and identify which explanations "
                "recur across customer segments instead of assuming a single cause."
            ),
            "description": (
                "Growth flagged weak repeat rates for the everyday shampoo. The internal hypothesis was price. "
                "This project tests that hypothesis against customer accounts, including people who never "
                "contacted support."
            ),
            "status": "in_progress",
            "priority": "high",
            "methodology": "Moderated 30-minute interviews (simulated)",
            "owner": users["priya"],
            "functions": ["growth", "product_category", "executive"],
            "segments": ["lapsed_buyer", "first_time_buyer", "household_buyer"],
            "start": 34,
            "deadline": -12,
            "questions": [
                ("What happened after the first bottle was finished?", False, ""),
                ("Which alternatives do customers consider, and why?", False, ""),
                ("Do household buyers judge the product differently from individual buyers?", True,
                 "Partially answered by two household conversations; not enough to generalize."),
                ("Is price the barrier, or is it something else?", True,
                 "Price did not come up unprompted in four conversations. Two participants raised value per bottle size instead."),
            ],
        },
        {
            "key": "routine_campaign",
            "name": "Everyday routine campaign perception",
            "objective": (
                "Check whether the 'everyday routine' campaign language matches the words customers use about "
                "their own routines, before the next flight of creative is produced."
            ),
            "description": (
                "Brand wanted to re-use a routine theme from an older product study but could not find the "
                "original notes. This project re-asks the question with explicit consent for quoting."
            ),
            "status": "analysis",
            "priority": "medium",
            "methodology": "Moderated 25-minute interviews (simulated)",
            "owner": users["dev"],
            "functions": ["brand_marketing", "growth"],
            "segments": ["repeat_buyer", "first_time_buyer"],
            "start": 48,
            "deadline": -5,
            "questions": [
                ("How do customers describe their own daily routine?", True,
                 "Routine language is concrete and unglamorous: 'quick', 'before work', 'whatever is in the shower'."),
                ("Does aspirational language feel like the brand or like advertising?", False, ""),
            ],
        },
        {
            "key": "bodywash",
            "name": "Body wash product experience study",
            "objective": (
                "Explore how body wash fits into a shared bathroom routine and what makes a bottle run out "
                "faster or slower than expected."
            ),
            "description": "Category team wants to understand usage in shared households before the next launch.",
            "status": "recruiting",
            "priority": "medium",
            "methodology": "Moderated 30-minute interviews (simulated)",
            "owner": users["nisha"],
            "functions": ["product_category", "operations"],
            "segments": ["repeat_buyer", "household_buyer"],
            "start": 12,
            "deadline": -30,
            "questions": [
                ("How is the product shared within a household?", False, ""),
                ("What signals that a bottle is nearly finished?", False, ""),
            ],
        },
        {
            "key": "first_to_second",
            "name": "First order to second order journey",
            "objective": (
                "Map the first 30 days after a first order to find where the second purchase decision is "
                "actually made, and which moments the team could influence."
            ),
            "description": "Growth and CX identified this as a shared priority; scoped but not yet recruiting.",
            "status": "planning",
            "priority": "high",
            "methodology": "Diary study plus short interviews (simulated)",
            "owner": users["rohan"],
            "functions": ["growth", "customer_experience"],
            "segments": ["first_time_buyer", "lapsed_buyer"],
            "start": -4,
            "deadline": -45,
            "questions": [
                ("What triggers a second purchase in the first month?", False, ""),
                ("Which support interactions change the decision?", False, ""),
                ("Where do customers get stuck between first and second order?", False, ""),
            ],
        },
        {
            "key": "packaging",
            "name": "Packaging refresh concept test",
            "objective": "Test two packaging concepts for shelf and marketplace thumbnail legibility.",
            "description": "Completed and archived. Kept visible so the team can reuse the evidence later.",
            "status": "archived",
            "priority": "low",
            "methodology": "Concept test (simulated)",
            "owner": users["dev"],
            "functions": ["brand_marketing", "product_category"],
            "segments": ["repeat_buyer"],
            "start": 150,
            "deadline": 96,
            "questions": [("Which concept is easier to recognise at thumbnail size?", True, "Concept B won on recognition; small sample.")],
        },
    ]

    projects: dict[str, ResearchProject] = {}
    for index, spec in enumerate(specs, start=1):
        project = ResearchProject(
            name=spec["name"],
            objective=spec["objective"],
            description=spec["description"],
            status=spec["status"],
            priority=spec["priority"],
            methodology=spec["methodology"],
            owner_id=spec["owner"].id,
            business_functions=spec["functions"],
            target_segments=spec["segments"],
            start_date=_d(spec["start"]),
            deadline=_d(spec["deadline"]),
            created_at=_dt(spec["start"]),
            archived_at=_dt(spec["deadline"]) if spec["status"] == "archived" else None,
            completed_at=_dt(spec["deadline"]) if spec["status"] in ("archived", "completed") else None,
        )
        db.add(project)
        db.flush()
        projects[spec["key"]] = project
        for order, (text, resolved, note) in enumerate(spec["questions"]):
            db.add(
                ResearchQuestion(
                    project_id=project.id,
                    text=text,
                    order_index=order,
                    is_resolved=resolved,
                    resolution_note=note,
                )
            )
    db.flush()
    return projects


def _seed_recruitment(
    db: Session,
    users: dict[str, User],
    projects: dict[str, ResearchProject],
    participants: dict[str, Participant],
) -> dict[str, RecruitmentRecord]:
    plan = [
        # project, participant, stage, invited_at, responded_at, next action, days in stage
        ("shampoo_repeat", "ananya", "completed", 30, 29, "Evidence captured; nothing outstanding.", 9),
        ("shampoo_repeat", "rahul", "completed", 30, 28, "Evidence captured; nothing outstanding.", 8),
        ("shampoo_repeat", "arjun_reddy", "completed", 27, 26, "Evidence captured; nothing outstanding.", 7),
        ("shampoo_repeat", "divya", "completed", 25, 24, "Evidence captured; nothing outstanding.", 6),
        ("shampoo_repeat", "meera", "scheduled", 12, 10, "Interview on the calendar; send reminder through Ops.", 2),
        ("shampoo_repeat", "kiran", "invited", 9, None, "Second attempt via the controlled Ops process, then mark no response.", 4),
        ("shampoo_repeat", "sanjay", "selected", None, None, "Confirm household buyer quota before inviting.", 1),
        ("shampoo_repeat", "nikhil", "declined", 20, 19, "Do not re-contact for this study.", 11),
        ("routine_campaign", "priya_sharma", "completed", 44, 43, "Nothing outstanding.", 20),
        ("routine_campaign", "farah", "completed", 42, 41, "Nothing outstanding.", 19),
        ("routine_campaign", "meera", "completed", 40, 39, "Nothing outstanding.", 18),
        ("bodywash", "priya_sharma", "selected", None, None, "Invite after the shampoo analysis is signed off.", 3),
        ("bodywash", "divya", "invited", 6, None, "Awaiting reply.", 6),
        ("bodywash", "sanjay", "invited", 5, None, "Awaiting reply.", 5),
    ]
    records: dict[str, RecruitmentRecord] = {}
    for project_key, participant_key, stage, invited, responded, next_action, age in plan:
        record = RecruitmentRecord(
            project_id=projects[project_key].id,
            participant_id=participants[participant_key].id,
            stage=stage,
            next_action=next_action,
            invited_at=_dt(invited) if invited else None,
            responded_at=_dt(responded) if responded else None,
            updated_by_id=users["priya"].id,
            created_at=_dt(age + 3),
            updated_at=_dt(age),
        )
        db.add(record)
        db.flush()
        db.add(
            RecruitmentEvent(
                recruitment_id=record.id,
                from_stage=None,
                to_stage="identified",
                note="Added to the recruitment list with a documented reason.",
                actor_id=users["priya"].id,
                created_at=_dt(age + 3),
            )
        )
        if stage not in ("identified", "selected"):
            db.add(
                RecruitmentEvent(
                    recruitment_id=record.id, from_stage="identified", to_stage="selected",
                    note="Selected to balance segments.", actor_id=users["priya"].id, created_at=_dt(age + 2),
                )
            )
            db.add(
                RecruitmentEvent(
                    recruitment_id=record.id, from_stage="selected", to_stage="invited",
                    note="Invitation sent through the controlled Ops process (simulated).",
                    actor_id=users["priya"].id, created_at=_dt(invited or age),
                )
            )
            if stage in ("completed", "declined", "responded", "scheduled"):
                db.add(
                    RecruitmentEvent(
                        recruitment_id=record.id, from_stage="invited", to_stage=stage if stage in ("declined",) else "responded",
                        note="Replied after one reminder." if stage != "declined" else "Declined: no time this month.",
                        actor_id=users["priya"].id, created_at=_dt(responded or age),
                    )
                )
            if stage in ("scheduled", "completed"):
                db.add(
                    RecruitmentEvent(
                        recruitment_id=record.id, from_stage="responded", to_stage="scheduled",
                        note="Time agreed.", actor_id=users["priya"].id, created_at=_dt(age + 1),
                    )
                )
            if stage == "completed":
                db.add(
                    RecruitmentEvent(
                        recruitment_id=record.id, from_stage="scheduled", to_stage="completed",
                        note="Conversation completed; evidence captured.", actor_id=users["priya"].id, created_at=_dt(age),
                    )
                )
        records[f"{project_key}:{participant_key}"] = record
    db.flush()
    return records


def _seed_interviews(
    db: Session,
    users: dict[str, User],
    projects: dict[str, ResearchProject],
    participants: dict[str, Participant],
    recruitment: dict[str, RecruitmentRecord],
) -> dict[str, Interview]:
    plan = [
        # key, project, participant, title, interviewer, status, days ago (scheduled), completed days ago, consent
        ("i_shampoo_ananya", "shampoo_repeat", "ananya", "First bottle, then nothing", "priya", "completed", 27, 27, "granted"),
        ("i_shampoo_rahul", "shampoo_repeat", "rahul", "Bought on a promotion", "priya", "completed", 25, 25, "granted"),
        ("i_shampoo_arjun", "shampoo_repeat", "arjun_reddy", "Household of four", "nisha", "completed", 22, 22, "granted"),
        ("i_shampoo_divya", "shampoo_repeat", "divya", "The delivery that went missing", "priya", "completed", 19, 19, "granted"),
        ("i_shampoo_meera", "shampoo_repeat", "meera", "Repeat buyer conversation", "priya", "scheduled", -2, None, "pending"),
        ("i_shampoo_kiran", "shampoo_repeat", "kiran", "First-time buyer, not yet scheduled", "priya", "planned", None, None, "pending"),
        ("i_campaign_priya", "routine_campaign", "priya_sharma", "What a routine actually sounds like", "dev", "completed", 40, 40, "granted"),
        ("i_campaign_farah", "routine_campaign", "farah", "Sensitive skin and shower shelf", "dev", "completed", 37, 37, "granted"),
        ("i_campaign_meera", "routine_campaign", "meera", "Products that earn their space", "dev", "completed", 33, 33, "granted"),
        ("i_bodywash_priya", "bodywash", "priya_sharma", "Body wash in a shared bathroom", "nisha", "scheduled", -5, None, "pending"),
        ("i_bodywash_divya", "bodywash", "divya", "Cancelled: participant unavailable", "nisha", "cancelled", 8, None, "pending"),
    ]
    interviews: dict[str, Interview] = {}
    for index, (key, project_key, participant_key, title, who, status, sched, completed, consent) in enumerate(plan, start=1):
        interview = Interview(
            code=f"INT-{index:04d}",
            project_id=projects[project_key].id,
            participant_id=participants[participant_key].id,
            recruitment_id=(recruitment.get(f"{project_key}:{participant_key}").id if recruitment.get(f"{project_key}:{participant_key}") else None),
            title=title,
            objective=projects[project_key].objective,
            scheduled_at=_dt(sched, hour=11) if sched is not None else None,
            duration_minutes=30,
            interviewer_id=users[who].id,
            status=status,
            consent_status=consent,
            recording_enabled=False,
            notes="",
            summary="",
            follow_up_questions=[],
            completed_at=_dt(completed, hour=12) if completed else None,
            created_at=_dt(abs(sched or 0) + 5),
        )
        db.add(interview)
        db.flush()
        for order, (text, purpose) in enumerate(SHAMPOO_GUIDE if project_key == "shampoo_repeat" else _campaign_guide(project_key)):
            db.add(
                InterviewGuideQuestion(
                    interview_id=interview.id, text=text, purpose=purpose, order_index=order, is_leading=False
                )
            )
        if consent == "granted":
            db.add(
                ConsentRecord(
                    interview_id=interview.id,
                    participant_id=participants[participant_key].id,
                    consent_type="participation",
                    status="granted",
                    recorded_by_id=users[who].id,
                    recorded_at=_dt((completed or 0) + 1),
                    note="Synthetic consent captured verbally at the start of the conversation.",
                )
            )
            db.add(
                ConsentRecord(
                    interview_id=interview.id,
                    participant_id=participants[participant_key].id,
                    consent_type="quoting",
                    status="granted",
                    recorded_by_id=users[who].id,
                    recorded_at=_dt((completed or 0) + 1),
                    note="Agreed that anonymised words may be quoted internally.",
                )
            )
        interviews[key] = interview
    db.flush()
    return interviews


def _campaign_guide(project_key: str) -> list[tuple[str, str]]:
    if project_key == "routine_campaign":
        return [
            ("Walk me through a normal morning for you.", "Get concrete routine language, not brand language."),
            ("Where do our products fit into that morning?", "Understand the role, not the preference."),
            ("If you described your routine to a friend, what words would you use?", "Collect customer vocabulary for copy."),
            ("What would make a routine-themed message feel false to you?", "Test the risk of aspirational tone."),
        ]
    return [
        ("Who else uses the body wash in your household?", "Understand shared usage."),
        ("How do you know when it is running low?", "Find replenishment signals."),
        ("What makes you pick a different bottle next time?", "Surface switching triggers."),
    ]


def _seed_evidence(
    db: Session,
    users: dict[str, User],
    projects: dict[str, ResearchProject],
    participants: dict[str, Participant],
    interviews: dict[str, Interview],
) -> dict[str, Evidence]:
    rows = [
        # key, interview, participant, type, content, interpretation, context, provenance, confidence, review, segment
        ("ev_still_using", "i_shampoo_ananya", "ananya", "verbatim_quote",
         "I am still using the first bottle. I only wash my hair a couple of times a week, so it has lasted.",
         "Low usage frequency may delay a repeat purchase without any dissatisfaction.",
         "Lapsed buyer, single purchase 5 months ago, uses the product twice a week.",
         "Interview INT-0001 · note 3 · synthetic transcript, 00:12:40", "medium", "reviewed", "lapsed_buyer"),
        ("ev_feel", "i_shampoo_ananya", "ananya", "verbatim_quote",
         "It left my hair feeling coated, so I stopped after about two weeks.",
         "Product feel is one reason this participant stopped, independent of price.",
         "Same participant, after describing usage.",
         "Interview INT-0001 · note 5 · synthetic transcript, 00:19:05", "medium", "reviewed", "lapsed_buyer"),
        ("ev_household", "i_shampoo_arjun", "arjun_reddy", "verbatim_quote",
         "I bought it for my daughter, she uses it. I could not tell you if she liked it.",
         "Purchaser and user are different people in household buying, so repeat behaviour may not reflect the user's view.",
         "Household buyer, four-person household, bought shampoo with other items.",
         "Interview INT-0003 · note 2 · synthetic transcript, 00:08:10", "medium", "reviewed", "household_buyer"),
        ("ev_shelf", "i_shampoo_arjun", "arjun_reddy", "observation",
         "Participant described the bottle as 'the big one' and could not recall the brand name without checking.",
         "Brand recall may be weaker than the team assumes in household purchases.",
         "Observed during the same conversation.",
         "Interview INT-0003 · researcher note 4", "low", "unreviewed", "household_buyer"),
        ("ev_delivery", "i_shampoo_divya", "divya", "verbatim_quote",
         "The courier left it with a neighbour and I never got it back. By the time it was sorted I had bought something else.",
         "A fulfilment failure, not product or price, ended this purchase journey.",
         "Lapsed buyer who contacted support about a delivery exception.",
         "Interview INT-0004 · note 3 · synthetic transcript, 00:14:22", "high", "reviewed", "lapsed_buyer"),
        ("ev_reordered", "i_shampoo_rahul", "rahul", "contradictory_evidence",
         "I did buy it again actually, the second one is in the shower now. It is fine for what it costs.",
         "Contradicts a simple 'customers do not repeat' framing for first-time buyers on promotion.",
         "Recorded as a first-time buyer in the export; had in fact reordered once.",
         "Interview INT-0002 · note 6 · synthetic transcript, 00:21:15", "high", "reviewed", "first_time_buyer"),
        ("ev_price", "i_shampoo_rahul", "rahul", "verbatim_quote",
         "Price was not really the thing. I just do not think about shampoo until the bottle is empty.",
         "Purchases may be triggered by depletion rather than evaluation, which delays any repeat decision.",
         "First-time buyer, bought during a promotion.",
         "Interview INT-0002 · note 4 · synthetic transcript, 00:16:02", "medium", "reviewed", "first_time_buyer"),
        ("ev_routine_fit", "i_shampoo_ananya", "ananya", "researcher_interpretation",
         "Across the first three conversations, routine fit came up before price. Price only appeared when the researcher asked about it directly.",
         "Treat the internal price hypothesis as unconfirmed rather than disproven.",
         "Interpretation written after three interviews, before the fourth.",
         "Researcher note, 12 May (synthetic)", "low", "flagged", "lapsed_buyer"),
        ("ev_question_size", "i_shampoo_divya", "divya", "open_question",
         "Would a smaller bottle change the repeat decision for low-frequency users? Nobody in the sample had an opinion because nobody was asked.",
         "Needs a deliberate question in the next round; do not treat as a finding.",
         "Raised by the researcher at analysis, not by a participant.",
         "Analysis note, synthetic", "low", "unreviewed", "lapsed_buyer"),
        ("ev_campaign_language", "i_campaign_priya", "priya_sharma", "verbatim_quote",
         "I do not think of it as a routine. I just pick up whatever is in the shower and go.",
         "Customers describe routine as habit and convenience, not as a crafted ritual.",
         "Repeat buyer, body wash and shampoo.",
         "Interview INT-0007 · note 3 · synthetic transcript, 00:10:55", "high", "reviewed", "repeat_buyer"),
        ("ev_campaign_false", "i_campaign_farah", "farah", "verbatim_quote",
         "When an advert says 'your moment', I know it is an advert. My morning is not a moment.",
         "Aspirational language reads as advertising to at least one repeat buyer.",
         "Repeat buyer, sensitive skin, reads labels.",
         "Interview INT-0008 · note 4 · synthetic transcript, 00:13:30", "medium", "reviewed", "repeat_buyer"),
        ("ev_campaign_space", "i_campaign_meera", "meera", "observation",
         "Participant repeatedly referred to products 'earning their space' in a shared bathroom.",
         "Shelf space may be a more useful frame than routine for household buyers.",
         "Repeat buyer in a shared flat.",
         "Interview INT-0009 · researcher note 2", "low", "unreviewed", "repeat_buyer"),
        ("ev_missing_provenance", None, None, "observation",
         "A note carried over from an older spreadsheet says customers found the shampoo 'too thin'.",
         "Kept as unverified context only; the original conversation and participant cannot be identified.",
         "Source, participant and date are unknown.",
         "", "low", "flagged", "unknown"),
    ]
    evidence: dict[str, Evidence] = {}
    for index, row in enumerate(rows, start=1):
        (key, interview_key, participant_key, ev_type, content, interpretation, context,
         provenance, confidence, review, segment) = row
        interview = interviews.get(interview_key) if interview_key else None
        ev = Evidence(
            code=f"EV-{index:04d}",
            interview_id=interview.id if interview else None,
            project_id=interview.project_id if interview else projects["shampoo_repeat"].id,
            participant_id=participants[participant_key].id if participant_key else None,
            evidence_type=ev_type,
            content=content,
            interpretation=interpretation,
            customer_context=context,
            segment=segment,
            provenance=provenance,
            provenance_status="recorded" if provenance else "missing",
            confidence=confidence,
            review_status=review,
            captured_by_id=users["priya"].id if interview_key else None,
            captured_at=_dt((interview.completed_at and (NOW - interview.completed_at).days) or 14, hour=13)
            if interview
            else _dt(60),
        )
        db.add(ev)
        evidence[key] = ev
    db.flush()
    return evidence


def _seed_feedback(
    db: Session,
    users: dict[str, User],
    projects: dict[str, ResearchProject],
    participants: dict[str, Participant],
    interviews: dict[str, Interview],
) -> None:
    """Add asynchronous and interview feedback in one provenance-preserving table."""
    rows = [
        (
            "ananya", "i_shampoo_ananya", "interview", "phone_interview",
            "Interview INT-0001 · synthetic transcript, 00:08:40", 24,
            "It lathered differently at home than it did in the shop. I finished it, but I did not buy it again.",
            "The gap between the in-store trial and home use may be an expectation problem.",
            "Repeat-purchase conversation, synthetic.", "verified", "shampoo_repeat",
        ),
        (
            "rahul", None, "short_survey", "short_survey",
            "Post-purchase survey · wave 2 · response 41", 38,
            "I would probably buy it again if the bottle was smaller.",
            "",
            "One-question exit survey. No follow-up was possible.", "unverified", "shampoo_repeat",
        ),
        (
            "divya", None, "customer_support", "support_feedback",
            "Support ticket export · delivery exception · approved sample", 16,
            "The replacement arrived after I had already bought another brand.",
            "Fulfilment timing, not product quality, may explain this lapse.",
            "Support resolution note, synthetic.", "needs_review", "shampoo_repeat",
        ),
        (
            None, None, "product_review", "product_review",
            "Marketplace review export · approved sample", 45,
            "Nice smell but the pump stopped working after a week.",
            "",
            "Public review with no participant identity. Unattributed by design.", "unverified", "shampoo_repeat",
        ),
        (
            "meera", None, "csv_import", "imported_feedback",
            "CRM feedback export · batch 2026-04 (approved)", 12,
            "I keep it in the shared bathroom because it does not leak.",
            "Shelf behaviour may matter more than brand routine for household buyers.",
            "Imported from an approved customer-feedback export.", "verified", "bodywash",
        ),
    ]
    for index, row in enumerate(rows, start=1):
        (participant_key, interview_key, source_type, method, reference, days,
         content, interpretation, context, verification, project_key) = row
        interview = interviews.get(interview_key) if interview_key else None
        db.add(
            FeedbackRecord(
                code=f"FB-{index:04d}",
                project_id=projects[project_key].id,
                participant_id=participants[participant_key].id if participant_key else None,
                interview_id=interview.id if interview else None,
                source_type=source_type,
                collection_method=method,
                source_reference=reference,
                collected_at=_dt(days, hour=11),
                contributor="Priya Menon" if source_type == "interview" else "Operations import",
                content=content,
                interpretation=interpretation,
                context=context,
                verification_status=verification,
                created_by_id=users["priya"].id,
            )
        )
    db.flush()


def _seed_insights(
    db: Session,
    users: dict[str, User],
    projects: dict[str, ResearchProject],
    evidence: dict[str, Evidence],
) -> dict[str, Insight]:
    specs = [
        {
            "key": "shampoo_multi",
            "title": "Multiple factors may explain the lack of repeat shampoo purchases",
            "summary": (
                "Four conversations produced four different accounts: a bottle still in use, a purchase made for "
                "another household member, a product-feel complaint, and a delivery failure. Price did not come up "
                "unprompted in any of them."
            ),
            "interpretation": (
                "The evidence is consistent with several explanations operating at once. It does not establish how "
                "common any explanation is, and a single-cause story such as 'price' would misrepresent it."
            ),
            "project": "shampoo_repeat",
            "status": "under_review",
            "confidence": "low",
            "owner": "priya",
            "limitations": (
                "Four fictional interview examples. Selection favoured people who could be reached quickly, and "
                "no one from the marketplace-only segment was included. Not representative of the customer base."
            ),
            "segments": ["lapsed_buyer", "household_buyer", "first_time_buyer"],
            "evidence": [
                ("ev_still_using", "supporting"),
                ("ev_household", "supporting"),
                ("ev_feel", "supporting"),
                ("ev_delivery", "supporting"),
                ("ev_reordered", "contradictory"),
            ],
            "created": 18,
        },
        {
            "key": "shampoo_price",
            "title": "Price is not the first explanation customers offer",
            "summary": (
                "When asked openly what happened after purchase, none of the four participants raised price. "
                "Two mentioned value relative to bottle size only after a prompt."
            ),
            "interpretation": (
                "The internal price hypothesis should be treated as untested rather than rejected. The sample is too "
                "small to conclude that price does not matter to the wider customer base."
            ),
            "project": "shampoo_repeat",
            "status": "draft",
            "confidence": "low",
            "owner": "rohan",
            "limitations": "Prompting may have introduced value framing. Four participants, all reachable by email.",
            "segments": ["lapsed_buyer", "first_time_buyer"],
            "evidence": [("ev_price", "supporting"), ("ev_routine_fit", "supporting")],
            "created": 12,
        },
        {
            "key": "delivery_drop",
            "title": "Fulfilment failures create a silent drop-off",
            "summary": (
                "One participant stopped buying after a delivery exception was resolved too late. Support closed "
                "the ticket without asking whether the customer still wanted the product."
            ),
            "interpretation": (
                "A cancelled order is not always a lost sale. The gap sits between support resolution and a "
                "purchase decision, and no one currently owns it."
            ),
            "project": "shampoo_repeat",
            "status": "needs_more_research",
            "confidence": "low",
            "owner": "vikram",
            "limitations": "Single case. Support ticket volume has not been reviewed, so frequency is unknown.",
            "segments": ["lapsed_buyer"],
            "evidence": [("ev_delivery", "supporting")],
            "created": 9,
        },
        {
            "key": "campaign_language",
            "title": "Customers describe routine as habit, not as a crafted moment",
            "summary": (
                "Repeat buyers used concrete, unglamorous language: 'whatever is in the shower', 'before work'. "
                "Aspirational framing was recognised as advertising."
            ),
            "interpretation": (
                "Campaign copy is more likely to land if it uses the flat, practical vocabulary customers use "
                "about their own mornings."
            ),
            "project": "routine_campaign",
            "status": "validated_internal",
            "confidence": "medium",
            "owner": "dev",
            "limitations": (
                "Internal validation means the team reviewed the evidence and context. It does not mean the finding "
                "is representative of all customers."
            ),
            "segments": ["repeat_buyer"],
            "evidence": [
                ("ev_campaign_language", "supporting"),
                ("ev_campaign_false", "supporting"),
                ("ev_campaign_space", "supporting"),
            ],
            "created": 26,
        },
    ]

    insights: dict[str, Insight] = {}
    for index, spec in enumerate(specs, start=1):
        insight = Insight(
            code=f"INS-{index:04d}",
            title=spec["title"],
            summary=spec["summary"],
            interpretation=spec["interpretation"],
            research_question=projects[spec["project"]].questions[0].text
            if projects[spec["project"]].questions
            else "",
            project_id=projects[spec["project"]].id,
            status=spec["status"],
            confidence=spec["confidence"],
            owner_id=users[spec["owner"]].id,
            limitations=spec["limitations"],
            segments=spec["segments"],
            created_at=_dt(spec["created"]),
            validated_at=_dt(spec["created"] - 2) if spec["status"] == "validated_internal" else None,
            validated_by_id=users["asha"].id if spec["status"] == "validated_internal" else None,
        )
        db.add(insight)
        db.flush()
        for ev_key, role in spec["evidence"]:
            db.add(InsightEvidence(insight_id=insight.id, evidence_id=evidence[ev_key].id, role=role))
        insights[spec["key"]] = insight
    db.flush()
    return insights


def _seed_decisions(
    db: Session,
    users: dict[str, User],
    projects: dict[str, ResearchProject],
    insights: dict[str, Insight],
    evidence: dict[str, Evidence],
) -> dict[str, Decision]:
    specs = [
        {
            "key": "pack_size",
            "title": "Run a bottle-size test before changing price",
            "function": "growth",
            "problem": "Repeat purchase is weak for the shampoo, and the internal explanation of price is not supported by the conversations so far.",
            "description": (
                "Test a 200ml trial size for low-frequency users alongside the current 400ml bottle, and measure "
                "second purchase within 60 days for each group."
            ),
            "rationale": (
                "The evidence points at depletion timing, bottle size and product feel rather than price alone. "
                "A size test is cheap to run and would settle one open question."
            ),
            "limitations": "Four conversations. The test needs enough volume to detect a difference, which the current sample cannot provide.",
            "project": "shampoo_repeat",
            "owner": "rohan",
            "status": "accepted",
            "date": 6,
            "insights": ["shampoo_multi", "shampoo_price"],
            "evidence": [("ev_still_using", "supporting"), ("ev_price", "supporting")],
            "sufficient": False,
        },
        {
            "key": "campaign_rewrite",
            "title": "Rewrite the routine campaign in customer language",
            "function": "brand_marketing",
            "problem": "The planned 'your moment' framing does not match how repeat buyers describe their own mornings.",
            "description": (
                "Replace aspirational routine copy with the practical vocabulary participants used, keeping the "
                "same media plan and budget."
            ),
            "rationale": "Three repeat buyers independently described routine as habit and convenience.",
            "limitations": "Only repeat buyers were interviewed; first-time buyers may respond differently to aspirational copy.",
            "project": "routine_campaign",
            "owner": "dev",
            "status": "under_review",
            "date": 3,
            "insights": ["campaign_language"],
            "evidence": [],
            "sufficient": None,
        },
        {
            "key": "support_prompt",
            "title": "Add a 'do you still want this?' step to delivery exception handling",
            "function": "customer_experience",
            "problem": "Support closes delivery exceptions without checking whether the customer still wants the product, which may silently end the relationship.",
            "description": (
                "Add a single question to the delivery-exception macro and record the answer, so the team can see "
                "how often a resolved issue ends in a lost repurchase."
            ),
            "rationale": "One conversation described exactly this sequence, and support agreed it is plausible.",
            "limitations": (
                "This decision is not yet linked to customer evidence. It should be treated as an internal "
                "improvement, and evidence gathered before it is described as research-backed."
            ),
            "project": "shampoo_repeat",
            "owner": "vikram",
            "status": "proposed",
            "date": 1,
            "insights": [],
            "evidence": [],
            "sufficient": False,
        },
        {
            "key": "pause_shampoo",
            "title": "Do not re-run the shampoo study this quarter",
            "function": "product_category",
            "problem": "Category asked whether another round of shampoo interviews was needed immediately.",
            "description": (
                "Defer further shampoo interviews until the size test results are available, and instead use the "
                "capacity to recruit household buyers for the body wash study."
            ),
            "rationale": "More conversations of the same shape would not answer the remaining questions about frequency.",
            "limitations": "Assumes the size test produces usable data. If it does not, the question reopens.",
            "project": "shampoo_repeat",
            "owner": "nisha",
            "status": "deferred",
            "date": 8,
            "insights": ["shampoo_multi"],
            "evidence": [("ev_question_size", "supporting")],
            "sufficient": None,
        },
    ]
    decisions: dict[str, Decision] = {}
    for index, spec in enumerate(specs, start=1):
        decision = Decision(
            code=f"DEC-{index:03d}",
            title=spec["title"],
            business_function=spec["function"],
            problem_statement=spec["problem"],
            description=spec["description"],
            rationale=spec["rationale"],
            limitations=spec["limitations"],
            project_id=projects[spec["project"]].id,
            owner_id=users[spec["owner"]].id,
            decision_date=_d(spec["date"]),
            status=spec["status"],
            evidence_sufficient=spec["sufficient"],
            created_at=_dt(spec["date"] + 1),
        )
        db.add(decision)
        db.flush()
        for insight_key in spec["insights"]:
            db.add(DecisionInsight(decision_id=decision.id, insight_id=insights[insight_key].id))
        for ev_key, role in spec["evidence"]:
            db.add(DecisionEvidence(decision_id=decision.id, evidence_id=evidence[ev_key].id, role=role))
        decisions[spec["key"]] = decision
    db.flush()
    return decisions


def _seed_actions(
    db: Session,
    users: dict[str, User],
    decisions: dict[str, Decision],
    insights: dict[str, Insight],
) -> None:
    rows = [
        ("Define the 200ml trial SKU with Operations", "pack_size", "arjun", "high", "completed", -2, -4),
        ("Brief the marketplace team on the trial listing", "pack_size", "rohan", "medium", "in_progress", -1, None),
        ("Recruit 8 lapsed buyers for the size test", "pack_size", "priya", "high", "blocked", 3, None),
        ("Rewrite hero copy using three customer phrases", "campaign_rewrite", "dev", "high", "in_progress", 4, None),
        ("Add delivery-exception question to the support macro", "support_prompt", "vikram", "medium", "not_started", 9, None),
        ("Book a decision review for the size test results", "pack_size", "asha", "low", "not_started", 14, None),
        ("Archive the packaging concept decisions", None, "dev", "low", "completed", -6, -7),
    ]
    for index, (title, decision_key, owner, priority, status, due, completed) in enumerate(rows, start=1):
        action = BusinessAction(
            code=f"ACT-{index:03d}",
            title=title,
            description=(
                "Synthetic demo action. Owner is accountable for the next step and the due date is used for the "
                "overdue view."
            ),
            owner_id=users[owner].id,
            due_date=_d(due),
            priority=priority,
            status=status,
            decision_id=decisions[decision_key].id if decision_key else None,
            insight_id=insights["shampoo_multi"].id if decision_key == "pack_size" and index == 3 else None,
            completed_at=_dt(completed) if completed else None,
            created_at=_dt(10),
        )
        db.add(action)
    db.flush()


def _seed_activity(
    db: Session,
    users: dict[str, User],
    projects: dict[str, ResearchProject],
    insights: dict[str, Insight],
    decisions: dict[str, Decision],
    interviews: dict[str, Interview],
    evidence: dict[str, Evidence],
) -> None:
    rows = [
        ("project", projects["shampoo_repeat"].id, "Why are shampoo buyers not purchasing again?", "updated",
         "Status moved to In Progress and the price hypothesis was marked as untested.", "priya", 20, "shampoo_repeat"),
        ("interview", interviews["i_shampoo_ananya"].id, "INT-0001 · First bottle, then nothing", "completed",
         "Conversation completed and consent recorded for internal quoting.", "priya", 27, "shampoo_repeat"),
        ("evidence", evidence["ev_delivery"].id, "EV-0005 · Delivery exception", "captured",
         "Evidence captured with full provenance from INT-0004.", "priya", 19, "shampoo_repeat"),
        ("insight", insights["shampoo_multi"].id, "Multiple factors may explain the lack of repeat shampoo purchases",
         "created", "Insight drafted from five evidence items with one contradiction attached.", "priya", 18, "shampoo_repeat"),
        ("decision", decisions["pack_size"].id, "Run a bottle-size test before changing price", "accepted",
         "Growth accepted the decision with an explicit limitation note.", "rohan", 6, "shampoo_repeat"),
        ("action", None, "Recruit 8 lapsed buyers for the size test", "blocked",
         "Blocked: the requested export has not been approved by Operations.", "priya", 2, "shampoo_repeat"),
        ("insight", insights["campaign_language"].id, "Customers describe routine as habit, not as a crafted moment",
         "validated", "Reviewed and validated for internal use by the CEO and Brand lead.", "dev", 24, "routine_campaign"),
        ("decision", decisions["campaign_rewrite"].id, "Rewrite the routine campaign in customer language",
         "created", "Decision proposed with supporting evidence and stated limitations.", "dev", 3, "routine_campaign"),
        ("decision", decisions["support_prompt"].id,
         "Add a 'do you still want this?' step to delivery exception handling", "created",
         "Recorded as an internal improvement with no linked customer evidence.", "vikram", 1, "shampoo_repeat"),
        ("project", projects["bodywash"].id, "Body wash product experience study", "updated",
         "Two invitations sent through the controlled Ops process (simulated).", "nisha", 5, "bodywash"),
    ]
    for entity_type, entity_id, label, verb, summary, actor, days, project_key in rows:
        db.add(
            ActivityLog(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_label=label,
                verb=verb,
                summary=summary,
                actor_id=users[actor].id,
                project_id=projects[project_key].id,
                created_at=_dt(days, hour=15),
            )
        )
    db.flush()
