"""Adversarial API probe.

Run against a live instance and it checks the invariants the product claims in
``docs/`` — not just the happy path. It resets the synthetic dataset before and
after, so it is safe to point at the demo stack.

    python scripts/api_audit.py [base_url]

Exit code 1 if any check fails.
"""

from __future__ import annotations

import csv
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000") + "/api/v1"

failures: list[str] = []
checks = 0


def call(method: str, path: str, payload=None, raw: bool = False):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
            return response.status, (body if raw else (json.loads(body) if body else None))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"raw": body}
        return error.code, parsed


def check(name: str, condition: bool, detail: str = "") -> None:
    global checks
    checks += 1
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}{(' — ' + detail) if detail else ''}")
        failures.append(name)


def reset() -> None:
    status, body = call("POST", "/demo/reset", {"confirm": True, "phrase": "RESET"})
    assert status == 200, (status, body)


def first_id(collection: str) -> str:
    _, body = call("GET", f"/{collection}?page_size=1")
    return body["items"][0]["id"]


print("== pagination and parameter hygiene")
reset()
for path in ("/projects?page=0", "/projects?page_size=0", "/projects?page=-3", "/projects?page_size=1000"):
    status, body = call("GET", path)
    check(
        f"{path} rejected with a field explanation",
        status == 422 and bool(body.get("error", {}).get("details")),
        f"status={status} body={str(body)[:120]}",
    )

status, body = call("GET", "/projects?page_size=100&page=1")
check("maximum page size accepted", status == 200 and len(body.get("items", [])) <= 100, f"status={status}")

status, body = call("GET", "/projects?status=not_a_status")
check(
    "unknown filter value yields an empty result rather than ignoring the filter",
    status == 200 and body.get("total") == 0,
    f"status={status} total={body.get('total')}",
)

print("== error envelope consistency")
for path in ("/projects/does-not-exist", "/insights/does-not-exist", "/decisions/nope"):
    status, body = call("GET", path)
    check(
        f"{path} returns 404 envelope",
        status == 404 and body.get("error", {}).get("code") == "not_found",
        f"status={status} body={str(body)[:120]}",
    )

status, body = call("GET", "/projects", raw=False)
check("list response shape stable", {"items", "total", "page", "page_size"} <= set(body), str(body)[:100])

print("== search edge cases")
for query in ("%", "_", "  ", "a", "x" * 100, "shampoo%' OR 1=1--"):
    status, body = call("GET", f"/search?q={urllib.parse.quote(query)}")
    check(
        f"search {query[:12]!r} returns a shaped response",
        status == 200 and "groups" in body,
        f"status={status}",
    )

status, body = call("GET", "/search?q=" + urllib.parse.quote("x" * 300))
check("over-long search term is rejected, not truncated silently", status == 422, f"status={status}")

status, body = call("GET", "/search?q=" + urllib.parse.quote("shampoo%' OR 1=1--"))
check("sql-ish search term is handled, not executed", status == 200 and "groups" in body, f"status={status}")

_, plain = call("GET", "/search?q=shampoo")
_, filler = call("GET", "/search?q=" + urllib.parse.quote("the shampoo"))
check(
    "filler words are ignored so natural queries still match",
    filler.get("total") == plain.get("total") and plain.get("total", 0) > 0,
    f"plain={plain.get('total')} filler={filler.get('total')}",
)

print("== projects")
status, body = call("POST", "/projects", {"name": "ab", "objective": "short"})
check("short project name rejected", status == 422, f"status={status}")

status, body = call(
    "POST",
    "/projects",
    {"name": "Audit project", "objective": "Check that dates are validated properly.", "start_date": "2026-05-01", "deadline": "2026-04-01"},
)
check("deadline before start rejected", status == 422, f"status={status} body={str(body)[:140]}")

status, body = call("GET", "/projects/templates")
check("four templates offered", status == 200 and len(body) == 4, f"status={status} n={len(body) if isinstance(body, list) else '?'}")
first_template = body[0]
status, body = call(
    "POST",
    "/projects",
    {
        "name": "Audit template project",
        "objective": "Create a project from a template's starter questions.",
        "questions": [{"text": question} for question in first_template["questions"][:3]],
    },
)
check("starter questions stored", status == 201 and len(body.get("questions", [])) == 3, f"status={status}")

status, body = call("POST", "/projects", {"name": "Audit blank", "objective": "Create without a template."})
project_id = body.get("id")
check("project created", status == 201 and project_id, f"status={status}")

status, body = call("PATCH", f"/projects/{project_id}", {})
check("empty PATCH is accepted and changes nothing", status == 200, f"status={status}")

status, body = call("PATCH", f"/projects/{project_id}", {"status": "nonsense"})
check("invalid status rejected", status == 422, f"status={status}")

print("== participants")
status, body = call("POST", "/participants", {"display_name": "Audit Person", "segment": "lapsed_buyer"})
participant_id = body.get("id")
check("participant created", status == 201 and body.get("is_synthetic") is True, f"status={status}")
check("no contact fields in participant payload", not ({"email", "phone", "address"} & set(body or {})), str(body)[:120])

status, body = call("POST", f"/participants/{participant_id}/assign", {"project_id": project_id})
check("assign to project", status == 201, f"status={status}")
status, body = call("POST", f"/participants/{participant_id}/assign", {"project_id": project_id})
check("double assignment rejected", status == 409, f"status={status} body={str(body)[:120]}")

print("== recruitment transitions")
_, recs = call("GET", f"/recruitment?project_id={project_id}&page_size=5")
record = recs["items"][0]
status, body = call("PATCH", f"/recruitment/{record['id']}", {"stage": "completed"})
check(
    "illegal stage jump rejected with allowed moves",
    status == 400 and "allowed" in str(body),
    f"status={status} body={str(body)[:140]}",
)
status, body = call("PATCH", f"/recruitment/{record['id']}", {"stage": "selected"})
check("legal stage move accepted", status == 200 and body.get("stage") == "selected", f"status={status}")
status, body = call("PATCH", f"/recruitment/{record['id']}", {"stage": "identified"})
check("backwards move rejected", status == 400, f"status={status}")

print("== interviews and consent")
status, body = call("POST", "/interviews", {"project_id": project_id, "participant_id": participant_id, "title": "Audit interview", "objective": "Probe the consent gate.", "use_default_guide": True})
interview_id = body.get("id")
check("interview created with guide", status == 201 and len(body.get("guide", [])) > 0, f"status={status}")

status, body = call("PATCH", f"/interviews/{interview_id}", {"recording_enabled": True})
check("recording blocked without consent", status == 400, f"status={status} body={str(body)[:120]}")

status, body = call("POST", f"/interviews/{interview_id}/consent", {"consent_type": "recording", "status": "declined"})
check("declined consent recorded", status == 200 or status == 201, f"status={status}")
status, body = call("PATCH", f"/interviews/{interview_id}", {"recording_enabled": True})
check("recording still blocked after decline", status == 400, f"status={status}")

status, body = call("POST", f"/interviews/{interview_id}/consent", {"consent_type": "recording", "status": "granted"})
status, body = call("PATCH", f"/interviews/{interview_id}", {"recording_enabled": True})
check("recording allowed after grant", status == 200, f"status={status} body={str(body)[:120]}")

print("== evidence")
status, body = call("POST", "/evidence", {"interview_id": interview_id, "evidence_type": "verbatim_quote", "content": "=HYPERLINK(\"http://example.test\",\"click\")", "provenance": "Audit note 1"})
evidence_id = body.get("id")
check("evidence created", status == 201, f"status={status}")
status, body = call("POST", "/evidence", {"interview_id": interview_id, "evidence_type": "observation", "content": "No source noted for this observation."})
check(
    "evidence without provenance is accepted but flagged and downgraded",
    status == 201
    and body.get("provenance_status") == "missing"
    and body.get("review_status") == "flagged"
    and body.get("confidence") == "low",
    str(body)[:160],
)

status, body = call("DELETE", "/evidence/does-not-exist")
check("delete unknown evidence 404s", status == 404, f"status={status}")

print("== insights")
status, body = call("POST", "/insights", {"title": "Audit insight", "summary": "An insight created by the audit probe to check validation rules.", "project_id": project_id})
insight_id = body.get("id")
check("insight created", status == 201, f"status={status}")
status, body = call("PATCH", f"/insights/{insight_id}", {"status": "validated_internal"})
check("validation without evidence blocked", status == 400, f"status={status}")
status, body = call("POST", f"/insights/{insight_id}/evidence", {"evidence_id": evidence_id, "role": "supporting"})
check("evidence linked", status == 201, f"status={status}")
status, body = call("POST", f"/insights/{insight_id}/evidence", {"evidence_id": evidence_id, "role": "supporting"})
check("duplicate link rejected", status == 409, f"status={status}")
status, body = call("PATCH", f"/insights/{insight_id}", {"status": "validated_internal"})
check("validation allowed with evidence", status == 200 and body.get("validated_at"), f"status={status}")

print("== decisions")
status, body = call(
    "POST",
    "/decisions",
    {
        "title": "Audit decision",
        "business_function": "growth",
        "problem_statement": "Probe the linkage and sufficiency rules.",
        "description": "A decision created by the audit probe.",
    },
)
decision_id = body.get("id")
check("decision created", status == 201, f"status={status}")

status, body = call("POST", f"/decisions/{decision_id}/links", {"insight_ids": [insight_id], "evidence_ids": [evidence_id]})
check("decision links accepted", status == 201 and body.get("insight_count") == 1, f"status={status} body={str(body)[:140]}")
check("decision marked evidence sufficient after linking", body.get("evidence_sufficient") is True, str(body.get("evidence_sufficient")))

status, body = call("POST", f"/decisions/{decision_id}/links", {"insight_ids": [insight_id]})
check("duplicate decision link rejected", status == 409, f"status={status}")

for kind, target in (("insight", insight_id), ("evidence", evidence_id)):
    status, body = call("DELETE", f"/decisions/{decision_id}/links/{kind}/{target}")
    check(f"{kind} unlink accepted", status == 200, f"status={status}")

status, body = call("GET", f"/decisions/{decision_id}")
check(
    "unlinking the last source resets evidence_sufficient",
    body.get("evidence_sufficient") is False,
    f"evidence_sufficient={body.get('evidence_sufficient')!r}",
)

# An explicit "we looked and it is not enough" must survive a later link.
_, explicit = call(
    "POST",
    "/decisions",
    {
        "title": "Audit explicit judgement",
        "business_function": "brand_marketing",
        "problem_statement": "Check that an explicit judgement is not overwritten.",
        "description": "Created by the audit probe.",
        "evidence_sufficient": False,
    },
)
call("POST", f"/decisions/{explicit['id']}/links", {"insight_ids": [insight_id]})
_, explicit_after = call("GET", f"/decisions/{explicit['id']}")
check(
    "explicit evidence_sufficient=false survives linking",
    explicit_after.get("evidence_sufficient") is False,
    f"evidence_sufficient={explicit_after.get('evidence_sufficient')!r}",
)

print("== actions")
status, body = call("POST", "/actions", {"title": "Audit action", "description": "Probe completion bookkeeping.", "due_date": "2026-01-01"})
action_id = body.get("id")
check("action created", status == 201, f"status={status}")
status, body = call("PATCH", f"/actions/{action_id}", {"status": "completed"})
check("completion stamps completed_at", status == 200 and body.get("completed_at"), str(body)[:140])
status, body = call("PATCH", f"/actions/{action_id}", {"status": "in_progress"})
check("reopening clears completed_at", status == 200 and body.get("completed_at") in (None, ""), str(body.get("completed_at")))

status, body = call("GET", "/actions?overdue_only=true")
check("overdue filter returns only overdue", all(item.get("is_overdue") for item in body.get("items", [])), str(body)[:120])

print("== settings and exports")
status, body = call("PATCH", "/settings", {"retention_months": -5})
check("negative retention rejected", status == 422, f"status={status} body={str(body)[:120]}")
status, body = call("PATCH", "/settings", {"recording_default": True})
check(
    "recording_default is actually persisted",
    status == 200 and body.get("recording_default") is True,
    f"status={status} body={str(body)[:140]}",
)
call("PATCH", "/settings", {"recording_default": False})

status, raw = call("GET", "/exports/evidence.csv", raw=True)
lines = raw.splitlines()
check("csv has is_synthetic and exported_at columns", "is_synthetic" in lines[0] and "exported_at" in lines[0], lines[0][:160])
dangerous_cells = [
    cell
    for row in csv.reader(io.StringIO(raw))
    for cell in row
    if cell[:1] in ("=", "+", "@") or (cell[:1] == "-" and not cell[1:2].isdigit())
]
check(
    "csv neutralises formula injection",
    not dangerous_cells,
    f"first dangerous cell: {dangerous_cells[0][:80]!r}" if dangerous_cells else "",
)

status, body = call("GET", "/exports/nope.csv")
check("unknown export lists available entities", status == 400 and "available" in str(body), f"status={status}")

print("== demo reset guard")
status, body = call("POST", "/demo/reset", {"confirm": True, "phrase": "nope"})
check("reset refuses wrong phrase", status == 400, f"status={status}")

print("== restore")
reset()

print(f"\n{checks - len(failures)}/{checks} checks passed")
if failures:
    print("failures:")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
