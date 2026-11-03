"""Evidence-to-insight traceability tests.

These pin the guarantees the product claims: evidence can come from any feedback
source, the customer's statement is never rewritten, every relationship carries
its own classification, cross-project links are refused on the server, unlink is
audited, and the export preserves provenance.
"""

import csv
import io

import pytest

from tests.conftest import CX_EMAIL, OWNER_EMAIL, login

SURVEY_STATEMENT = "The cap is hard to open with wet hands, so I stopped using it in the shower."


def _feedback(client, project_id, **overrides):
    payload = {
        "project_id": project_id,
        "source_type": "short_survey",
        "collection_method": "short_survey",
        "source_reference": "Survey wave 7 · Q3 free-text",
        "content": SURVEY_STATEMENT,
        "interpretation": "Possible packaging accessibility issue, not a product-quality complaint.",
        "context": "Answered from a phone, one line only.",
        "verification_status": "verified",
    }
    payload.update(overrides)
    response = client.post("/api/v1/feedback", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _evidence_from_feedback(client, project_id, **overrides):
    record = _feedback(client, project_id, **overrides)
    response = client.post(f"/api/v1/feedback/{record['id']}/evidence")
    assert response.status_code == 201, response.text
    return record, response.json()


def _insight(client, project_id, title="Traceability insight"):
    response = client.post(
        "/api/v1/insights",
        json={
            "title": title,
            "summary": "Customers describe the cap as difficult to open, which changes how they use it.",
            "project_id": project_id,
            "confidence": "low",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _link(client, insight_id, evidence_id, role="supporting", **extra):
    payload = {"evidence_id": evidence_id, "role": role, **extra}
    return client.post(f"/api/v1/insights/{insight_id}/evidence", json=payload)


def test_feedback_derives_verbatim_evidence_with_provenance(seeded, sample_ids):
    record, evidence = _evidence_from_feedback(seeded, sample_ids["project_id"])

    # The customer's words are copied exactly, not summarised or trimmed.
    assert evidence["content"] == SURVEY_STATEMENT
    assert evidence["feedback_record_id"] == record["id"]
    assert evidence["interpretation"] == record["interpretation"]
    assert evidence["source_type"] == "short_survey"
    assert evidence["collection_method"] == "short_survey"
    assert evidence["research_depth"] == "limited"
    assert evidence["verification_state"] == "verified"
    assert evidence["source_reference"] == record["source_reference"]
    assert evidence["project_id"] == sample_ids["project_id"]

    # Deriving twice from one source would duplicate research history.
    again = seeded.post(f"/api/v1/feedback/{record['id']}/evidence")
    assert again.status_code == 409
    assert again.json()["error"]["details"]["evidence_code"] == evidence["code"]


def test_unverified_and_unattributed_feedback_is_labelled(seeded, sample_ids):
    record, evidence = _evidence_from_feedback(
        seeded,
        sample_ids["project_id"],
        verification_status="unverified",
        source_reference="",
        participant_id=None,
    )
    assert evidence["provenance_status"] == "missing"
    assert evidence["verification_state"] == "unverified"
    assert evidence["is_verified_source"] is False
    assert evidence["is_attributed"] is False
    assert evidence["provenance_warning"]
    assert evidence["review_status"] == "flagged"

    derived = seeded.get(f"/api/v1/feedback/{record['id']}/evidence").json()
    assert [item["id"] for item in derived] == [evidence["id"]]


def test_link_evidence_with_three_classifications_and_read_groups(seeded, sample_ids):
    project_id = sample_ids["project_id"]
    insight = _insight(seeded, project_id)

    _, support = _evidence_from_feedback(seeded, project_id)
    _, against = _evidence_from_feedback(
        seeded, project_id, content="I open the cap one-handed every morning without any trouble."
    )
    _, context = _evidence_from_feedback(
        seeded, project_id, content="I only use the product at the gym, so the bottle stays upright."
    )

    assert _link(seeded, insight["id"], support["id"], "supporting", rationale="Matches the main theme.").status_code == 201
    assert _link(
        seeded,
        insight["id"],
        against["id"],
        "contradictory",
        rationale="One participant reports no difficulty.",
        confidence="high",
        tags=["packaging", "disconfirming"],
    ).status_code == 201
    assert _link(seeded, insight["id"], context["id"], "contextual", rationale="Explains where the product is used.").status_code == 201

    grouped = seeded.get(f"/api/v1/insights/{insight['id']}/evidence").json()
    assert grouped["total"] == 3
    assert grouped["supporting"]["count"] == 1
    assert grouped["contradictory"]["count"] == 1
    assert grouped["contextual"]["count"] == 1
    assert grouped["contradictory"]["items"][0]["confidence"] == "high"
    assert grouped["contradictory"]["items"][0]["tags"] == ["packaging", "disconfirming"]
    assert grouped["contradictory"]["items"][0]["created_by"]["label"]

    detail = seeded.get(f"/api/v1/insights/{insight['id']}").json()
    assert detail["supporting_count"] == 1
    assert detail["contradictory_count"] == 1
    assert detail["contextual_count"] == 1
    assert detail["evidence_count"] == 3


def test_one_evidence_can_serve_several_insights(seeded, sample_ids):
    project_id = sample_ids["project_id"]
    _, evidence = _evidence_from_feedback(seeded, project_id)
    first = _insight(seeded, project_id, title="Cap is hard to open")
    second = _insight(seeded, project_id, title="Product is abandoned in the shower")

    assert _link(seeded, first["id"], evidence["id"], "supporting").status_code == 201
    assert _link(seeded, second["id"], evidence["id"], "contextual").status_code == 201

    reverse = seeded.get(f"/api/v1/evidence/{evidence['id']}/insights").json()
    assert reverse["total"] == 2
    assert [item["insight"]["id"] for item in reverse["supporting"]] == [first["id"]]
    assert [item["insight"]["id"] for item in reverse["contextual"]] == [second["id"]]
    assert reverse["supporting"][0]["insight"]["contradictory_count"] == 0
    assert "never rewritten" in reverse["statement_note"]


def test_relationship_can_be_reclassified_without_touching_the_statement(seeded, sample_ids):
    project_id = sample_ids["project_id"]
    _, evidence = _evidence_from_feedback(seeded, project_id)
    insight = _insight(seeded, project_id)
    _link(seeded, insight["id"], evidence["id"], "supporting", rationale="Initial reading.")

    grouped = seeded.get(f"/api/v1/insights/{insight['id']}/evidence").json()
    relationship_id = grouped["supporting"]["items"][0]["relationship_id"]

    updated = seeded.patch(
        f"/api/v1/insights/{insight['id']}/evidence/{relationship_id}",
        json={
            "role": "contradictory",
            "rationale": "On review this is a counter-example, not support.",
            "confidence": "medium",
            "tags": ["reviewed"],
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()["relationship"]
    assert body["classification"] == "contradictory"
    assert body["rationale"].startswith("On review")
    assert body["relationship_id"] == relationship_id

    # The evidence itself is untouched, and so is the feedback record.
    after = seeded.get(f"/api/v1/evidence/{evidence['id']}").json()
    assert after["content"] == SURVEY_STATEMENT
    assert after["interpretation"] == evidence["interpretation"]
    feedback_after = seeded.get(f"/api/v1/feedback/{evidence['feedback_record_id']}").json()
    assert feedback_after["content"] == SURVEY_STATEMENT

    regrouped = seeded.get(f"/api/v1/insights/{insight['id']}/evidence").json()
    assert regrouped["contradictory"]["count"] == 1
    assert regrouped["supporting"]["count"] == 0


def test_editing_feedback_does_not_rewrite_derived_evidence(seeded, sample_ids):
    record, evidence = _evidence_from_feedback(seeded, sample_ids["project_id"])
    edited = seeded.patch(
        f"/api/v1/feedback/{record['id']}",
        json={"interpretation": "Later interpretation, written after review."},
    )
    assert edited.status_code == 200, edited.text

    after = seeded.get(f"/api/v1/evidence/{evidence['id']}").json()
    assert after["content"] == SURVEY_STATEMENT
    assert after["interpretation"] == record["interpretation"], "the snapshot must not drift"


def test_duplicate_and_invalid_relationships_are_refused(seeded, sample_ids):
    project_id = sample_ids["project_id"]
    _, evidence = _evidence_from_feedback(seeded, project_id)
    insight = _insight(seeded, project_id)

    assert _link(seeded, insight["id"], evidence["id"]).status_code == 201
    duplicate = _link(seeded, insight["id"], evidence["id"], "contradictory")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["details"]["classification"] == "supporting"

    invalid = _link(seeded, insight["id"], evidence["id"], "unsupported")
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"


def test_missing_records_return_clear_errors(seeded, sample_ids):
    insight = _insight(seeded, sample_ids["project_id"])
    missing_evidence = _link(seeded, insight["id"], "does-not-exist")
    assert missing_evidence.status_code == 404
    assert "does not exist" in missing_evidence.json()["error"]["message"]

    _, evidence = _evidence_from_feedback(seeded, sample_ids["project_id"])
    missing_insight = _link(seeded, "does-not-exist", evidence["id"])
    assert missing_insight.status_code == 404

    assert seeded.get("/api/v1/insights/does-not-exist/traceability").status_code == 404
    assert seeded.get("/api/v1/evidence/does-not-exist/insights").status_code == 404


def test_cross_project_relationship_is_rejected(seeded, sample_ids):
    projects = seeded.get("/api/v1/projects", params={"page_size": 50}).json()["items"]
    other_project = next(p for p in projects if p["id"] != sample_ids["project_id"])

    _, foreign_evidence = _evidence_from_feedback(seeded, other_project["id"])
    insight = _insight(seeded, sample_ids["project_id"])

    response = _link(seeded, insight["id"], foreign_evidence["id"])
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "rule_violation"
    assert error["details"]["evidence_project_id"] == other_project["id"]

    grouped = seeded.get(f"/api/v1/insights/{insight['id']}/evidence").json()
    assert grouped["total"] == 0

    # A project-less insight may draw on any project, which is the documented
    # cross-project workflow rather than an accident.
    unscoped = seeded.post(
        "/api/v1/insights",
        json={
            "title": "Cross-project pattern",
            "summary": "A pattern noticed across projects that is not yet owned by a single study.",
        },
    ).json()
    assert _link(seeded, unscoped["id"], foreign_evidence["id"]).status_code == 201


def test_unlink_is_audited_and_keeps_the_evidence(seeded, sample_ids):
    project_id = sample_ids["project_id"]
    _, evidence = _evidence_from_feedback(seeded, project_id)
    insight = _insight(seeded, project_id)
    _link(seeded, insight["id"], evidence["id"], "contradictory")

    grouped = seeded.get(f"/api/v1/insights/{insight['id']}/evidence").json()
    relationship_id = grouped["contradictory"]["items"][0]["relationship_id"]

    removed = seeded.delete(f"/api/v1/insights/{insight['id']}/evidence/{relationship_id}")
    assert removed.status_code == 200, removed.text

    # Both records survive; only the relationship is gone.
    assert seeded.get(f"/api/v1/evidence/{evidence['id']}").status_code == 200
    assert seeded.get(f"/api/v1/insights/{insight['id']}").status_code == 200
    assert seeded.get(f"/api/v1/insights/{insight['id']}/evidence").json()["total"] == 0

    activity = seeded.get("/api/v1/dashboard").json()["recent_activity"]
    summaries = [entry["summary"] for entry in activity]
    assert any("removed as contradictory evidence" in summary for summary in summaries), summaries

    # The legacy evidence-id form still resolves.
    assert _link(seeded, insight["id"], evidence["id"]).status_code == 201
    assert seeded.delete(f"/api/v1/insights/{insight['id']}/evidence/{evidence['id']}").status_code == 200


def test_traceability_reports_quality_without_claiming_validation(seeded, sample_ids):
    project_id = sample_ids["project_id"]
    insight = _insight(seeded, project_id)
    empty = seeded.get(f"/api/v1/insights/{insight['id']}/traceability").json()
    assert empty["quality"]["unsubstantiated"] is True
    assert empty["quality"]["total"] == 0
    assert any("unsubstantiated" in warning.lower() for warning in empty["warnings"])
    assert "validated" not in empty["quality"]

    _, support = _evidence_from_feedback(seeded, project_id)
    _, against = _evidence_from_feedback(
        seeded, project_id, content="No problem at all: the cap opens easily."
    )
    _link(seeded, insight["id"], support["id"], "supporting", rationale="Recurring across sources.")
    _link(seeded, insight["id"], against["id"], "contradictory", rationale="Single counter-example.")

    record = seeded.get(f"/api/v1/insights/{insight['id']}/traceability").json()
    assert record["quality"]["supporting"] == 1
    assert record["quality"]["contradictory"] == 1
    assert record["quality"]["has_conflict"] is True
    assert record["quality"]["unsubstantiated"] is False
    assert record["quality"]["verified"] == 2
    assert record["quality"]["distinct_source_types"] == 1
    assert any("contradict" in warning for warning in record["warnings"])
    assert "Feedback source" in record["chain_note"]


def test_decision_traceability_reaches_the_customer_words(seeded, sample_ids):
    project_id = sample_ids["project_id"]
    _, support = _evidence_from_feedback(seeded, project_id)
    _, against = _evidence_from_feedback(
        seeded, project_id, content="I never had trouble opening it."
    )
    insight = _insight(seeded, project_id, title="Cap design blocks shower use")
    _link(seeded, insight["id"], support["id"], "supporting")
    _link(seeded, insight["id"], against["id"], "contradictory")

    decision = seeded.post(
        "/api/v1/decisions",
        json={
            "title": "Redesign the cap",
            "business_function": "product_category",
            "problem_statement": "Shower use is blocked by the cap.",
            "description": "Fund a packaging review.",
            "rationale": "The pattern recurs, though one customer disagreed.",
            "project_id": project_id,
            "insight_ids": [insight["id"]],
        },
    )
    assert decision.status_code == 201, decision.text
    action = seeded.post(
        f"/api/v1/decisions/{decision.json()['id']}/actions",
        json={"title": "Commission packaging review", "priority": "high"},
    )
    assert action.status_code == 201, action.text

    chain = seeded.get(f"/api/v1/decisions/{decision.json()['id']}/traceability").json()
    assert chain["decision_code"] == decision.json()["code"]
    assert chain["insights"][0]["support_count"] == 1
    assert chain["insights"][0]["contradiction_count"] == 1
    assert chain["insights"][0]["evidence"][0]["content"]
    assert [item["content"] for item in chain["escalated_contradictions"]] == ["I never had trouble opening it."]
    assert any("contradictory item" in gap for gap in chain["gaps"])
    assert any(item["code"] == action.json()["code"] for item in chain["actions"])


def test_traceability_export_preserves_provenance(seeded, sample_ids):
    project_id = sample_ids["project_id"]
    _, support = _evidence_from_feedback(seeded, project_id)
    _, against = _evidence_from_feedback(
        seeded, project_id, content="The cap is fine, honestly."
    )
    insight = _insight(seeded, project_id)
    _link(seeded, insight["id"], support["id"], "supporting", rationale="Recurring complaint.")
    _link(seeded, insight["id"], against["id"], "contradictory", rationale="Disconfirming case.")

    response = seeded.get("/api/v1/exports/traceability.csv")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"] == 'attachment; filename="everyday-goods-traceability-synthetic.csv"'
    assert response.headers["cache-control"] == "no-store"
    assert response.text.startswith("\ufeff"), "the UTF-8 BOM is the existing export convention"

    rows = list(csv.DictReader(io.StringIO(response.text.lstrip("\ufeff"))))
    assert int(response.headers["X-Row-Count"]) == len(rows)
    ours = [row for row in rows if row["insight_code"] == insight["code"]]
    assert len(ours) == 2
    by_class = {row["relationship_classification"]: row for row in ours}

    contradicting = by_class["contradictory"]
    assert contradicting["customer_statement"] == "The cap is fine, honestly."
    assert contradicting["researcher_rationale"] == "Disconfirming case."
    assert contradicting["research_depth"] == "limited"
    assert contradicting["verification_state"] == "verified"
    assert contradicting["attribution"] == "unattributed"
    assert contradicting["source_type"] == "short_survey"
    assert by_class["supporting"]["customer_statement"] == SURVEY_STATEMENT
    assert all(row["data_origin"] == "synthetic" for row in rows)

    # Relationship uniqueness: no insight/evidence pair appears twice.
    pairs = [(row["insight_code"], row["evidence_code"]) for row in rows]
    assert len(pairs) == len(set(pairs))
    assert all(row["customer_statement"] for row in rows), "no statement may be dropped"

    activity = seeded.get("/api/v1/dashboard").json()["recent_activity"]
    assert any("traceability" in entry["summary"] for entry in activity)


def test_relationship_writes_require_a_research_role(seeded, sample_ids):
    project_id = sample_ids["project_id"]
    _, evidence = _evidence_from_feedback(seeded, project_id)
    insight = _insight(seeded, project_id)

    login(seeded, CX_EMAIL)
    blocked = _link(seeded, insight["id"], evidence["id"])
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "forbidden"

    login(seeded, OWNER_EMAIL)
    also_blocked = seeded.patch(
        f"/api/v1/insights/{insight['id']}/evidence/{evidence['id']}", json={"role": "contextual"}
    )
    assert also_blocked.status_code == 403


def test_creating_an_insight_with_a_bad_evidence_id_is_atomic(seeded, sample_ids):
    _, evidence = _evidence_from_feedback(seeded, sample_ids["project_id"])
    title = "Should never be persisted"

    response = seeded.post(
        "/api/v1/insights",
        json={
            "title": title,
            "summary": "Created with one valid and one missing evidence id to check rollback.",
            "project_id": sample_ids["project_id"],
            "evidence_ids": [evidence["id"], "missing-evidence-id"],
        },
    )
    assert response.status_code == 404
    listed = seeded.get("/api/v1/insights", params={"q": title}).json()["items"]
    assert listed == []
    # The valid evidence was not linked to anything either.
    assert seeded.get(f"/api/v1/evidence/{evidence['id']}/insights").json()["total"] == 0
