"""Contract and rule tests for the API."""

from datetime import date, timedelta


def test_health_reports_ok(seeded):
    response = seeded.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["demo_mode"] is True
    assert body["seeded"] is True


def test_dashboard_numbers_are_derived_not_hardcoded(seeded):
    dashboard = seeded.get("/api/v1/dashboard").json()
    projects = seeded.get("/api/v1/projects").json()["items"]
    active = [p for p in projects if p["status"] not in ("completed", "archived")]
    assert dashboard["active_projects"] == len(active)

    recruitment = seeded.get("/api/v1/recruitment").json()["items"]
    invited = [r for r in recruitment if r["invited_at"]]
    responded = [r for r in recruitment if r["responded_at"]]
    assert dashboard["response_rate"]["denominator"] == len(invited)
    assert dashboard["response_rate"]["numerator"] == len(responded)
    assert dashboard["response_rate"]["definition"]

    evidence = seeded.get("/api/v1/evidence").json()["items"]
    assert sum(p["evidence"] for p in dashboard["segments"]) == len(evidence)


def test_project_create_and_read(seeded):
    payload = {
        "name": "Delivery experience follow-up",
        "objective": "Understand what customers expect after a delivery exception is resolved.",
        "description": "Created by an API test.",
        "status": "planning",
        "priority": "high",
        "business_functions": ["customer_experience", "operations"],
        "target_segments": ["lapsed_buyer"],
        "start_date": str(date.today()),
        "deadline": str(date.today() + timedelta(days=20)),
        "questions": [{"text": "What happens after a support ticket is closed?"}],
    }
    created = seeded.post("/api/v1/projects", json=payload)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "planning"
    assert len(body["questions"]) == 1
    assert body["counts"]["participants"] == 0

    fetched = seeded.get(f"/api/v1/projects/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == payload["name"]


def test_project_validation_rejects_bad_dates_and_short_names(seeded):
    bad_dates = seeded.post(
        "/api/v1/projects",
        json={
            "name": "Backwards dates",
            "objective": "An objective that is long enough to pass validation.",
            "start_date": str(date.today()),
            "deadline": str(date.today() - timedelta(days=5)),
        },
    )
    assert bad_dates.status_code == 422
    assert bad_dates.json()["error"]["code"] == "validation_error"

    short_name = seeded.post(
        "/api/v1/projects",
        json={"name": "ab", "objective": "An objective that is long enough to pass validation."},
    )
    assert short_name.status_code == 422
    fields = [d["field"] for d in short_name.json()["error"]["details"]]
    assert "name" in fields


def test_unknown_ids_return_404_envelope(seeded):
    for path in (
        "/api/v1/projects/does-not-exist",
        "/api/v1/participants/does-not-exist",
        "/api/v1/interviews/does-not-exist",
        "/api/v1/insights/does-not-exist",
        "/api/v1/decisions/does-not-exist",
        "/api/v1/evidence/does-not-exist",
    ):
        response = seeded.get(path)
        assert response.status_code == 404, path
        body = response.json()
        assert body["error"]["code"] == "not_found"
        assert "does not exist" in body["error"]["message"]


def test_participant_creation_never_stores_contact_details(seeded):
    response = seeded.post(
        "/api/v1/participants",
        json={
            "display_name": "Test Participant",
            "segment": "repeat_buyer",
            "purchase_frequency": "Every 2 months",
            "product_category": "Shampoo",
            "eligibility": "eligible",
            "notes": "Created by test",
            "email": "should-not-be-stored@example.test",
            "phone": "+10000000000",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"].startswith("P-")
    assert "email" not in body
    assert "phone" not in body
    # A record entered through the API is real research data, not demo data,
    # so it must not inherit the synthetic flag the seed uses.
    assert body["is_synthetic"] is False

    search = seeded.get("/api/v1/search", params={"q": "should-not-be-stored"}).json()
    assert search["total"] == 0


def test_recruitment_transitions_and_history(seeded, sample_ids):
    candidate = seeded.post(
        "/api/v1/participants",
        json={"display_name": "Recruitment Test Buyer", "segment": "lapsed_buyer", "eligibility": "eligible"},
    ).json()

    created = seeded.post(
        "/api/v1/recruitment",
        json={"project_id": sample_ids["project_id"], "participant_ids": [candidate["id"]]},
    )
    assert created.status_code == 201, created.text
    record = created.json()["created"][0]
    assert record["stage"] == "selected"

    duplicate = seeded.post(
        "/api/v1/recruitment",
        json={"project_id": sample_ids["project_id"], "participant_ids": [candidate["id"]]},
    )
    assert duplicate.status_code == 409

    invited = seeded.patch(f"/api/v1/recruitment/{record['id']}", json={"stage": "invited"})
    assert invited.status_code == 200, invited.text
    assert invited.json()["stage"] == "invited"
    assert invited.json()["invited_at"] is not None

    illegal = seeded.patch(f"/api/v1/recruitment/{record['id']}", json={"stage": "completed"})
    assert illegal.status_code == 400
    assert illegal.json()["error"]["code"] == "rule_violation"
    assert "responded" in illegal.json()["error"]["details"]["allowed"]

    history = seeded.get(f"/api/v1/recruitment/{record['id']}").json()["events"]
    assert [event["to_stage"] for event in history][0] == "invited"
    assert len(history) >= 2


def test_recruitment_reports_segment_gap(seeded, sample_ids):
    response = seeded.get("/api/v1/recruitment", params={"project_id": sample_ids["project_id"]})
    assert response.status_code == 200
    body = response.json()
    assert body["warnings"], "a small sample must produce a representation warning"
    assert any("representative" in w for w in body["warnings"])


def test_interview_lifecycle_and_recording_consent_gate(seeded, sample_ids):
    created = seeded.post(
        "/api/v1/interviews",
        json={
            "project_id": sample_ids["project_id"],
            "participant_id": sample_ids["participant_id"],
            "title": "Consent gate interview",
            "use_default_guide": True,
            "status": "planned",
        },
    )
    assert created.status_code == 201, created.text
    interview = created.json()
    assert len(interview["guide"]) >= 4
    assert interview["recording_enabled"] is False

    blocked = seeded.post(f"/api/v1/interviews/{interview['id']}/recording", json={"enabled": True})
    assert blocked.status_code == 400
    assert "consent" in blocked.json()["error"]["message"].lower()

    consent = seeded.post(
        f"/api/v1/interviews/{interview['id']}/consent",
        json={"consent_type": "recording", "status": "granted", "note": "Simulated verbal consent."},
    )
    assert consent.status_code == 200
    allowed = seeded.post(f"/api/v1/interviews/{interview['id']}/recording", json={"enabled": True})
    assert allowed.status_code == 200

    illegal = seeded.patch(f"/api/v1/interviews/{interview['id']}", json={"status": "completed"})
    assert illegal.status_code == 400
    assert illegal.json()["error"]["details"]["allowed"] == ["cancelled", "scheduled"]

    scheduled = seeded.patch(f"/api/v1/interviews/{interview['id']}", json={"status": "scheduled"})
    assert scheduled.status_code == 200
    completed = seeded.patch(
        f"/api/v1/interviews/{interview['id']}",
        json={"status": "completed", "notes": "Notes captured.", "change_note": "Completed after the call."},
    )
    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None


def test_evidence_without_provenance_is_flagged(seeded, sample_ids):
    response = seeded.post(
        "/api/v1/evidence",
        json={
            "interview_id": sample_ids["interview_id"],
            "evidence_type": "verbatim_quote",
            "content": "A statement with no source.",
            "interpretation": "Should not be treated as verified.",
            "confidence": "high",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["provenance_status"] == "missing"
    assert body["review_status"] == "flagged"
    assert body["confidence"] == "low", "unattributed evidence must not keep high confidence"
    assert body["is_verified_source"] is False
    assert "do not treat this as verified evidence" in body["provenance_warning"].lower()


def test_evidence_with_provenance_is_verified(seeded, sample_ids):
    response = seeded.post(
        "/api/v1/evidence",
        json={
            "interview_id": sample_ids["interview_id"],
            "evidence_type": "observation",
            "content": "Participant checked the bottle label before answering.",
            "provenance": "Interview note 3, timestamp 00:04:12 (synthetic)",
            "confidence": "medium",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["is_verified_source"] is True
    assert body["provenance_warning"] is None


def test_insight_requires_evidence_before_validation(seeded, sample_ids):
    created = seeded.post(
        "/api/v1/insights",
        json={
            "title": "A hypothesis without evidence",
            "summary": "This insight exists to prove the validation rule is enforced by the API.",
            "project_id": sample_ids["project_id"],
            "status": "draft",
        },
    )
    assert created.status_code == 201, created.text
    insight = created.json()
    assert insight["evidence_warning"].startswith("No evidence is linked yet")

    blocked = seeded.patch(f"/api/v1/insights/{insight['id']}", json={"status": "validated_internal"})
    assert blocked.status_code == 400
    assert "without at least one linked evidence" in blocked.json()["error"]["message"]

    before_validation = seeded.post(
        "/api/v1/insights",
        json={
            "title": "Premature validation attempt",
            "summary": "Creating something already validated should be rejected when no evidence is attached.",
            "status": "validated_internal",
        },
    )
    assert before_validation.status_code == 400

    evidence = seeded.post(
        "/api/v1/evidence",
        json={
            "interview_id": sample_ids["interview_id"],
            "content": "A quote used to support the hypothesis.",
            "provenance": "Interview note 5 (synthetic)",
        },
    ).json()
    linked = seeded.post(
        f"/api/v1/insights/{insight['id']}/evidence",
        json={"evidence_id": evidence["id"], "role": "supporting"},
    )
    assert linked.status_code == 201, linked.text
    duplicate = seeded.post(
        f"/api/v1/insights/{insight['id']}/evidence",
        json={"evidence_id": evidence["id"], "role": "supporting"},
    )
    assert duplicate.status_code == 409

    validated = seeded.patch(f"/api/v1/insights/{insight['id']}", json={"status": "validated_internal"})
    assert validated.status_code == 200
    assert validated.json()["validated_at"] is not None


def test_decision_without_evidence_is_warned_not_hidden(seeded):
    created = seeded.post(
        "/api/v1/decisions",
        json={
            "title": "An internal decision with no research behind it",
            "business_function": "operations",
            "problem_statement": "Recorded to demonstrate the honest labelling of unevidenced decisions.",
            "description": "This is an internal judgement call, not an evidence-based decision.",
            "status": "proposed",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["evidence_count"] == 0
    assert body["insight_count"] == 0
    assert "not linked to any customer evidence" in body["evidence_warning"].lower()

    listed = seeded.get("/api/v1/decisions", params={"has_evidence": "false"}).json()
    assert any(d["id"] == body["id"] for d in listed["items"])
    assert listed["unevidenced"] >= 1


def test_decision_links_and_action_creation(seeded, sample_ids):
    insights = seeded.get("/api/v1/insights").json()["items"]
    insight = insights[0]
    decision = seeded.post(
        "/api/v1/decisions",
        json={
            "title": "Link test decision",
            "business_function": "growth",
            "problem_statement": "Link a decision to an existing insight through the API.",
            "description": "Created by the automated test suite to verify linking and action creation.",
            "insight_ids": [insight["id"]],
        },
    )
    assert decision.status_code == 201, decision.text
    body = decision.json()
    assert body["insight_count"] == 1
    assert len(body["insights"]) == 1

    action = seeded.post(
        f"/api/v1/decisions/{body['id']}/actions",
        json={
            "title": "Test follow-up action",
            "owner_id": sample_ids["user_id"],
            "due_date": str(date.today() + timedelta(days=3)),
            "priority": "high",
        },
    )
    assert action.status_code == 201, action.text
    action_body = action.json()
    assert action_body["status"] == "not_started"
    assert action_body["is_overdue"] is False

    completed = seeded.patch(f"/api/v1/actions/{action_body['id']}", json={"status": "completed"})
    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None

    overdue = seeded.get("/api/v1/actions", params={"overdue_only": "true"}).json()
    assert overdue["overdue"] == len(overdue["items"])


def test_decision_status_transitions_are_validated(seeded):
    decision = seeded.post(
        "/api/v1/decisions",
        json={
            "title": "Transition test decision",
            "business_function": "brand_marketing",
            "problem_statement": "Verify the decision state machine.",
            "description": "Created by the automated test suite.",
            "status": "proposed",
        },
    ).json()
    accepted = seeded.patch(f"/api/v1/decisions/{decision['id']}", json={"status": "accepted"})
    assert accepted.status_code == 200
    invalid = seeded.patch(f"/api/v1/decisions/{decision['id']}", json={"status": "under_review"})
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "rule_violation"


def test_search_finds_insight_and_related_work(seeded):
    response = seeded.get("/api/v1/search", params={"q": "shampoo"})
    assert response.status_code == 200
    body = response.json()
    types = {group["entity_type"] for group in body["groups"]}
    assert "insight" in types
    assert "evidence" in types
    assert body["total"] >= 3

    insight = seeded.get("/api/v1/insights").json()["items"][0]
    related = seeded.get(f"/api/v1/insights/{insight['id']}/related")
    assert related.status_code == 200
    assert isinstance(related.json(), list)


def test_analytics_labels_metric_basis(seeded):
    body = seeded.get("/api/v1/analytics").json()
    bases = {metric["basis"] for metric in body["metrics"]}
    assert {"calculated", "observed", "pending_baseline"} <= bases
    reuse = next(m for m in body["metrics"] if m["key"] == "research_reuse_rate")
    assert reuse["basis"] == "calculated"
    cooperation = next(m for m in body["metrics"] if m["key"] == "coordination_time")
    assert cooperation["display"] == "Not measured"
    assert body["measurement_gaps"]


def test_csv_export_is_labelled_synthetic(seeded):
    response = seeded.get("/api/v1/exports/participants.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["X-Data-Origin"] == "synthetic-demo-data"
    assert response.headers["X-Row-Count"]
    assert "attachment; filename=" in response.headers["content-disposition"]
    lines = response.text.strip().splitlines()
    assert lines[0].lstrip("\ufeff").endswith("data_origin,exported_at")
    assert ",synthetic," in lines[1]

    unknown = seeded.get("/api/v1/exports/nope.csv")
    assert unknown.status_code == 400
    assert "error" in unknown.json()


def test_demo_reset_requires_confirmation_phrase(seeded):
    blocked = seeded.post("/api/v1/demo/reset", json={"confirm": True, "phrase": "please"})
    assert blocked.status_code == 400
    assert blocked.json()["error"]["details"]["field"] == "phrase"

    reset = seeded.post("/api/v1/demo/reset", json={"confirm": True, "phrase": "RESET"})
    assert reset.status_code == 200
    counts = reset.json()["counts"]
    assert counts["projects"] >= 5
    assert counts["participants"] >= 10


def test_session_directory_is_demo_entry_not_an_identity_provider(seeded):
    body = seeded.get("/api/v1/session").json()
    assert body["demo_mode"] is True
    # The directory must state that a real session is issued and enforced, and
    # that the picker is still not a substitute for an identity provider.
    assert "server-side session" in body["notice"]
    assert "identity provider" in body["notice"]
    roles = {user["role"] for user in body["users"]}
    assert {"ceo", "researcher", "business_owner", "cx", "admin"} <= roles
