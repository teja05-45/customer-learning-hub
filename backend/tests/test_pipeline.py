"""Recruitment pipeline behaviour.

These tests pin the definitions the dashboard depends on: which participants
count as contacted, what the response-rate denominator is, and that every stage
change leaves a history event even when it is a side effect of an interview.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select


def _new_participant(client, name: str, segment: str = "lapsed_buyer") -> dict:
    response = client.post(
        "/api/v1/participants",
        json={"display_name": name, "segment": segment, "eligibility": "eligible"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _dash(client) -> dict:
    return client.get("/api/v1/dashboard").json()


def test_selected_participants_are_not_counted_as_contacted(seeded, sample_ids):
    """The denominator must only contain people who were actually invited."""
    before = _dash(seeded)
    participant = _new_participant(seeded, "Pipeline Counting Buyer")

    created = seeded.post(
        "/api/v1/recruitment",
        json={"project_id": sample_ids["project_id"], "participant_ids": [participant["id"]]},
    )
    assert created.status_code == 201, created.text

    after_select = _dash(seeded)
    assert after_select["response_rate"]["denominator"] == before["response_rate"]["denominator"]
    assert after_select["participants_contacted"] == before["participants_contacted"]

    record = created.json()["created"][0]
    seeded.patch(f"/api/v1/recruitment/{record['id']}", json={"stage": "invited"})

    after_invite = _dash(seeded)
    assert after_invite["response_rate"]["denominator"] == before["response_rate"]["denominator"] + 1
    assert after_invite["response_rate"]["numerator"] == before["response_rate"]["numerator"]
    assert after_invite["participants_contacted"] == before["participants_contacted"] + 1


def test_distinct_participants_are_counted_once_across_projects(seeded, sample_ids):
    """One person invited to two studies is still one person contacted."""
    participant = _new_participant(seeded, "Pipeline Reused Buyer")
    other = seeded.post(
        "/api/v1/projects",
        json={
            "name": "Secondary pipeline project",
            "objective": "Check that participant-level metrics are de-duplicated across projects.",
            "status": "planning",
            "target_segments": ["lapsed_buyer"],
        },
    ).json()

    for project_id in (sample_ids["project_id"], other["id"]):
        created = seeded.post(
            "/api/v1/recruitment",
            json={"project_id": project_id, "participant_ids": [participant["id"]]},
        )
        assert created.status_code == 201, created.text
        record = created.json()["created"][0]
        seeded.patch(f"/api/v1/recruitment/{record['id']}", json={"stage": "invited"})

    invited_rows = seeded.get("/api/v1/recruitment").json()["items"]
    mine = [row for row in invited_rows if row["participant_id"] == participant["id"]]
    assert len(mine) == 2, "two project records should exist"
    dashboard = _dash(seeded)
    assert dashboard["participants_contacted"] == len(
        {row["participant_id"] for row in invited_rows if row["invited_at"]}
    )


def test_scheduling_and_completing_an_interview_writes_history(seeded, sample_ids):
    """Stage changes caused by an interview are still pipeline history."""
    participant = _new_participant(seeded, "Pipeline Interview Buyer")
    record = seeded.post(
        "/api/v1/recruitment",
        json={"project_id": sample_ids["project_id"], "participant_ids": [participant["id"]]},
    ).json()["created"][0]
    seeded.patch(f"/api/v1/recruitment/{record['id']}", json={"stage": "invited"})

    interview = seeded.post(
        "/api/v1/interviews",
        json={
            "project_id": sample_ids["project_id"],
            "participant_id": participant["id"],
            "title": "Pipeline history interview",
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
            "status": "scheduled",
        },
    )
    assert interview.status_code == 201, interview.text

    listed = seeded.get("/api/v1/recruitment").json()["items"]
    row = next(item for item in listed if item["id"] == record["id"])
    assert row["stage"] == "scheduled"
    assert [event["to_stage"] for event in row["events"]][0] == "scheduled"
    assert row["events"][0]["actor"] is not None, "an actor must be attributed"

    seeded.patch(f"/api/v1/interviews/{interview.json()['id']}", json={"status": "completed"})
    listed = seeded.get("/api/v1/recruitment").json()["items"]
    row = next(item for item in listed if item["id"] == record["id"])
    assert row["stage"] == "completed"
    assert [event["to_stage"] for event in row["events"]][0] == "completed"
    assert "invited" in {event["to_stage"] for event in row["events"]}


def test_stage_counts_and_filters_are_consistent(seeded):
    """Card counts must agree with the rows the filters return."""
    listing = seeded.get("/api/v1/recruitment").json()
    for stage, count in listing["stage_counts"].items():
        filtered = seeded.get("/api/v1/recruitment", params={"stage": stage}).json()
        assert filtered["total"] == count, f"stage {stage} count disagrees with its filter"
        assert all(item["stage"] == stage for item in filtered["items"])

    assert sum(listing["stage_counts"].values()) == listing["total"]


def test_segment_coverage_is_derived_from_records(seeded, sample_ids):
    """Coverage must count the project's own recruitment records only."""
    listing = seeded.get("/api/v1/recruitment", params={"project_id": sample_ids["project_id"]}).json()
    coverage = listing["segment_coverage"]
    assert sum(coverage.values()) == listing["total"]
    rows = seeded.get("/api/v1/dashboard").json()["segments"]
    for segment, count in coverage.items():
        assert any(point["segment"] == segment for point in rows)
        assert count >= 1
