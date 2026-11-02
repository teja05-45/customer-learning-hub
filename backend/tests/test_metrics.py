"""Metric definitions and dashboard/analytics agreement.

The product's central claim is that its numbers come from records. These tests
mutate the record set and check that every derived counter moves in the expected
direction, and that the dashboard and analytics screens never disagree about the
same quantity.
"""

from datetime import date, timedelta


def _dash(client) -> dict:
    return client.get("/api/v1/dashboard").json()


def _analytics(client) -> dict:
    return client.get("/api/v1/analytics").json()


def _metric(analytics: dict, key: str) -> dict:
    return next(metric for metric in analytics["metrics"] if metric["key"] == key)


def _pct(display: str) -> tuple[int, int, int]:
    percent, fraction = display.split("% (", 1)
    numerator, denominator = fraction.rstrip(")").split("/", 1)
    return int(percent), int(numerator), int(denominator)


def _evidence_count(client) -> int:
    return client.get("/api/v1/evidence").json()["total"]


def _interview_project(client, interview_id: str) -> str:
    """Evidence may only be linked inside the project that produced it."""
    return client.get(f"/api/v1/interviews/{interview_id}").json()["project_id"]


def _new_evidence(client, interview_id: str, content: str) -> dict:
    response = client.post(
        "/api/v1/evidence",
        json={
            "interview_id": interview_id,
            "evidence_type": "verbatim_quote",
            "content": content,
            "provenance": "Metrics test transcript, synthetic",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _new_insight(client, project_id: str, evidence_id: str, title: str) -> dict:
    response = client.post(
        "/api/v1/insights",
        json={
            "title": title,
            "summary": "A metric test insight with one piece of linked, attributed evidence behind it.",
            "project_id": project_id,
            "confidence": "low",
            "limitations": "One synthetic conversation.",
            "evidence_ids": [evidence_id],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _new_decision(client, insight_id: str, title: str) -> dict:
    response = client.post(
        "/api/v1/decisions",
        json={
            "title": title,
            "business_function": "product_category",
            "problem_statement": "Metric consistency must be observable from the decision register.",
            "description": "A decision created by the metrics test suite to move the derived counters.",
            "insight_ids": [insight_id],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_dashboard_and_analytics_report_the_same_quantities(seeded):
    """The two screens must agree on response rate, interviews and decisions."""
    dashboard = _dash(seeded)
    analytics = _analytics(seeded)

    _, numerator, denominator = _pct(_metric(analytics, "invitation_response_rate")["display"])
    assert numerator == dashboard["response_rate"]["numerator"]
    assert denominator == dashboard["response_rate"]["denominator"]

    assert _metric(analytics, "interviews_completed")["display"] == str(dashboard["interviews_completed"])

    _, decision_num, decision_den = _pct(_metric(analytics, "evidence_linked_decisions")["display"])
    assert decision_num == dashboard["decisions_with_evidence"]
    assert decision_den == dashboard["decisions_total"]

    _, evidence_num, insight_total = _pct(_metric(analytics, "findings_with_evidence")["display"])
    assert insight_total == dashboard["learning"]["findings_total"]
    assert evidence_num == dashboard["learning"]["findings_with_evidence"]


def test_new_evidence_insight_and_decision_move_the_counters(seeded, sample_ids):
    """Counters are derived from rows, not from a seeded constant."""
    before_dashboard = _dash(seeded)
    before_analytics = _analytics(seeded)
    before_evidence = _evidence_count(seeded)

    evidence = _new_evidence(seeded, sample_ids["interview_id"], "Metrics quote one about shampoo packaging.")
    insight = _new_insight(
        seeded,
        _interview_project(seeded, sample_ids["interview_id"]),
        evidence["id"],
        "Metrics insight one",
    )
    decision = _new_decision(seeded, insight["id"], "Metrics decision one")

    after_dashboard = _dash(seeded)
    after_analytics = _analytics(seeded)

    assert _evidence_count(seeded) == before_evidence + 1
    assert sum(point["evidence"] for point in after_dashboard["segments"]) == before_evidence + 1
    assert after_dashboard["learning"]["findings_total"] == before_dashboard["learning"]["findings_total"] + 1
    assert (
        after_dashboard["learning"]["findings_with_evidence"]
        == before_dashboard["learning"]["findings_with_evidence"] + 1
    )
    assert after_dashboard["decisions_total"] == before_dashboard["decisions_total"] + 1
    assert (
        after_dashboard["decisions_with_evidence"] == before_dashboard["decisions_with_evidence"] + 1
    )
    assert after_dashboard["insights_awaiting_review"] == before_dashboard["insights_awaiting_review"] + 1

    _, numerator, denominator = _pct(_metric(after_analytics, "evidence_linked_decisions")["display"])
    assert numerator == after_dashboard["decisions_with_evidence"]
    assert denominator == after_dashboard["decisions_total"]

    # The new decision is visible and evidence-backed wherever it is read.
    detail = seeded.get(f"/api/v1/decisions/{decision['id']}").json()
    assert detail["insight_count"] == 1
    # One linked insight is deliberately still called thin rather than sufficient.
    assert "thin" in (detail["evidence_warning"] or "").lower()

    assert _metric(after_analytics, "evidence_captured")["display"].startswith(str(_evidence_count(seeded)))


def test_overdue_actions_are_derived_and_clear_on_completion(seeded, sample_ids):
    """Overdue is computed from the due date and status, never stored."""
    before = _dash(seeded)
    overdue_before = seeded.get("/api/v1/actions", params={"overdue_only": "true"}).json()

    action = seeded.post(
        "/api/v1/actions",
        json={
            "title": "Metrics overdue action",
            "owner_id": sample_ids["user_id"],
            "due_date": str(date.today() - timedelta(days=2)),
            "priority": "high",
        },
    )
    assert action.status_code == 201, action.text
    action = action.json()
    assert action["is_overdue"] is True

    after = _dash(seeded)
    assert after["overdue_actions"] == before["overdue_actions"] + 1
    overdue_after = seeded.get("/api/v1/actions", params={"overdue_only": "true"}).json()
    assert overdue_after["total"] == overdue_before["total"] + 1
    assert overdue_after["overdue"] == len(overdue_after["items"])

    completed = seeded.patch(f"/api/v1/actions/{action['id']}", json={"status": "completed"})
    assert completed.status_code == 200
    assert completed.json()["is_overdue"] is False

    settled = _dash(seeded)
    assert settled["overdue_actions"] == before["overdue_actions"]


def test_research_reuse_requires_repeat_use(seeded, sample_ids):
    """One immediate decision is use, not reuse; a second decision is reuse."""
    evidence = _new_evidence(seeded, sample_ids["interview_id"], "Reuse quote about bottle size confusion.")
    insight = _new_insight(
        seeded,
        _interview_project(seeded, sample_ids["interview_id"]),
        evidence["id"],
        "Reuse definition insight",
    )

    before = _analytics(seeded)
    assert seeded.get(f"/api/v1/insights/{insight['id']}").json()["reuse_flag"] is False

    _new_decision(seeded, insight["id"], "Reuse decision one")
    after_one = _analytics(seeded)
    assert seeded.get(f"/api/v1/insights/{insight['id']}").json()["reuse_flag"] is False

    _new_decision(seeded, insight["id"], "Reuse decision two")
    assert seeded.get(f"/api/v1/insights/{insight['id']}").json()["reuse_flag"] is True

    after_two = _analytics(seeded)
    _, reused_before, total_before = _pct(_metric(before, "research_reuse_rate")["display"])
    _, reused_after, total_after = _pct(_metric(after_two, "research_reuse_rate")["display"])
    # The insight already existed in the "before" snapshot, so only the numerator moves.
    assert total_after == total_before
    assert reused_after == reused_before + 1
    assert _pct(_metric(after_one, "research_reuse_rate")["display"])[0] == _pct(
        _metric(before, "research_reuse_rate")["display"]
    )[0]

    row = next(item for item in after_two["reuse_detail"] if item["insight_id"] == insight["id"])
    assert row["decisions"] == 2
    assert row["reused"] is True
    assert "Reuse decision two" in row["decision_titles"]


def test_segment_totals_reconcile_with_the_participant_directory(seeded):
    """Segment charts must add up to the directory they come from."""
    dashboard = _dash(seeded)
    directory = seeded.get("/api/v1/participants", params={"page_size": 100}).json()
    assert sum(point["participants"] for point in dashboard["segments"]) == directory["total"]

    analytics = _analytics(seeded)
    assert sum(point["participants"] for point in analytics["segment_distribution"]) == directory["total"]
