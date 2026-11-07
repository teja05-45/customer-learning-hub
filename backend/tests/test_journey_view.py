"""Learning-journey board and customer profile history are derived from real records."""

from app.models import Evidence, InsightEvidence


def _project(client) -> dict:
    items = client.get("/api/v1/projects").json()["items"]
    return next(item for item in items if "shampoo" in item["name"].lower())


def test_journey_board_uses_real_records(seeded):
    project = _project(seeded)
    response = seeded.get(f"/api/v1/projects/{project['id']}/journey")
    assert response.status_code == 200, response.text
    body = response.json()

    assert [stage["key"] for stage in body["stages"]] == [
        "discovery",
        "recruitment",
        "sessions",
        "feedback",
        "evidence",
        "insights",
        "decisions",
        "actions",
        "outcomes",
    ]
    by_key = {stage["key"]: stage for stage in body["stages"]}
    assert by_key["evidence"]["count"] >= 1
    assert by_key["insights"]["count"] >= 1
    assert by_key["decisions"]["count"] >= 1
    # Cards link to the entity they describe, not to a decorative placeholder.
    first_evidence = by_key["evidence"]["items"][0]
    assert first_evidence["href"].startswith("/evidence/")
    detail = seeded.get(f"/api/v1{first_evidence['href']}").json()
    assert detail["id"] == first_evidence["id"]

    assert body["timeline"], "the timeline must contain real dates"
    ordered = [item["at"] for item in body["timeline"]]
    assert ordered == sorted(ordered)

    # A milestone in the past is not labelled upcoming just because it is an
    # outcome or a deadline.
    from datetime import date

    today = date.today().isoformat()
    for item in body["timeline"]:
        if item["at"][:10] < today and item["state"] == "upcoming":
            raise AssertionError(f"past milestone labelled upcoming: {item}")


def test_journey_flags_unmeasured_outcomes(seeded):
    project = _project(seeded)
    body = seeded.get(f"/api/v1/projects/{project['id']}/journey").json()
    outcomes = next(stage for stage in body["stages"] if stage["key"] == "outcomes")
    assert outcomes["count"] >= 1
    assert outcomes["status"] in ("in_progress", "waiting")
    assert any("outcome" in warning.lower() for warning in body["warnings"])


def test_profile_includes_feedback_history_and_insight_counts(seeded):
    participants = seeded.get("/api/v1/participants").json()["items"]
    # Ananya has an interview, a feedback record and linked evidence in the seed.
    participant = next(item for item in participants if item["display_name"] == "Ananya Rao")
    body = seeded.get(f"/api/v1/participants/{participant['id']}").json()

    assert body["feedback_history"], "feedback must appear on the customer profile"
    record = body["feedback_history"][0]
    assert record["project_name"]
    assert record["source_type"]
    assert record["research_depth"] in ("deep", "medium", "limited", "context")

    history = body["participation_history"]
    assert history
    assert any(item["insight_count"] >= 1 for item in history), (
        "an interview whose evidence supports an insight must report that insight"
    )

    # The profile does not leak another participant's feedback.
    other = next(item for item in participants if item["id"] != participant["id"])
    other_body = seeded.get(f"/api/v1/participants/{other['id']}").json()
    assert all(item["id"] != record["id"] for item in other_body["feedback_history"])

    # Verify the count came from the join, not from a hard-coded zero.
    from app.core.database import SessionLocal
    from app.models import Evidence, InsightEvidence

    db = SessionLocal()
    try:
        interview_id = next(item["interview_id"] for item in history if item["interview_id"])
        expected = (
            db.query(InsightEvidence.insight_id)
            .join(Evidence, Evidence.id == InsightEvidence.evidence_id)
            .filter(Evidence.interview_id == interview_id)
            .distinct()
            .count()
        )
        actual = next(item["insight_count"] for item in history if item["interview_id"] == interview_id)
        assert actual == expected
    finally:
        db.close()
