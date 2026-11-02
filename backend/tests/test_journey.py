"""The complete customer-learning journey, driven through the public API.

This is the acceptance test for the product's core claim: a business question
becomes a project, a project produces interviews, interviews produce evidence
with provenance, evidence produces an insight, and an insight reaches a decision
with named follow-up work. It also checks that the numbers the dashboard and
analytics screens show are derived from the records created here rather than
from anything pre-computed.

Every record is synthetic. The test resets the demo dataset first so it is
repeatable and does not depend on the order of other tests.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest


ADMIN_EMAIL = "arjun.demo@example.test"
RESEARCHER_EMAIL = "priya.demo@example.test"


def _reset(client) -> None:
    # Resetting replaces every user, so sign in as the administrator first and
    # then re-authenticate as the researcher who runs the journey.
    admin_login = client.post(
        "/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": "demo-password"}
    )
    assert admin_login.status_code == 200, admin_login.text
    response = client.post("/api/v1/demo/reset", json={"confirm": True, "phrase": "RESET"})
    assert response.status_code == 200, response.text
    login = client.post(
        "/api/v1/auth/login", json={"email": RESEARCHER_EMAIL, "password": "demo-password"}
    )
    assert login.status_code == 200, login.text


def _users(client) -> dict[str, dict]:
    body = client.get("/api/v1/session").json()
    return {user["role"]: user for user in body["users"]}


def _headers(user: dict) -> dict[str, str]:
    """Identity travels in the server-issued session cookie, not a header.

    The argument is kept so the journey reads as "this user acts here"; the
    role is enforced by the API against the signed-in session.
    """
    assert user, "a real user must be selected for this step"
    return {}


def _metric(analytics: dict, key: str) -> dict:
    return next(metric for metric in analytics["metrics"] if metric["key"] == key)


def _parse_pct(display: str) -> tuple[int, int, int]:
    """Read the ``42% (6/14)`` display form the analytics metrics use."""
    percent, fraction = display.split("% (", 1)
    numerator, denominator = fraction.rstrip(")").split("/", 1)
    return int(percent), int(numerator), int(denominator)


@pytest.fixture()
def journey(client):
    """Run the full journey once and return every record created along the way."""
    _reset(client)
    users = _users(client)
    researcher = users["researcher"]
    owner = users["business_owner"]
    headers = _headers(researcher)

    # 1-3. A researcher creates a project and defines the business question.
    project_response = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "name": "Why are shampoo buyers not purchasing again?",
            "objective": "Understand what stops a first shampoo purchase from becoming a repeat purchase.",
            "description": "Synthetic discovery study used by the acceptance test.",
            "status": "planning",
            "priority": "high",
            "methodology": "Moderated interviews",
            "business_functions": ["product_category", "growth"],
            "target_segments": [
                "first_time_buyer",
                "repeat_buyer",
                "household_buyer",
                "lapsed_buyer",
            ],
            "start_date": date.today().isoformat(),
            "deadline": (date.today() + timedelta(days=21)).isoformat(),
            "questions": [
                {"text": "What did buyers expect the first time they used the shampoo?"},
                {"text": "What made a second purchase feel worth it or not worth it?"},
            ],
        },
    )
    assert project_response.status_code == 201, project_response.text
    project = project_response.json()
    assert len(project["questions"]) == 2

    # 4-5. Synthetic participants, one per target segment.
    participant_ids: dict[str, str] = {}
    for segment in ("first_time_buyer", "repeat_buyer", "household_buyer", "lapsed_buyer"):
        created = client.post(
            "/api/v1/participants",
            headers=headers,
            json={
                "display_name": f"Synthetic {segment.replace('_', ' ')}",
                "segment": segment,
                "purchase_frequency": "One order in the last 90 days",
                "orders_count": 1,
                "product_category": "Hair care",
                "eligibility": "eligible",
                "contact_route": "Controlled Ops outreach (simulated)",
            },
        )
        assert created.status_code == 201, created.text
        participant_ids[segment] = created.json()["id"]

    # 6. Recruitment records are created for the project.
    recruitment = client.post(
        "/api/v1/recruitment",
        headers=headers,
        json={
            "project_id": project["id"],
            "participant_ids": list(participant_ids.values()),
            "next_action": "Confirm eligibility, then invite",
        },
    )
    assert recruitment.status_code == 201, recruitment.text
    records = {item["participant_id"]: item for item in recruitment.json()["created"]}
    assert len(records) == 4
    assert all(item["stage"] == "selected" for item in records.values())

    # 7. Invitations and responses are recorded, one stage at a time.
    for participant_id, record in records.items():
        invited = client.patch(
            f"/api/v1/recruitment/{record['id']}",
            headers=headers,
            json={"stage": "invited", "note": "Invitation sent (simulated)."},
        )
        assert invited.status_code == 200, invited.text
        assert invited.json()["invited_at"] is not None

    focus_id = participant_ids["first_time_buyer"]
    focus_record = records[focus_id]
    for stage in ("responded", "scheduled"):
        moved = client.patch(
            f"/api/v1/recruitment/{focus_record['id']}",
            headers=headers,
            json={"stage": stage},
        )
        assert moved.status_code == 200, moved.text

    # 8-9. An interview is scheduled, which must not lose the recruitment link.
    scheduled_at = datetime.now(timezone.utc) - timedelta(hours=2)
    interview_response = client.post(
        "/api/v1/interviews",
        headers=headers,
        json={
            "project_id": project["id"],
            "participant_id": focus_id,
            "title": "First shampoo purchase follow-up",
            "scheduled_at": scheduled_at.isoformat(),
            "duration_minutes": 30,
            "status": "scheduled",
            "use_default_guide": True,
        },
    )
    assert interview_response.status_code == 201, interview_response.text
    interview = interview_response.json()
    assert interview["recruitment_id"] == focus_record["id"]
    assert len(interview["guide"]) > 0

    # The participant must have granted participation consent before the
    # conversation is written up.
    consent = client.post(
        f"/api/v1/interviews/{interview['id']}/consent",
        headers=headers,
        json={"consent_type": "participation", "status": "granted", "note": "Synthetic consent."},
    )
    assert consent.status_code == 200, consent.text
    assert consent.json()["consent_status"] == "granted"

    # 10. Completing the interview must close the recruitment stage too.
    completed = client.patch(
        f"/api/v1/interviews/{interview['id']}",
        headers=headers,
        json={"status": "completed", "summary": "Participant described a scent expectation gap."},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"

    recruitment_after = client.get(f"/api/v1/recruitment/{focus_record['id']}").json()
    assert recruitment_after["stage"] == "completed"
    stages = [event["to_stage"] for event in recruitment_after["events"]]
    assert {"selected", "invited", "responded", "scheduled", "completed"} <= set(stages)

    # 11-13. A verbatim quote keeps its provenance; the interpretation is a
    # separate record; contradictory evidence is preserved rather than removed.
    quote = client.post(
        "/api/v1/evidence",
        headers=headers,
        json={
            "interview_id": interview["id"],
            "evidence_type": "verbatim_quote",
            "content": "It smelled different from the bottle I used in the shop, so I did not buy it again.",
            "customer_context": "Answering: what made a second purchase feel worth it?",
            "provenance": f"{interview['code']} · 12:04 into the conversation",
            "confidence": "medium",
        },
    )
    assert quote.status_code == 201, quote.text
    quote = quote.json()
    assert quote["provenance_status"] == "recorded"
    assert quote["is_verified_source"] is True
    assert quote["evidence_type"] == "verbatim_quote"

    interpretation = client.post(
        "/api/v1/evidence",
        headers=headers,
        json={
            "interview_id": interview["id"],
            "evidence_type": "researcher_interpretation",
            "content": "The expectation gap between in-store scent and home use may drive non-repurchase.",
            "provenance": f"{interview['code']} · researcher note",
        },
    )
    assert interpretation.status_code == 201, interpretation.text
    interpretation = interpretation.json()

    unattributed = client.post(
        "/api/v1/evidence",
        headers=headers,
        json={
            "interview_id": interview["id"],
            "evidence_type": "open_question",
            "content": "Is the in-store tester the same formula as the retail bottle?",
        },
    )
    assert unattributed.status_code == 201, unattributed.text
    unattributed = unattributed.json()
    assert unattributed["provenance_status"] == "missing"
    assert unattributed["review_status"] == "flagged"
    assert unattributed["is_verified_source"] is False
    assert unattributed["provenance_warning"]

    contradictory = client.post(
        "/api/v1/evidence",
        headers=headers,
        json={
            "interview_id": interview["id"],
            "evidence_type": "contradictory_evidence",
            "content": "I actually repurchased because the scent lasted longer than my previous brand.",
            "provenance": f"{interview['code']} · follow-up question",
        },
    )
    assert contradictory.status_code == 201, contradictory.text
    contradictory = contradictory.json()

    # 14-15. The insight links supporting and contradictory evidence.
    insight_response = client.post(
        "/api/v1/insights",
        headers=headers,
        json={
            "title": "In-store scent expectation does not survive home use",
            "summary": (
                "First-time buyers describe a gap between the fragrance they tested in store and the "
                "product they used at home. The gap appears in their reason for not repurchasing."
            ),
            "interpretation": "The team reads this as an expectation-setting problem, not a product defect.",
            "research_question": "Why are shampoo buyers not purchasing again?",
            "project_id": project["id"],
            "confidence": "medium",
            "limitations": "Four synthetic conversations. Not representative of the customer base.",
            "segments": ["first_time_buyer", "lapsed_buyer"],
            "evidence_ids": [quote["id"], interpretation["id"]],
        },
    )
    assert insight_response.status_code == 201, insight_response.text
    insight = insight_response.json()
    assert insight["evidence_count"] == 2

    linked = client.post(
        f"/api/v1/insights/{insight['id']}/evidence",
        headers=headers,
        json={"evidence_id": contradictory["id"], "role": "contradictory"},
    )
    assert linked.status_code == 201, linked.text
    insight = linked.json()
    assert insight["supporting_count"] == 2
    assert insight["contradictory_count"] == 1

    duplicate = client.post(
        f"/api/v1/insights/{insight['id']}/evidence",
        headers=headers,
        json={"evidence_id": quote["id"], "role": "supporting"},
    )
    assert duplicate.status_code == 409

    # 16. Review: "validated for internal use" is a review decision, not a claim
    # of representativeness.
    validated = client.patch(
        f"/api/v1/insights/{insight['id']}",
        headers=headers,
        json={"status": "validated_internal"},
    )
    assert validated.status_code == 200, validated.text
    assert validated.json()["validated_at"] is not None

    # 17-18. The business owner records a decision with rationale and limits.
    decision_response = client.post(
        "/api/v1/decisions",
        headers=_headers(owner),
        json={
            "title": "Test the retail bottle fragrance before changing the formula",
            "business_function": "product_category",
            "problem_statement": "First-time shampoo buyers are not repurchasing at the expected rate.",
            "description": "Run a matched in-store and at-home fragrance trial before any reformulation.",
            "rationale": "The strongest explanation in the evidence is an expectation gap, not efficacy.",
            "limitations": "Based on four synthetic conversations; the effect may not generalise.",
            "project_id": project["id"],
            "owner_id": owner["id"],
            "decision_date": date.today().isoformat(),
            "status": "proposed",
            "evidence_sufficient": True,
            "insight_ids": [insight["id"]],
            "evidence_ids": [quote["id"]],
        },
    )
    assert decision_response.status_code == 201, decision_response.text
    decision = decision_response.json()
    assert decision["insight_count"] == 1
    assert decision["evidence_count"] == 1
    assert decision["evidence_sufficient"] is True

    # 19-20. Follow-up work gets an owner, a due date and a status.
    action_response = client.post(
        f"/api/v1/decisions/{decision['id']}/actions",
        headers=_headers(owner),
        json={
            "title": "Run the matched fragrance trial",
            "description": "Recruit eight first-time buyers for a two-week at-home trial.",
            "owner_id": owner["id"],
            "due_date": (date.today() - timedelta(days=1)).isoformat(),
            "priority": "high",
            "status": "not_started",
        },
    )
    assert action_response.status_code == 201, action_response.text
    action = action_response.json()
    assert action["owner"]["id"] == owner["id"]
    assert action["is_overdue"] is True

    for status in ("in_progress", "blocked", "in_progress", "completed"):
        updated = client.patch(
            f"/api/v1/actions/{action['id']}",
            headers=_headers(owner),
            json={"status": status},
        )
        assert updated.status_code == 200, updated.text
    action = updated.json()
    assert action["status"] == "completed"
    assert action["completed_at"] is not None
    assert action["is_overdue"] is False

    return {
        "project": project,
        "participants": participant_ids,
        "recruitment": records,
        "interview": interview,
        "quote": quote,
        "contradictory": contradictory,
        "insight": insight,
        "decision": decision,
        "action": action,
        "owner": owner,
        "researcher": researcher,
    }


def test_full_journey_produces_traceable_records(seeded, journey):
    """Every step of the journey leaves a record linked to its source."""
    client = seeded
    insight = client.get(f"/api/v1/insights/{journey['insight']['id']}").json()
    assert {item["id"] for item in insight["evidence"]} >= {
        journey["quote"]["id"],
        journey["contradictory"]["id"],
    }

    decision = client.get(f"/api/v1/decisions/{journey['decision']['id']}").json()
    assert decision["insights"][0]["id"] == journey["insight"]["id"]
    assert decision["actions"][0]["id"] == journey["action"]["id"]

    # Provenance travels all the way down: the quote still names its interview
    # and project when read from the decision side.
    quote = next(item for item in decision["evidence"] if item["id"] == journey["quote"]["id"])
    assert quote["interview"]["label"] == journey["interview"]["code"]
    assert quote["project"]["id"] == journey["project"]["id"]


def test_recruitment_history_survives_list_view(seeded, journey):
    """The pipeline list must carry stage history, not only the current stage."""
    listing = seeded.get("/api/v1/recruitment").json()
    record = next(
        item for item in listing["items"] if item["id"] == journey["recruitment"][
            journey["participants"]["first_time_buyer"]
        ]["id"]
    )
    assert record["events"], "the pipeline list must return the stage timeline"
    assert record["events"][0]["to_stage"] == "completed"


def test_dashboard_and_analytics_agree(seeded, journey):
    """The two screens must report the same numbers for the same records."""
    dashboard = seeded.get("/api/v1/dashboard").json()
    analytics = seeded.get("/api/v1/analytics").json()

    response_rate = dashboard["response_rate"]
    assert response_rate["numerator"] >= 1
    assert response_rate["denominator"] >= response_rate["numerator"]
    _, numerator, denominator = _parse_pct(
        _metric(analytics, "invitation_response_rate")["display"]
    )
    assert (numerator, denominator) == (response_rate["numerator"], response_rate["denominator"])

    interviews_completed = dashboard["interviews_completed"]
    assert _metric(analytics, "interviews_completed")["display"] == str(interviews_completed)

    assert dashboard["decisions_total"] >= 1
    _, decision_num, decision_den = _parse_pct(
        _metric(analytics, "evidence_linked_decisions")["display"]
    )
    assert decision_num == dashboard["decisions_with_evidence"]
    assert decision_den == dashboard["decisions_total"]

    # Every insight in the workspace has evidence in this journey, so the
    # denominator must equal the insight count shown by the reuse table.
    _, with_evidence, insight_total = _parse_pct(
        _metric(analytics, "findings_with_evidence")["display"]
    )
    assert insight_total == len(analytics["reuse_detail"])
    assert with_evidence == insight_total
    assert journey["insight"]["id"] in {row["insight_id"] for row in analytics["reuse_detail"]}


def test_dashboard_metrics_reflect_new_records(seeded, journey):
    """A new project, interview and action must move the derived counters."""
    dashboard = seeded.get("/api/v1/dashboard").json()
    project_ids = {item["id"] for item in dashboard["projects"]}
    assert journey["project"]["id"] in project_ids
    assert dashboard["interviews_completed"] >= 1
    assert dashboard["participants_contacted"] >= 4
    # The journey's follow-up was completed, so it must not still be listed.
    assert journey["action"]["id"] not in {item["id"] for item in dashboard["outstanding_actions"]}
    assert dashboard["learning"]["findings_with_evidence"] >= 1
    assert dashboard["learning"]["decisions_supported"] >= 1


def test_global_search_reaches_insight_and_evidence(seeded, journey):
    """Search must find the journey's insight and expose a navigable href."""
    result = seeded.get("/api/v1/search", params={"q": "in-store scent expectation"}).json()
    insight_hits = [
        item
        for group in result["groups"]
        if group["entity_type"] == "insight"
        for item in group["items"]
    ]
    assert any(item["id"] == journey["insight"]["id"] for item in insight_hits)

    evidence_search = seeded.get("/api/v1/search", params={"q": "smelled different"}).json()
    evidence_hits = [
        item
        for group in evidence_search["groups"]
        if group["entity_type"] == "evidence"
        for item in group["items"]
    ]
    assert any(item["id"] == journey["quote"]["id"] for item in evidence_hits)
    assert all(hit["href"].startswith("/evidence/") for hit in evidence_hits)


def test_insight_rejects_evidence_from_another_project(seeded, journey):
    """Evidence is only meaningful inside the project that produced it."""
    other = seeded.post(
        "/api/v1/projects",
        json={
            "name": "Unrelated deodorant study",
            "objective": "Understand deodorant usage moments.",
            "status": "planning",
            "priority": "low",
            "target_segments": ["repeat_buyer"],
        },
    )
    assert other.status_code == 201, other.text
    other_project = other.json()

    participant = seeded.post(
        "/api/v1/participants",
        json={"display_name": "Synthetic outsider", "segment": "repeat_buyer"},
    ).json()
    interview = seeded.post(
        "/api/v1/interviews",
        json={
            "project_id": other_project["id"],
            "participant_id": participant["id"],
            "title": "Unrelated conversation",
            "status": "planned",
        },
    )
    assert interview.status_code == 201, interview.text
    foreign = seeded.post(
        "/api/v1/evidence",
        json={
            "interview_id": interview.json()["id"],
            "evidence_type": "verbatim_quote",
            "content": "I only buy deodorant when it is on offer.",
            "provenance": "unrelated conversation",
        },
    ).json()

    response = seeded.post(
        f"/api/v1/insights/{journey['insight']['id']}/evidence",
        json={"evidence_id": foreign["id"], "role": "supporting"},
    )
    assert response.status_code == 400, response.text
    assert "different research project" in response.text.lower()