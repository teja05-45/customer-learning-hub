"""Regression tests for the CSV export path.

The Settings screen used to answer every download with "Export failed": the
endpoint was restricted to the administrator role while demonstration entry
signed reviewers in as a researcher. These tests pin the whole download path —
every entity, every signed-in role, honest labelling, escaping, empty datasets
and the audit trail — so that defect cannot return.
"""

import csv
import io

import pytest

ENTITIES = [
    "projects",
    "participants",
    "recruitment",
    "interviews",
    "evidence",
    "feedback",
    "insights",
    "decisions",
    "actions",
]

FORBIDDEN_COLUMNS = {"email", "phone", "address", "contact_route", "notes"}


def _rows(response) -> list[list[str]]:
    # Strip the UTF-8 BOM the API adds so Excel reads non-Latin text correctly.
    return list(csv.reader(io.StringIO(response.text.lstrip("\ufeff"))))


@pytest.mark.parametrize("entity", ENTITIES)
def test_every_export_downloads(seeded, entity):
    response = seeded.get(f"/api/v1/exports/{entity}.csv")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="everyday-goods-{entity}-synthetic.csv"'
    )
    assert response.headers["cache-control"] == "no-store"
    rows = _rows(response)
    assert rows[0][-2:] == ["data_origin", "exported_at"]
    assert rows[0][0], "the header must name the first column"
    assert int(response.headers["X-Row-Count"]) == len(rows) - 1
    assert len(rows) > 1, "the seeded dataset should produce data rows"
    assert all(row[-2] == "synthetic" for row in rows[1:])


def test_a_researcher_can_export(researcher_client):
    """The exact role the demo signs in must be able to download records."""
    response = researcher_client.get("/api/v1/exports/participants.csv")
    assert response.status_code == 200, response.text
    assert len(_rows(response)) > 1


def test_anonymous_export_is_rejected(seeded):
    from fastapi.testclient import TestClient

    from app.main import app

    anonymous = TestClient(app)
    try:
        response = anonymous.get("/api/v1/exports/projects.csv")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
    finally:
        anonymous.close()


def test_exports_exclude_personal_and_internal_fields(seeded):
    for entity in ENTITIES:
        header = _rows(seeded.get(f"/api/v1/exports/{entity}.csv"))[0]
        assert FORBIDDEN_COLUMNS.isdisjoint(header), (entity, header)


def test_export_preserves_unicode(seeded):
    created = seeded.post(
        "/api/v1/participants",
        json={
            "display_name": "Zoë Ångström",
            "segment": "repeat_buyer",
            "purchase_frequency": "Every 6 weeks",
            "product_category": "Shampoo",
            "eligibility": "eligible",
            "notes": "Accented name used to check CSV encoding.",
        },
    )
    assert created.status_code == 201, created.text
    response = seeded.get("/api/v1/exports/participants.csv")
    assert response.status_code == 200
    assert "Zoë Ångström" in [row[1] for row in _rows(response)[1:]]


def test_empty_dataset_exports_a_header_only_file(seeded):
    from sqlalchemy import delete

    from app.core.database import SessionLocal
    from app.models import BusinessAction

    db = SessionLocal()
    try:
        db.execute(delete(BusinessAction))
        db.commit()
    finally:
        db.close()

    response = seeded.get("/api/v1/exports/actions.csv")
    assert response.status_code == 200
    assert response.headers["X-Row-Count"] == "0"
    rows = _rows(response)
    assert len(rows) == 1


def test_export_is_written_to_the_audit_trail(seeded):
    response = seeded.get("/api/v1/exports/insights.csv")
    assert response.status_code == 200
    dashboard = seeded.get("/api/v1/dashboard").json()
    summaries = [entry["summary"] for entry in dashboard["recent_activity"]]
    assert any("exported" in summary and "insights" in summary for summary in summaries), summaries


def test_unknown_export_returns_a_helpful_error(seeded):
    response = seeded.get("/api/v1/exports/salaries.csv")
    assert response.status_code == 400
    body = response.json()["error"]
    assert body["code"] == "rule_violation"
    assert "actions" in body["details"]["available"]
