"""Seed safety.

The demo database is rebuilt often. Seeding must be repeatable, must never duplicate codes,
and must never introduce contact details or unlabelled records.
"""

from sqlalchemy import func, select

ADMIN_EMAIL = "arjun.demo@example.test"


def _login(client):
    login = client.post(
        "/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": "demo-password"}
    )
    assert login.status_code == 200, login.text


def _counts(client) -> dict:
    _login(client)
    response = client.post("/api/v1/demo/reset", json={"confirm": True, "phrase": "RESET"})
    assert response.status_code == 200, response.text
    # The reset recreates every user, so the previous session no longer exists.
    _login(client)
    return response.json()["counts"]


def test_demo_reset_is_repeatable(seeded):
    """Two resets produce the same dataset, not an accumulating one."""
    first = _counts(seeded)
    second = _counts(seeded)
    assert first == second
    for key in ("projects", "participants", "interviews", "evidence", "insights", "decisions", "actions"):
        assert second[key] > 0, f"{key} should be seeded"

    listed = seeded.get("/api/v1/projects", params={"page_size": 100}).json()
    assert listed["total"] == second["projects"]


def test_seeded_codes_are_unique(seeded):
    """Generated codes must not collide across a reset."""
    from app.core.database import SessionLocal
    from app.models import Evidence, Insight, Interview, Participant

    db = SessionLocal()
    try:
        for model in (Participant, Interview, Evidence, Insight):
            total = db.execute(select(func.count(model.id))).scalar_one()
            distinct = db.execute(select(func.count(func.distinct(model.code)))).scalar_one()
            assert total == distinct, f"{model.__tablename__} has duplicate codes"
    finally:
        db.close()


def test_all_seeded_people_are_synthetic_and_contact_free(seeded):
    """The dataset must be safe to share and honest about its origin."""
    participants = seeded.get("/api/v1/participants", params={"page_size": 100}).json()["items"]
    assert participants
    for participant in participants:
        assert participant["is_synthetic"] is True
        assert "email" not in participant
        assert "phone" not in participant
        # contact_route describes a process, never a value.
        assert "@" not in (participant.get("contact_route") or "")


def test_seeded_evidence_keeps_provenance_distinction(seeded):
    """The demo must include both verified and flagged evidence, not only clean examples."""
    evidence = seeded.get("/api/v1/evidence", params={"unverified_only": "true"}).json()
    assert evidence["total"] >= 1
    assert evidence["unverified_count"] == evidence["total"]
    for item in evidence["items"]:
        assert item["is_verified_source"] is False
        assert item["provenance_warning"]
        assert item["confidence"] == "low"

    stats = seeded.get("/api/v1/evidence/stats").json()
    assert stats["total"] >= evidence["total"] + 1
    assert stats["unverified"] >= 1
