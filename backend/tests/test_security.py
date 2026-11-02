"""Security controls: sign-in throttling, CSRF and account administration.

These cover the two controls that gated "production hardened" (rate limiting and
a CSRF defence for cookie-authenticated writes) and the administrator account
management that replaced the "no user-management UI" gap.
"""

from fastapi.testclient import TestClient

from app.api.v1.endpoints.auth import login_limiter
from app.core.config import settings


def _fresh_client() -> TestClient:
    from app.main import app

    return TestClient(app)


def _email_of(role: str = "researcher") -> str:
    from app.core.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        return db.query(User).filter(User.role == role).first().email
    finally:
        db.close()


def _failed(client, email: str, password: str = "definitely-wrong"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def _sign_in(email: str, password: str) -> TestClient:
    client = _fresh_client()
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return client


# ------------------------------------------------------------------ throttling
def test_failed_sign_ins_are_throttled(seeded, monkeypatch):
    monkeypatch.setattr(login_limiter, "limit", 3)
    login_limiter.reset()
    email = _email_of()
    client = _fresh_client()
    try:
        for _ in range(3):
            assert _failed(client, email).status_code == 401
        blocked = _failed(client, email)
        assert blocked.status_code == 429
        assert blocked.json()["error"]["code"] == "rate_limited"
        assert int(blocked.headers["retry-after"]) > 0
        # A throttled attempt issues no session.
        assert "clh_session" not in blocked.headers.get("set-cookie", "")
        # Even the right password is refused while the block stands.
        assert _failed(client, email, "demo-password").status_code == 429
    finally:
        login_limiter.reset()
        client.close()


def test_a_successful_sign_in_clears_the_failure_counter(seeded, monkeypatch):
    monkeypatch.setattr(login_limiter, "limit", 3)
    login_limiter.reset()
    email = _email_of()
    client = _fresh_client()
    try:
        assert _failed(client, email).status_code == 401
        assert _failed(client, email).status_code == 401
        signed_in = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "demo-password"}
        )
        assert signed_in.status_code == 200, signed_in.text
        # The counter was cleared, so two more mistakes are still tolerated.
        assert _failed(client, email).status_code == 401
        assert _failed(client, email).status_code == 401
        assert (
            client.post("/api/v1/auth/login", json={"email": email, "password": "demo-password"}).status_code
            == 200
        )
    finally:
        login_limiter.reset()
        client.close()


def test_a_second_account_is_not_blocked_by_the_history_of_another(seeded, monkeypatch):
    """The account key keeps one person's failures from locking the whole team."""
    monkeypatch.setattr(login_limiter, "limit", 3)
    login_limiter.reset()
    target = _email_of()
    other = _email_of("business_owner")
    try:
        for _ in range(3):
            login_limiter.record_failure(f"email:{target}")
        client = _sign_in(other, "demo-password")
        try:
            assert client.get("/api/v1/auth/me").status_code == 200
        finally:
            client.close()
        assert login_limiter.retry_after(f"email:{target}") > 0
    finally:
        login_limiter.reset()


# ------------------------------------------------------------------------ CSRF
def test_cross_site_writes_are_rejected(seeded):
    payload = {"name": "Forged project", "objective": "A cross-site request must not create this."}

    forged = seeded.post("/api/v1/projects", json=payload, headers={"Origin": "https://attacker.example"})
    assert forged.status_code == 403
    assert forged.json()["error"]["code"] == "csrf_origin_rejected"

    referer = seeded.post(
        "/api/v1/projects", json=payload, headers={"Referer": "https://attacker.example/page"}
    )
    assert referer.status_code == 403

    opaque = seeded.post("/api/v1/projects", json=payload, headers={"Origin": "null"})
    assert opaque.status_code == 403

    # The application's own origin is trusted.
    trusted = seeded.post(
        "/api/v1/projects", json=payload, headers={"Origin": "http://localhost:5173"}
    )
    assert trusted.status_code == 201, trusted.text

    # Same-origin requests behind the Compose proxy do not have to be configured
    # in CORS_ORIGINS: the request's own host is trusted.
    host = seeded.post(
        "/api/v1/projects",
        json={"name": "Same origin", "objective": "Same-origin writes stay allowed."},
        headers={"Origin": "http://testserver"},
    )
    assert host.status_code == 201, host.text


def test_reads_are_not_affected_by_the_origin_check(seeded):
    assert (
        seeded.get("/api/v1/projects", headers={"Origin": "https://attacker.example"}).status_code
        == 200
    )


# -------------------------------------------------------------- account admin
def test_a_non_administrator_cannot_manage_accounts(seeded):
    client = _sign_in(_email_of(), "demo-password")
    try:
        assert client.get("/api/v1/users").status_code == 403
        created = client.post(
            "/api/v1/users",
            json={
                "name": "Escalation Attempt",
                "email": "escalation@example.test",
                "role": "admin",
                "password": "a-long-enough-password",
            },
        )
        assert created.status_code == 403
        assert created.json()["error"]["code"] == "forbidden"
    finally:
        client.close()


def test_an_administrator_can_create_an_account_that_signs_in(seeded):
    created = seeded.post(
        "/api/v1/users",
        json={
            "name": "Nadia Okafor",
            "email": "Nadia.Okafor@Example.test",
            "role": "researcher",
            "job_title": "Senior researcher",
            "password": "an-initial-password",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["email"] == "nadia.okafor@example.test"
    assert body["is_active"] is True
    assert body["initials"] == "NO"

    duplicate = seeded.post(
        "/api/v1/users",
        json={
            "name": "Duplicate",
            "email": "nadia.okafor@example.test",
            "role": "cx",
            "password": "another-long-password",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"

    client = _sign_in("nadia.okafor@example.test", "an-initial-password")
    try:
        assert client.get("/api/v1/auth/me").json()["name"] == "Nadia Okafor"
    finally:
        client.close()

    listed = seeded.get("/api/v1/users").json()
    assert any(member["email"] == "nadia.okafor@example.test" for member in listed)


def test_deactivating_an_account_revokes_its_sessions(seeded):
    created = seeded.post(
        "/api/v1/users",
        json={
            "name": "Leaver",
            "email": "leaver@example.test",
            "role": "cx",
            "password": "a-temporary-password",
        },
    ).json()
    client = _sign_in("leaver@example.test", "a-temporary-password")
    try:
        assert client.get("/api/v1/auth/me").status_code == 200
        updated = seeded.patch(f"/api/v1/users/{created['id']}", json={"is_active": False})
        assert updated.status_code == 200, updated.text
        assert updated.json()["is_active"] is False
        assert client.get("/api/v1/auth/me").status_code == 401
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": "leaver@example.test", "password": "a-temporary-password"},
            ).status_code
            == 401
        )
    finally:
        client.close()


def test_an_administrator_can_reset_another_password(seeded):
    created = seeded.post(
        "/api/v1/users",
        json={
            "name": "Forgetful",
            "email": "forgetful@example.test",
            "role": "researcher",
            "password": "the-original-password",
        },
    ).json()
    client = _sign_in("forgetful@example.test", "the-original-password")
    try:
        reset = seeded.post(
            f"/api/v1/users/{created['id']}/password",
            json={"new_password": "a-replacement-password"},
        )
        assert reset.status_code == 200, reset.text
        assert "no email provider" in reset.json()["message"].lower()
        assert client.get("/api/v1/auth/me").status_code == 401
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": "forgetful@example.test", "password": "the-original-password"},
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"email": "forgetful@example.test", "password": "a-replacement-password"},
            ).status_code
            == 200
        )
    finally:
        client.close()


def test_the_last_administrator_cannot_be_removed(seeded):
    """A workspace must never end up with nobody who can administer it."""
    from app.core.database import SessionLocal
    from app.seed.demo_data import _wipe

    db = SessionLocal()
    try:
        _wipe(db)
    finally:
        db.close()

    client = _fresh_client()
    try:
        registered = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Sole Administrator",
                "email": "sole@example.test",
                "password": "a-long-enough-password",
                "organisation_name": "Everyday Goods",
            },
        )
        assert registered.status_code == 201, registered.text
        admin_id = registered.json()["id"]

        deactivate = client.patch(f"/api/v1/users/{admin_id}", json={"is_active": False})
        assert deactivate.status_code == 400
        assert deactivate.json()["error"]["code"] == "rule_violation"
        demote = client.patch(f"/api/v1/users/{admin_id}", json={"role": "researcher"})
        assert demote.status_code == 400

        # With a second administrator the change is allowed.
        second = client.post(
            "/api/v1/users",
            json={
                "name": "Second Administrator",
                "email": "second@example.test",
                "role": "admin",
                "password": "another-long-password",
            },
        )
        assert second.status_code == 201, second.text
        assert client.patch(f"/api/v1/users/{admin_id}", json={"role": "researcher"}).status_code == 200
    finally:
        client.close()
