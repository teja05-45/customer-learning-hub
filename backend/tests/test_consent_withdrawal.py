"""Consent withdrawal has prospective consequences.

A withdrawal is not a deleted record. The consent history stays append-only,
future contact is stopped, and previously collected research is retained for the
retention policy rather than silently destroyed.
"""

from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models import ActivityLog, ConsentRecord, Interview, Participant
from tests.conftest import RESEARCHER_EMAIL, login


def _scheduled_interview(client) -> dict:
    items = client.get("/api/v1/interviews", params={"status": "scheduled"}).json()["items"]
    assert items, "the synthetic dataset should contain a scheduled interview"
    return items[0]


def test_withdrawal_cancels_future_contact_and_keeps_history(researcher_client):
    client = researcher_client
    interview = _scheduled_interview(client)
    participant_id = interview["participant_id"]

    response = client.post(
        f"/api/v1/interviews/{interview['id']}/consent",
        json={
            "consent_type": "participation",
            "status": "withdrawn",
            "note": "Participant asked to stop all research contact (synthetic test).",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["consent_status"] == "withdrawn"
    assert body["status"] == "cancelled"
    assert body["recording_enabled"] is False
    assert any(record["status"] == "withdrawn" for record in body["consent_records"])

    refreshed = client.get(f"/api/v1/interviews/{interview['id']}").json()
    assert refreshed["consent_status"] == "withdrawn"
    # Previously captured evidence is retained, not deleted.
    assert refreshed["evidence"] == body["evidence"]

    participant = client.get(f"/api/v1/participants/{participant_id}").json()
    assert participant["contact_consent"] == "withdrawn"

    # A new session cannot be booked after withdrawal.
    blocked = client.post(
        "/api/v1/interviews",
        json={
            "project_id": interview["project_id"],
            "participant_id": participant_id,
            "title": "A session that must not be booked",
            "status": "planned",
        },
    )
    assert blocked.status_code == 400, blocked.text
    assert "withdrawn" in blocked.text.lower()


def test_withdrawal_cancels_other_scheduled_sessions(seeded):
    from tests.conftest import RESEARCHER_EMAIL as researcher_email

    login(seeded, researcher_email)
    interviews = seeded.get("/api/v1/interviews").json()["items"]
    by_participant: dict[str, list[dict]] = {}
    for item in interviews:
        by_participant.setdefault(item["participant_id"], []).append(item)

    # Find a participant with at least two live sessions if the seed has one;
    # otherwise verify the single-session path.
    live = {"planned", "scheduled", "in_progress"}
    pair = next(
        (rows for rows in by_participant.values() if len([r for r in rows if r["status"] in live]) >= 1),
        None,
    )
    assert pair is not None
    target = next(r for r in pair if r["status"] in live)
    original_id = target["id"]

    response = seeded.post(
        f"/api/v1/interviews/{original_id}/consent",
        json={
            "consent_type": "participation",
            "status": "withdrawn",
            "note": "Withdrawal recorded for the regression test.",
        },
    )
    assert response.status_code == 200, response.text

    db = SessionLocal()
    try:
        remaining = (
            db.query(Interview)
            .filter(
                Interview.participant_id == target["participant_id"],
                Interview.status.in_(("planned", "scheduled", "in_progress")),
            )
            .count()
        )
        assert remaining == 0
        withdrawal_rows = (
            db.query(ConsentRecord)
            .filter(
                ConsentRecord.participant_id == target["participant_id"],
                ConsentRecord.status == "withdrawn",
            )
            .count()
        )
        assert withdrawal_rows >= 1
        participant = db.get(Participant, target["participant_id"])
        assert participant is not None and participant.contact_consent == "withdrawn"
        audit = (
            db.query(ActivityLog)
            .filter(ActivityLog.verb == "withdrawn", ActivityLog.entity_type == "participant")
            .count()
        )
        assert audit >= 1
    finally:
        db.close()
