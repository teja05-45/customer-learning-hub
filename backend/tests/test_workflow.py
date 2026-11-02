"""The complete journey the product exists to support.

Question → project → participant → recruitment → interview → evidence →
insight → decision → action → find it again.
"""

from datetime import date, timedelta


def test_full_research_to_decision_journey(seeded):
    # 1. A research question becomes a project with an explicit objective.
    project = seeded.post(
        "/api/v1/projects",
        json={
            "name": "Why do household buyers stop at one bottle?",
            "objective": "Understand whether shared households make repeat purchase decisions differently.",
            "status": "recruiting",
            "priority": "medium",
            "business_functions": ["product_category"],
            "target_segments": ["household_buyer"],
            "start_date": str(date.today()),
            "deadline": str(date.today() + timedelta(days=30)),
            "questions": [
                {"text": "Who decides to buy the next bottle in a shared household?"},
                {"text": "Does bottle size change the decision?"},
            ],
        },
    )
    assert project.status_code == 201, project.text
    project_body = project.json()
    assert project_body["unresolved_questions"] == 2

    # 2. A synthetic participant is added without storing contact details.
    participant = seeded.post(
        "/api/v1/participants",
        json={
            "display_name": "Journey Test Buyer",
            "segment": "household_buyer",
            "purchase_frequency": "Every 8 weeks",
            "orders_count": 2,
            "product_category": "Shampoo",
            "eligibility": "eligible",
        },
    )
    assert participant.status_code == 201, participant.text
    participant_body = participant.json()

    # 3. The participant joins the recruitment pipeline.
    recruitment = seeded.post(
        "/api/v1/recruitment",
        json={"project_id": project_body["id"], "participant_ids": [participant_body["id"]]},
    )
    assert recruitment.status_code == 201, recruitment.text
    record = recruitment.json()["created"][0]
    assert record["stage"] == "selected"

    # 4. Outreach is recorded as simulated, then the invitation response arrives.
    invited = seeded.patch(
        f"/api/v1/recruitment/{record['id']}",
        json={"stage": "invited", "note": "Invitation sent through the controlled Ops process (simulated)."},
    )
    assert invited.status_code == 200
    responded = seeded.patch(f"/api/v1/recruitment/{record['id']}", json={"stage": "responded"})
    assert responded.status_code == 200

    # 5. An interview is scheduled with a neutral guide.
    interview = seeded.post(
        "/api/v1/interviews",
        json={
            "project_id": project_body["id"],
            "participant_id": participant_body["id"],
            "title": "Household bottle decision",
            "scheduled_at": "2026-12-15T10:00:00Z",
            "interviewer_id": record["updated_by"]["id"] if record.get("updated_by") else None,
            "status": "scheduled",
            "use_default_guide": True,
        },
    )
    assert interview.status_code == 201, interview.text
    interview_body = interview.json()
    assert interview_body["recording_enabled"] is False
    assert len(interview_body["guide"]) >= 4

    # 6. Consent is recorded, then the conversation is completed.
    seeded.post(
        f"/api/v1/interviews/{interview_body['id']}/consent",
        json={"consent_type": "participation", "status": "granted", "note": "Simulated verbal consent."},
    )
    completed = seeded.patch(
        f"/api/v1/interviews/{interview_body['id']}",
        json={"status": "completed", "notes": "Participant described a shared bathroom shelf."},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["consent_status"] == "granted"

    # 7. Evidence is captured with provenance, and a quote is kept verbatim.
    quote = seeded.post(
        "/api/v1/evidence",
        json={
            "interview_id": interview_body["id"],
            "evidence_type": "verbatim_quote",
            "content": "My partner buys whatever is on offer, I do not think either of us owns the shampoo decision.",
            "interpretation": "Purchase ownership may be shared, which weakens the single-buyer assumption.",
            "customer_context": "Household of three, two adults buying.",
            "provenance": "Interview note 2, synthetic transcript 00:07:45",
            "confidence": "medium",
        },
    )
    assert quote.status_code == 201, quote.text
    quote_body = quote.json()
    assert quote_body["is_verified_source"] is True
    assert quote_body["segment"] == "household_buyer"

    # 8. An insight is drafted from that evidence.
    insight = seeded.post(
        "/api/v1/insights",
        json={
            "title": "Household purchases may not have a single decision owner",
            "summary": (
                "One conversation suggested that neither adult feels responsible for the shampoo decision, which "
                "could explain why nobody re-orders deliberately."
            ),
            "research_question": "Who decides to buy the next bottle in a shared household?",
            "project_id": project_body["id"],
            "status": "draft",
            "confidence": "low",
            "limitations": "One conversation. No frequency claim is possible.",
            "segments": ["household_buyer"],
            "evidence_ids": [quote_body["id"]],
        },
    )
    assert insight.status_code == 201, insight.text
    insight_body = insight.json()
    assert insight_body["evidence_count"] == 1
    assert insight_body["evidence_warning"], "thin evidence must be flagged"

    # 9. A decision is recorded against the insight.
    decision = seeded.post(
        "/api/v1/decisions",
        json={
            "title": "Test a two-person household messaging variant",
            "business_function": "product_category",
            "problem_statement": "The team assumes one buyer makes the repeat decision in shared households.",
            "description": "Build a small messaging variant that addresses both adults and test it with recruiters.",
            "rationale": "One household conversation contradicted the single-buyer assumption.",
            "limitations": "Single conversation; this is a hypothesis to test, not a conclusion.",
            "project_id": project_body["id"],
            "insight_ids": [insight_body["id"]],
            "status": "proposed",
        },
    )
    assert decision.status_code == 201, decision.text
    decision_body = decision.json()
    assert decision_body["insight_count"] == 1
    # A single linked insight is still a thin evidence base, and the API says so.
    assert "thin" in (decision_body["evidence_warning"] or "").lower()

    # 10. An action is assigned with an owner and a due date.
    action = seeded.post(
        f"/api/v1/decisions/{decision_body['id']}/actions",
        json={
            "title": "Draft the two-person household messaging variant",
            "description": "Owner drafts copy and books a review with the category lead.",
            "owner_id": decision_body["owner_id"],
            "due_date": str(date.today() + timedelta(days=10)),
            "priority": "medium",
        },
    )
    assert action.status_code == 201, action.text
    action_body = action.json()
    assert action_body["decision"]["id"] == decision_body["id"]

    # 11. The action is progressed.
    progressed = seeded.patch(f"/api/v1/actions/{action_body['id']}", json={"status": "in_progress"})
    assert progressed.status_code == 200
    assert progressed.json()["status"] == "in_progress"

    # 12. Everything is findable later, with its provenance intact.
    search = seeded.get("/api/v1/search", params={"q": "household decision"}).json()
    found_types = {group["entity_type"] for group in search["groups"]}
    assert "insight" in found_types

    detail = seeded.get(f"/api/v1/insights/{insight_body['id']}").json()
    assert detail["evidence"][0]["id"] == quote_body["id"]
    assert detail["evidence"][0]["provenance"] == quote_body["provenance"]
    assert detail["decisions"][0]["id"] == decision_body["id"]

    decision_detail = seeded.get(f"/api/v1/decisions/{decision_body['id']}").json()
    assert decision_detail["actions"][0]["status"] == "in_progress"
    assert any(entry["verb"] == "created" for entry in decision_detail["history"])

    dashboard = seeded.get("/api/v1/dashboard").json()
    assert dashboard["open_actions"] >= 1
    assert dashboard["response_rate"]["denominator"] >= 1
