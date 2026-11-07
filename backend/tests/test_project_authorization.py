"""Project-level authorization: the IDOR/BOLA test matrix.

These tests talk to the API over HTTP with real sessions. They do not use the
frontend, because frontend restrictions are not a security control.

The synthetic team is deliberately uneven:

* arjun (admin)        - implicit project_owner everywhere
* priya (researcher)   - editor on every study, owner of the shampoo study
* rohan (business)     - owner of "first order to second order", editor on the
                         routine campaign, viewer on packaging, and *not* on the
                         shampoo or body-wash studies
* vikram (cx)          - editor on the shampoo study, viewer on first-to-second
* asha (ceo)           - read-only viewer on every study
* nisha (business)     - owner of the body-wash study
* dev (business)       - owner of the routine campaign and packaging studies
"""

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.services.access import participant_project_ids

PASSWORD = "demo-password"

ADMIN = "arjun.demo@example.test"
RESEARCHER = "priya.demo@example.test"
ROHAN = "rohan.demo@example.test"
VIKRAM = "vikram.demo@example.test"
ASHA = "asha.demo@example.test"
NISHA = "nisha.demo@example.test"
DEV = "dev.demo@example.test"

SHAMPOO = "shampoo"
ROUTINE = "Everyday routine campaign"
BODYWASH = "Body wash"


def client_for(email: str) -> TestClient:
    client = TestClient(app)
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return client


def _projects(client: TestClient) -> list[dict]:
    return client.get("/api/v1/projects").json()["items"]


def _find(fragment: str, client: TestClient) -> dict:
    return next(p for p in _projects(client) if fragment.lower() in p["name"].lower())


def _routine_evidence(admin: TestClient, routine_id: str) -> dict:
    items = admin.get("/api/v1/evidence", params={"project_id": routine_id}).json()["items"]
    assert items, "The seeded routine study should contain evidence."
    return items[0]


def test_authorized_project_is_readable(seeded):
    projects = _projects(seeded)
    bodywash = next(p for p in projects if BODYWASH.lower() in p["name"].lower())
    client = client_for(NISHA)
    try:
        response = client.get(f"/api/v1/projects/{bodywash['id']}")
        assert response.status_code == 200
        assert response.json()["role"] == "project_owner"
    finally:
        client.close()


def test_unauthorized_project_cannot_be_read(seeded):
    routine = _find(ROUTINE, seeded)
    client = client_for(VIKRAM)
    try:
        assert client.get(f"/api/v1/projects/{routine['id']}").status_code == 403
        assert client.get(f"/api/v1/projects/{routine['id']}/journey").status_code == 403
    finally:
        client.close()


def test_unauthorized_project_cannot_be_updated_or_archived(seeded):
    routine = _find(ROUTINE, seeded)
    client = client_for(VIKRAM)
    try:
        updated = client.patch(f"/api/v1/projects/{routine['id']}", json={"priority": "critical"})
        assert updated.status_code == 403
        archived = client.post(f"/api/v1/projects/{routine['id']}/archive")
        assert archived.status_code == 403
    finally:
        client.close()
    after = seeded.get(f"/api/v1/projects/{routine['id']}").json()
    assert after["priority"] == "medium"
    assert after["status"] != "archived"


def test_nested_customer_records_do_not_leak(seeded):
    shampoo = _find(SHAMPOO, seeded)
    matches = seeded.get("/api/v1/participants", params={"q": "Farah"}).json()["items"]
    assert matches, "The seed should contain Farah Khan."
    farah_id = matches[0]["id"]

    db = SessionLocal()
    try:
        assert shampoo["id"] not in participant_project_ids(db, farah_id)
    finally:
        db.close()

    client = client_for(VIKRAM)
    try:
        assert client.get(f"/api/v1/participants/{farah_id}").status_code == 403
        assert client.patch(f"/api/v1/participants/{farah_id}", json={"notes": "leak"}).status_code == 403
    finally:
        client.close()


def test_feedback_evidence_insights_from_another_project_are_denied(seeded):
    routine = _find(ROUTINE, seeded)
    bodywash = _find(BODYWASH, seeded)
    evidence = _routine_evidence(seeded, routine["id"])
    insight = seeded.get("/api/v1/insights", params={"project_id": routine["id"]}).json()["items"][0]
    feedback = seeded.get("/api/v1/feedback", params={"project_id": bodywash["id"]}).json()["items"][0]

    client = client_for(VIKRAM)
    try:
        assert client.get(f"/api/v1/evidence/{evidence['id']}").status_code == 403
        assert client.get(f"/api/v1/evidence/{evidence['id']}/insights").status_code == 403
        assert client.get(f"/api/v1/feedback/{feedback['id']}").status_code == 403
        assert client.get(f"/api/v1/insights/{insight['id']}").status_code == 403
        assert client.get(f"/api/v1/insights/{insight['id']}/traceability").status_code == 403
    finally:
        client.close()


def test_decisions_and_outcomes_from_another_project_are_denied(seeded):
    routine = _find(ROUTINE, seeded)
    decision_id = seeded.get("/api/v1/decisions", params={"project_id": routine["id"]}).json()["items"][0]["id"]
    outcome = seeded.post(
        "/api/v1/outcomes",
        json={
            "name": "Bottle duration",
            "decision_id": decision_id,
            "metric_definition": "Average days a bottle lasts in a shared household.",
            "target_value": 30,
            "unit": "days",
            "direction": "increase",
        },
    )
    assert outcome.status_code == 201, outcome.text

    client = client_for(VIKRAM)
    try:
        assert client.get(f"/api/v1/decisions/{decision_id}").status_code == 403
        assert client.get(f"/api/v1/decisions/{decision_id}/traceability").status_code == 403
        assert client.get(f"/api/v1/outcomes/{outcome.json()['id']}").status_code == 403
        assert client.post(f"/api/v1/decisions/{decision_id}/links", json={"insight_ids": []}).status_code == 403
    finally:
        client.close()

    owner = client_for(DEV)
    try:
        assert owner.get(f"/api/v1/decisions/{decision_id}").status_code == 200
    finally:
        owner.close()


def test_analytics_and_dashboard_reflect_only_visible_projects(seeded):
    admin_dashboard = seeded.get("/api/v1/dashboard").json()
    client = client_for(VIKRAM)
    try:
        scoped = client.get("/api/v1/dashboard").json()
        analytics = client.get("/api/v1/analytics").json()
    finally:
        client.close()

    assert scoped["active_projects"] < admin_dashboard["active_projects"]
    assert scoped["decisions_total"] <= admin_dashboard["decisions_total"]
    assert analytics["metrics"], "Analytics should still return scoped metrics."
    # The scoped run must not report another project's unresolved questions.
    project_names = {row["project_name"] for row in analytics["unresolved_questions"]}
    assert ROUTINE not in project_names


def test_exports_exclude_other_projects(seeded):
    routine = _find(ROUTINE, seeded)
    admin_csv = seeded.get("/api/v1/exports/evidence.csv").text
    routine_evidence = _routine_evidence(seeded, routine["id"])
    admin_header_count = int(seeded.get("/api/v1/exports/evidence.csv").headers["X-Row-Count"])

    client = client_for(VIKRAM)
    try:
        scoped = client.get("/api/v1/exports/evidence.csv")
        traceability = client.get("/api/v1/exports/traceability.csv")
    finally:
        client.close()

    assert scoped.status_code == 200
    assert routine_evidence["code"] in admin_csv
    assert routine_evidence["code"] not in scoped.text
    assert int(scoped.headers["X-Row-Count"]) < admin_header_count
    assert traceability.status_code == 200
    assert "Evidence from a different project" not in traceability.text


def test_search_and_lists_do_not_leak_project_names(seeded):
    admin = seeded.get("/api/v1/search", params={"q": "Everyday routine campaign"}).json()
    assert admin["total"] > 0

    routine = _find(ROUTINE, seeded)
    client = client_for(VIKRAM)
    try:
        scoped = client.get("/api/v1/search", params={"q": "Everyday routine campaign"}).json()
        projects = client.get("/api/v1/projects").json()["items"]
        insights = client.get("/api/v1/insights").json()["items"]
        feedback = client.get("/api/v1/feedback").json()["items"]
        evidence = client.get("/api/v1/evidence").json()["items"]
    finally:
        client.close()

    assert scoped["total"] == 0
    assert all(ROUTINE.lower() not in project["name"].lower() for project in projects)
    assert all(item.get("project_id") != routine["id"] for item in insights)
    assert all(item.get("project_id") != routine["id"] for item in feedback)
    assert all(item.get("project_id") != routine["id"] for item in evidence)


def test_cross_project_evidence_link_is_rejected(seeded):
    shampoo = _find(SHAMPOO, seeded)
    routine = _find(ROUTINE, seeded)
    insight = seeded.get("/api/v1/insights", params={"project_id": shampoo["id"]}).json()["items"][0]
    evidence = _routine_evidence(seeded, routine["id"])

    # Even an administrator cannot create a cross-project relationship through
    # the link endpoint; the rule belongs to the domain, not to the caller.
    response = seeded.post(
        f"/api/v1/insights/{insight['id']}/evidence",
        json={"evidence_id": evidence["id"], "role": "supporting", "rationale": "Should be refused."},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "rule_violation"


def test_cross_project_decision_link_is_rejected(seeded):
    shampoo = _find(SHAMPOO, seeded)
    routine = _find(ROUTINE, seeded)
    decision = seeded.post(
        "/api/v1/decisions",
        json={
            "title": "Shampoo decision",
            "business_function": "growth",
            "problem_statement": "A decision must not absorb another project's evidence.",
            "description": "Used to verify the link rule.",
            "project_id": shampoo["id"],
        },
    ).json()
    evidence = _routine_evidence(seeded, routine["id"])
    response = seeded.post(
        f"/api/v1/decisions/{decision['id']}/links", json={"evidence_ids": [evidence["id"]]}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "rule_violation"


def test_viewer_cannot_write(seeded):
    shampoo = _find(SHAMPOO, seeded)
    client = client_for(ASHA)
    try:
        assert client.get(f"/api/v1/projects/{shampoo['id']}").status_code == 200
        assert client.patch(f"/api/v1/projects/{shampoo['id']}", json={"priority": "low"}).status_code == 403
        assert (
            client.post(
                "/api/v1/feedback",
                json={
                    "project_id": shampoo["id"],
                    "source_type": "written_feedback",
                    "collection_method": "written_feedback",
                    "content": "A viewer must not be able to add this.",
                },
            ).status_code
            == 403
        )
    finally:
        client.close()


def test_researcher_cannot_manage_workspace_administration(seeded):
    client = client_for(RESEARCHER)
    try:
        assert client.get("/api/v1/users").status_code == 403
        assert client.patch("/api/v1/settings", json={"name": "Hijacked"}).status_code == 403
    finally:
        client.close()


def test_project_owner_manages_only_their_project_members(seeded):
    owned = _find("First order to second order", seeded)
    not_owned = _find(BODYWASH, seeded)
    target = next(u for u in seeded.get("/api/v1/users").json() if u["email"] == VIKRAM)

    client = client_for(ROHAN)
    try:
        granted = client.post(
            f"/api/v1/projects/{owned['id']}/members",
            json={"user_id": target["id"], "role": "viewer"},
        )
        assert granted.status_code == 201, granted.text
        denied = client.post(
            f"/api/v1/projects/{not_owned['id']}/members",
            json={"user_id": target["id"], "role": "viewer"},
        )
        assert denied.status_code == 403
        assert client.get(f"/api/v1/projects/{not_owned['id']}").status_code == 403
    finally:
        client.close()


def test_removing_a_member_revokes_access_immediately(seeded):
    bodywash = _find(BODYWASH, seeded)
    target = next(u for u in seeded.get("/api/v1/users").json() if u["email"] == VIKRAM)

    owner = client_for(NISHA)
    try:
        added = owner.post(
            f"/api/v1/projects/{bodywash['id']}/members",
            json={"user_id": target["id"], "role": "viewer"},
        )
        assert added.status_code == 201, added.text
        membership_id = added.json()["id"]
    finally:
        owner.close()

    guest = client_for(VIKRAM)
    try:
        assert guest.get(f"/api/v1/projects/{bodywash['id']}").status_code == 200
    finally:
        guest.close()

    owner = client_for(NISHA)
    try:
        removed = owner.delete(f"/api/v1/projects/{bodywash['id']}/members/{membership_id}")
        assert removed.status_code == 200, removed.text
    finally:
        owner.close()

    guest = client_for(VIKRAM)
    try:
        assert guest.get(f"/api/v1/projects/{bodywash['id']}").status_code == 403
        assert guest.get("/api/v1/projects").json()["items"]
    finally:
        guest.close()


def test_unauthenticated_requests_are_denied(seeded):
    anonymous = TestClient(app)
    try:
        assert anonymous.get("/api/v1/projects").status_code == 401
        assert anonymous.get("/api/v1/dashboard").status_code == 401
        assert anonymous.get("/api/v1/exports/projects.csv").status_code == 401
    finally:
        anonymous.close()
