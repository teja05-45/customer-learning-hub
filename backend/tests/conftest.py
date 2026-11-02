"""Test fixtures.

Each test session gets its own throwaway SQLite file, rebuilt from the synthetic
demo dataset before each test that needs it. Test data lives only in that
temporary database; it is never written to a production database and every
participant row it creates is marked ``is_synthetic``.
"""

import os
import tempfile
from pathlib import Path

import pytest

TEST_DIR = Path(tempfile.mkdtemp(prefix="clh-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_DIR / 'test.db').as_posix()}"
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "WARNING"
# The test database *is* the synthetic dataset, so demonstration entry is on.
os.environ["DEMO_MODE"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import DEMO_PASSWORD  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.seed.demo_data import seed_demo_data  # noqa: E402

ADMIN_EMAIL = "arjun.demo@example.test"
RESEARCHER_EMAIL = "priya.demo@example.test"
OWNER_EMAIL = "rohan.demo@example.test"
CX_EMAIL = "vikram.demo@example.test"


@pytest.fixture(scope="session")
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def reset_dataset() -> None:
    """Rebuild the synthetic dataset in the throwaway test database."""
    # Failed-sign-in counters are process-wide, so a test that deliberately
    # exhausts them must not leak the block into the next test.
    from app.api.v1.endpoints.auth import login_limiter

    login_limiter.reset()
    db = SessionLocal()
    try:
        seed_demo_data(db, reset=True)
    finally:
        db.close()


def login(client: TestClient, email: str = ADMIN_EMAIL, password: str = DEMO_PASSWORD) -> TestClient:
    """Sign in through the real password endpoint; the session lands in a cookie."""
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return client


@pytest.fixture()
def seeded(client: TestClient) -> TestClient:
    """The synthetic dataset plus an authenticated administrator session.

    Administrators may write research data, decisions, actions, settings and
    exports, so one fixture covers the read/write needs of the API tests. Role
    restrictions are exercised explicitly in ``test_auth.py``.
    """
    reset_dataset()
    return login(client, ADMIN_EMAIL)


@pytest.fixture()
def researcher_client(seeded: TestClient) -> TestClient:
    """The same deterministic dataset, signed in as the researcher."""
    return login(seeded, RESEARCHER_EMAIL)


@pytest.fixture()
def sample_ids(seeded: TestClient) -> dict:
    data = seeded.get("/api/v1/projects").json()["items"]
    project = next(p for p in data if "shampoo" in p["name"].lower())
    participants = seeded.get("/api/v1/participants").json()["items"]
    interviews = seeded.get("/api/v1/interviews").json()["items"]
    completed = next(i for i in interviews if i["status"] == "completed")
    owner = (
        SessionLocal()
        .query(User)
        .filter(User.role == "business_owner")
        .first()
    )
    return {
        "project_id": project["id"],
        "participant_id": participants[0]["id"],
        "interview_id": completed["id"],
        "user_id": owner.id if owner else None,
    }
