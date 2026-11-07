"""Outcome measurement lifecycle.

The rules under test are business rules, not formatting: an outcome may be
planned before data exists, but it cannot be marked achieved without an actual
result, and the direction rule decides achieved versus not achieved.
"""

from datetime import date, timedelta

from tests.conftest import CX_EMAIL, login


def _decision(client) -> dict:
    return client.get("/api/v1/decisions").json()["items"][0]


def _action(client, decision_id: str) -> dict | None:
    detail = client.get(f"/api/v1/decisions/{decision_id}").json()
    return detail["actions"][0] if detail["actions"] else None


def test_outcome_planned_without_inventing_a_result(seeded):
    decision = _decision(seeded)
    response = seeded.post(
        "/api/v1/outcomes",
        json={
            "name": "Second purchase within 60 days",
            "decision_id": decision["id"],
            "metric_definition": "Share of trial buyers placing a second order within 60 days.",
            "baseline_value": 18,
            "target_value": 28,
            "unit": "%",
            "direction": "increase",
            "measurement_start": (date.today() + timedelta(days=5)).isoformat(),
            "measurement_end": (date.today() + timedelta(days=40)).isoformat(),
            "data_source": "Commerce order table (not connected)",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "planned"
    assert body["actual_value"] is None
    assert body["recorded_at"] is None
    assert body["decision"]["id"] == decision["id"]


def test_outcome_result_is_derived_from_target_and_direction(seeded):
    decision = _decision(seeded)
    created = seeded.post(
        "/api/v1/outcomes",
        json={
            "name": "Repeat purchase rate",
            "decision_id": decision["id"],
            "metric_definition": "Share of buyers who reorder inside the window.",
            "baseline_value": 10,
            "target_value": 20,
            "unit": "%",
            "direction": "increase",
            "actual_value": 24,
        },
    )
    assert created.status_code == 201, created.text
    outcome = created.json()
    assert outcome["status"] == "achieved"
    assert outcome["recorded_at"] is not None

def test_outcome_direction_decrease(seeded):
    decision = _decision(seeded)
    created = seeded.post(
        "/api/v1/outcomes",
        json={
            "name": "Support contacts per order",
            "decision_id": decision["id"],
            "metric_definition": "Average support contacts per 100 orders.",
            "baseline_value": 12,
            "target_value": 8,
            "direction": "decrease",
            "actual_value": 9,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "not_achieved"


def test_outcome_cannot_claim_a_result_without_a_value(seeded):
    decision = _decision(seeded)
    response = seeded.post(
        "/api/v1/outcomes",
        json={
            "name": "Claimed without evidence",
            "decision_id": decision["id"],
            "metric_definition": "A metric that was never measured.",
            "target_value": 10,
            "status": "achieved",
        },
    )
    assert response.status_code == 400, response.text
    assert "actual result" in response.text.lower()


def test_outcome_cannot_be_left_pending_after_a_result(seeded):
    decision = _decision(seeded)
    response = seeded.post(
        "/api/v1/outcomes",
        json={
            "name": "Contradictory outcome state",
            "decision_id": decision["id"],
            "metric_definition": "A metric with a result but a pending state.",
            "target_value": 10,
            "actual_value": 12,
            "status": "measurement_pending",
        },
    )
    assert response.status_code == 400, response.text


def test_outcome_rejects_an_unrelated_action(seeded):
    decisions = seeded.get("/api/v1/decisions").json()["items"]
    first = decisions[0]
    second = next(item for item in decisions[1:] if item["id"] != first["id"])
    action = _action(seeded, second["id"])
    if action is None:
        return
    response = seeded.post(
        "/api/v1/outcomes",
        json={
            "name": "Wrong action link",
            "decision_id": first["id"],
            "action_id": action["id"],
            "metric_definition": "This action belongs to another decision.",
        },
    )
    assert response.status_code == 400, response.text
    assert "different decision" in response.text.lower()


def test_outcome_write_permissions(seeded):
    login(seeded, CX_EMAIL)
    response = seeded.post(
        "/api/v1/outcomes",
        json={
            "name": "CX cannot measure outcomes",
            "decision_id": _decision(seeded)["id"],
            "metric_definition": "Role boundary check.",
        },
    )
    assert response.status_code == 403, response.text


def test_outcome_list_filters_by_project_and_status(seeded):
    listing = seeded.get("/api/v1/outcomes").json()
    assert listing["total"] >= 2
    assert all(item["decision"]["id"] for item in listing["items"])
    project_id = listing["items"][0]["project_id"]
    filtered = seeded.get("/api/v1/outcomes", params={"project_id": project_id}).json()
    assert all(item["project_id"] == project_id for item in filtered["items"])
    planned = seeded.get("/api/v1/outcomes", params={"status": "planned"}).json()
    assert all(item["status"] == "planned" for item in planned["items"])


def test_seeded_measurement_windows_are_chronological(seeded):
    """Regression: the demo seed once stored the window backwards, which made
    every result update fail the end-before-start validation."""
    items = seeded.get("/api/v1/outcomes").json()["items"]
    assert items
    for item in items:
        if item["measurement_start"] and item["measurement_end"]:
            assert item["measurement_start"] <= item["measurement_end"], item["code"]
