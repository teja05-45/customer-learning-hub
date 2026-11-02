"""Regression tests for defects found during the audit.

Each test names the invariant it protects, so a future change that reopens the
hole fails loudly instead of silently shipping.
"""

import csv
import io


def _decision(client, **overrides):
    payload = {
        "title": "Integrity check decision",
        "business_function": "growth",
        "problem_statement": "Prove the sufficiency flag cannot go stale.",
        "description": "Created by an integrity test.",
    }
    payload.update(overrides)
    response = client.post("/api/v1/decisions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _insight_with_evidence(client, sample_ids):
    evidence = client.post(
        "/api/v1/evidence",
        json={
            "interview_id": sample_ids["interview_id"],
            "evidence_type": "verbatim_quote",
            "content": "A quote created by an integrity test.",
            "provenance": "Integrity test note 1",
        },
    ).json()
    insight = client.post(
        "/api/v1/insights",
        json={
            "title": "Integrity check insight",
            "summary": "An insight created to check decision linkage behaviour.",
            "project_id": sample_ids["project_id"],
        },
    ).json()
    linked = client.post(
        f"/api/v1/insights/{insight['id']}/evidence",
        json={"evidence_id": evidence["id"], "role": "supporting"},
    )
    assert linked.status_code == 201, linked.text
    return insight["id"], evidence["id"]


def test_exports_neutralise_spreadsheet_formulas(seeded, sample_ids):
    """A customer quote must never become a live formula in Excel."""
    hostile = '=HYPERLINK("http://example.test","click")'
    created = seeded.post(
        "/api/v1/evidence",
        json={
            "interview_id": sample_ids["interview_id"],
            "evidence_type": "verbatim_quote",
            "content": hostile,
            "provenance": "Integrity test note 2",
        },
    )
    assert created.status_code == 201, created.text

    response = seeded.get("/api/v1/exports/evidence.csv")
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.text)))
    header, *body = rows
    content_column = header.index("content")

    cells = [row[content_column] for row in body if row]
    assert f"'{hostile}" in cells, "the exported text should still be readable, just neutralised"
    # Neutralised means the cell no longer starts with "=", so no spreadsheet
    # evaluates it as a formula.
    assert all(not cell.startswith(("=", "+", "@")) for cell in cells), cells
    assert any(cell.startswith("'=") for cell in cells), cells


def test_settings_recording_default_is_persisted(seeded):
    """A field the API documents as writable must not be silently dropped."""
    updated = seeded.patch("/api/v1/settings", json={"recording_default": True})
    assert updated.status_code == 200, updated.text
    assert updated.json()["recording_default"] is True

    fetched = seeded.get("/api/v1/settings").json()
    assert fetched["recording_default"] is True

    seeded.patch("/api/v1/settings", json={"recording_default": False})


def test_decision_sufficiency_tracks_links(seeded, sample_ids):
    """The flag must follow the evidence, but never overwrite a human judgement."""
    insight_id, evidence_id = _insight_with_evidence(seeded, sample_ids)

    unassessed = _decision(seeded)
    assert unassessed["evidence_sufficient"] is None

    linked = seeded.post(
        f"/api/v1/decisions/{unassessed['id']}/links",
        json={"insight_ids": [insight_id], "evidence_ids": [evidence_id]},
    )
    assert linked.status_code == 201, linked.text
    assert linked.json()["evidence_sufficient"] is True

    for kind, target in (("insight", insight_id), ("evidence", evidence_id)):
        removed = seeded.delete(f"/api/v1/decisions/{unassessed['id']}/links/{kind}/{target}")
        assert removed.status_code == 200, removed.text

    after = seeded.get(f"/api/v1/decisions/{unassessed['id']}").json()
    assert after["evidence_sufficient"] is False
    assert after["insight_count"] == 0 and after["evidence_count"] == 0


def test_explicit_insufficient_judgement_survives_linking(seeded, sample_ids):
    insight_id, _ = _insight_with_evidence(seeded, sample_ids)
    explicit = _decision(seeded, evidence_sufficient=False)

    seeded.post(f"/api/v1/decisions/{explicit['id']}/links", json={"insight_ids": [insight_id]})
    after = seeded.get(f"/api/v1/decisions/{explicit['id']}").json()
    assert after["evidence_sufficient"] is False, "linking must not rewrite a human judgement"


def test_unlinking_is_recorded_in_the_activity_trail(seeded, sample_ids):
    insight_id, _ = _insight_with_evidence(seeded, sample_ids)
    decision = _decision(seeded)
    seeded.post(f"/api/v1/decisions/{decision['id']}/links", json={"insight_ids": [insight_id]})
    seeded.delete(f"/api/v1/decisions/{decision['id']}/links/insight/{insight_id}")

    dashboard = seeded.get("/api/v1/dashboard").json()
    summaries = [entry["summary"] for entry in dashboard["recent_activity"]]
    assert any("no customer source left" in summary for summary in summaries), summaries
