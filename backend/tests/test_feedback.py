"""Feedback-source tests.

These pin the rules that make the module trustworthy: customer words and
researcher interpretation are separate, depth is labelled, verified sources need
a reference, interview links must match their project, and role enforcement is
server-side.
"""

import csv
import io
from datetime import datetime, timezone

from tests.conftest import CX_EMAIL, login


def _project_and_interview(seeded, sample_ids) -> tuple[str, str]:
    interviews = seeded.get(
        "/api/v1/interviews", params={"project_id": sample_ids["project_id"]}
    ).json()["items"]
    completed = next(item for item in interviews if item["status"] == "completed")
    return sample_ids["project_id"], completed["id"]


def _payload(seeded, sample_ids, **overrides) -> dict:
    project_id, interview_id = _project_and_interview(seeded, sample_ids)
    payload = {
        "project_id": project_id,
        "participant_id": sample_ids["participant_id"],
        "interview_id": interview_id,
        "source_type": "interview",
        "collection_method": "video_interview",
        "source_reference": "INT-0001 · 00:14:22",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "contributor": "Priya Menon",
        "content": "It smelled different from the bottle in the shop, so I did not buy it again.",
        "interpretation": "Possible expectation gap rather than a product defect.",
        "context": "Answering the repurchase question.",
        "verification_status": "unverified",
    }
    payload.update(overrides)
    return payload


def _create(seeded, sample_ids, **overrides):
    return seeded.post("/api/v1/feedback", json=_payload(seeded, sample_ids, **overrides))


def test_feedback_preserves_statement_and_interpretation_separately(seeded, sample_ids):
    response = _create(seeded, sample_ids)
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["content"].startswith("It smelled different")
    assert body["interpretation"].startswith("Possible expectation gap")
    assert body["content"] != body["interpretation"]
    assert body["is_attributed"] is True
    assert body["research_depth"] == "deep"
    assert body["verification_status"] == "unverified"
    assert body["project"]["id"] == body["project_id"]
    assert body["interview"]["id"] == body["interview_id"]


def test_survey_feedback_is_labelled_as_limited_depth(seeded, sample_ids):
    response = _create(
        seeded,
        sample_ids,
        interview_id=None,
        source_type="short_survey",
        collection_method="short_survey",
        source_reference="Survey export · wave 1",
        content="I stopped because the bottle was hard to open.",
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["research_depth"] == "limited"
    assert "not for explaining why" in body["depth_note"]
    assert body["interview"] is None


def test_unattributed_feedback_is_allowed_and_labelled(seeded, sample_ids):
    response = _create(
        seeded,
        sample_ids,
        participant_id=None,
        interview_id=None,
        source_type="customer_support",
        collection_method="support_feedback",
        source_reference="Support ticket export (approved)",
        content="The pump broke after one week and I could not get a replacement.",
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["is_attributed"] is False
    assert body["participant"] is None
    assert body["research_depth"] == "context"


def test_verified_source_requires_a_reference(seeded, sample_ids):
    response = _create(
        seeded,
        sample_ids,
        interview_id=None,
        source_type="manual_entry",
        collection_method="manual_entry",
        source_reference="",
        verification_status="verified",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "rule_violation"


def test_interview_must_belong_to_the_project(seeded, sample_ids):
    projects = seeded.get("/api/v1/projects").json()["items"]
    other = next(project for project in projects if project["id"] != sample_ids["project_id"])
    response = _create(seeded, sample_ids, project_id=other["id"])
    assert response.status_code == 400
    assert "different project" in response.json()["error"]["message"]


def test_survey_source_cannot_claim_an_interview(seeded, sample_ids):
    response = _create(
        seeded, sample_ids, source_type="short_survey", collection_method="short_survey"
    )
    assert response.status_code == 400
    assert "Only an interview source" in response.json()["error"]["message"]


def test_customer_experience_role_cannot_create_feedback(seeded, sample_ids):
    payload = _payload(seeded, sample_ids)
    cx_client = login(seeded, CX_EMAIL)
    response = cx_client.post("/api/v1/feedback", json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_feedback_can_be_filtered_and_reviewed(seeded, sample_ids):
    created = _create(
        seeded,
        sample_ids,
        interview_id=None,
        source_type="short_survey",
        collection_method="short_survey",
        content="Opening the bottle was difficult.",
    ).json()

    filtered = seeded.get("/api/v1/feedback", params={"source_type": "short_survey"}).json()
    assert filtered["total"] >= 1
    assert all(item["source_type"] == "short_survey" for item in filtered["items"])
    assert filtered["source_counts"]["short_survey"] >= 1

    reviewed = seeded.patch(
        f"/api/v1/feedback/{created['id']}",
        json={"verification_status": "verified", "source_reference": "Survey wave 1 export"},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["verification_status"] == "verified"

    unverified = seeded.patch(
        f"/api/v1/feedback/{created['id']}",
        json={"verification_status": "needs_review"},
    )
    assert unverified.status_code == 200
    assert unverified.json()["verification_status"] == "needs_review"


def test_feedback_delete_is_audited(seeded, sample_ids):
    created = _create(seeded, sample_ids).json()
    response = seeded.delete(f"/api/v1/feedback/{created['id']}")
    assert response.status_code == 200, response.text
    assert created["code"] in response.json()["message"]

    dashboard = seeded.get("/api/v1/dashboard").json()
    summaries = [item["summary"] for item in dashboard["recent_activity"]]
    assert any("Feedback source" in summary and "deleted" in summary for summary in summaries)


def test_feedback_export_preserves_the_original_content(seeded, sample_ids):
    created = _create(seeded, sample_ids).json()
    response = seeded.get("/api/v1/exports/feedback.csv")
    assert response.status_code == 200, response.text
    rows = list(csv.reader(io.StringIO(response.text.lstrip("\ufeff"))))
    header = rows[0]
    assert "content" in header
    assert "source_reference" in header
    assert "interpretation" in header
    assert any(created["content"] in row for row in rows[1:])


def test_unknown_project_is_rejected(seeded, sample_ids):
    response = _create(seeded, sample_ids, project_id="00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
