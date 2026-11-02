"""Complete the delivery plan's P0: authenticated sessions and role enforcement.

The demo still offers a role picker, but it now issues a real server-side
session and every write is checked against the user's role. These tests pin
that boundary so it cannot quietly regress to a UI-only convenience.
"""

from sqlalchemy import select  # noqa: E402


def _fresh_client():
    """A client with no cookies, representing an anonymous browser."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def _login(client, email: str) -> any:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "demo-password"}
    )
    assert response.status_code == 200, response.text
    return response


def test_anonymous_requests_are_rejected(seeded):
    anonymous = _fresh_client()
    try:
        assert anonymous.get("/api/v1/projects").status_code == 401
        assert anonymous.get("/api/v1/dashboard").status_code == 401
        assert anonymous.post(
            "/api/v1/projects",
            json={"name": "Anonymous project", "objective": "Should never be created by an anonymous caller."},
        ).status_code == 401
        # Health and the demo directory must stay reachable for the entry screen.
        assert anonymous.get("/api/v1/health").status_code == 200
        assert anonymous.get("/api/v1/session").status_code == 200
    finally:
        anonymous.close()


def test_password_login_and_logout(seeded):
    client = _fresh_client()
    try:
        from app.core.database import SessionLocal
        from app.models import User

        db = SessionLocal()
        try:
            email = db.query(User).filter(User.role == "researcher").first().email
        finally:
            db.close()
        _login(client, email)
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == email
        assert client.get("/api/v1/projects").status_code == 200

        wrong = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "not-the-password"}
        )
        assert wrong.status_code == 401
        assert "incorrect" in wrong.json()["error"]["message"].lower()

        assert client.post("/api/v1/auth/logout").status_code == 200
        assert client.get("/api/v1/auth/me").status_code == 401
        assert client.get("/api/v1/projects").status_code == 401
    finally:
        client.close()


def test_role_enforcement_on_writes(seeded):
    from app.core.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        researcher = db.execute(select(User).where(User.role == "researcher")).scalars().first()
        owner = db.execute(select(User).where(User.role == "business_owner")).scalars().first()
        cx = db.execute(select(User).where(User.role == "cx")).scalars().first()
    finally:
        db.close()
    
    client = _fresh_client()
    try:
        # CX is read-only for research artefacts.
        _login(client, cx.email)
        assert client.get("/api/v1/projects").status_code == 200
        blocked = client.post(
            "/api/v1/projects",
            json={"name": "CX project", "objective": "A CX user must not be able to create research."},
        )
        assert blocked.status_code == 403
        assert blocked.json()["error"]["code"] == "forbidden"

        # A researcher may create research but not settings changes.
        _login(client, researcher.email)
        created = client.post(
            "/api/v1/projects",
            json={"name": "Researcher project", "objective": "Created by a researcher role in the auth test."},
        )
        assert created.status_code == 201, created.text

        # A business owner may record a decision but not create research.
        _login(client, owner.email)
        blocked_project = client.post(
            "/api/v1/projects",
            json={"name": "Owner project", "objective": "Owners must not create research projects."},
        )
        assert blocked_project.status_code == 403
        decision = client.post(
            "/api/v1/decisions",
            json={
                "title": "Owner decision without evidence",
                "business_function": "growth",
                "problem_statement": "An owner may record an internal judgement.",
                "description": "The API must allow this while keeping it labelled as unevidenced.",
            },
        )
        assert decision.status_code == 201, decision.text
    finally:
        client.close()


def test_demo_login_creates_a_server_side_session(seeded):
    from app.core.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        researcher = db.execute(select(User).where(User.role == "researcher")).scalars().first()
    finally:
        db.close()
    
    session = seeded.get("/api/v1/session").json()
    client = _fresh_client()
    try:
        login_response = _login(client, researcher.email)
        set_cookie = login_response.headers.get("set-cookie", "")
        assert "clh_session" in set_cookie
        assert "httponly" in set_cookie.lower()
        assert "samesite=lax" in set_cookie.lower()
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["id"] == researcher.id
    finally:
        client.close()


def test_first_run_registration_claims_an_empty_workspace(seeded):
    """A fresh production database must be usable: the first account becomes admin."""
    from app.core.database import SessionLocal
    from app.seed.demo_data import _wipe

    db = SessionLocal()
    try:
        _wipe(db)
    finally:
        db.close()

    client = _fresh_client()
    try:
        payload = {
            "name": "Dana Ellis",
            "email": "Dana.Ellis@Example.test",
            "password": "a-long-enough-password",
            "organisation_name": "Everyday Goods",
        }
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["role"] == "admin"
        assert body["email"] == "dana.ellis@example.test"
        # Registration signs the new administrator in.
        assert client.get("/api/v1/auth/me").status_code == 200
        assert client.get("/api/v1/projects").status_code == 200
        assert client.get("/api/v1/settings").json()["name"] == "Everyday Goods"

        # The endpoint is closed once a user exists, so it cannot be used to join.
        again = client.post("/api/v1/auth/register", json=payload)
        assert again.status_code == 403
        assert again.json()["error"]["code"] == "registration_closed"
    finally:
        client.close()


def test_demo_entry_requires_demo_mode(seeded, monkeypatch):
    from app.core.config import settings

    session = seeded.get("/api/v1/session").json()
    researcher = next(user for user in session["users"] if user["role"] == "researcher")
    client = _fresh_client()
    try:
        monkeypatch.setattr(settings, "demo_mode", False)
        response = client.post("/api/v1/auth/demo", json={"user_id": researcher["id"]})
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "demo_disabled"
        assert "clh_session" not in response.headers.get("set-cookie", "")
    finally:
        client.close()


def test_password_change_revokes_other_sessions(seeded):
    from app.core.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        email = db.query(User).filter(User.role == "researcher").first().email
    finally:
        db.close()

    first = _fresh_client()
    second = _fresh_client()
    try:
        _login(first, email)
        _login(second, email)
        changed = first.post(
            "/api/v1/auth/password",
            json={"current_password": "demo-password", "new_password": "a-brand-new-password"},
        )
        assert changed.status_code == 200, changed.text
        assert first.get("/api/v1/auth/me").status_code == 200
        assert second.get("/api/v1/auth/me").status_code == 401

        wrong = first.post(
            "/api/v1/auth/password",
            json={"current_password": "demo-password", "new_password": "another-password-123"},
        )
        assert wrong.status_code == 401
    finally:
        first.close()
        second.close()


def test_session_is_not_trusted_from_a_client_supplied_header_without_demo_mode(seeded, monkeypatch):
    from app.core.config import settings

    client = _fresh_client()
    try:
        session = seeded.get("/api/v1/session").json()
        researcher = next(user for user in session["users"] if user["role"] == "researcher")
        monkeypatch.setattr(settings, "demo_mode", False)
        response = client.get("/api/v1/projects", headers={"X-Demo-User-Id": researcher["id"]})
        assert response.status_code == 401
    finally:
        client.close()
