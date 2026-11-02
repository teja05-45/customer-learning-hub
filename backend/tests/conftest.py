"""Test fixtures.

Each test session gets its own throwaway SQLite file, seeded with the same
synthetic dataset the demo uses, so tests exercise real queries rather than
mocks.
"""

import os
import tempfile
from pathlib import Path

import pytest

TEST_DIR = Path(tempfile.mkdtemp(prefix="clh-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_DIR / 'test.db').as_posix()}"
os.environ["SEED_ON_STARTUP"] = "true"
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "WARNING"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed.demo_data import seed_demo_data  # noqa: E402


@pytest.fixture(scope="session")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def seeded(client):
    """Guarantee the demo dataset exists before a test mutates it."""
    from app.core.database import SessionLocal
    from app.models import User
    from sqlalchemy import func, select

    db = SessionLocal()
    if db.execute(select(func.count(User.id))).scalar_one() == 0:
        seed_demo_data(db)
    db.close()
    return client


@pytest.fixture()
def sample_ids(seeded):
    data = seeded.get("/api/v1/projects").json()["items"]
    project = next(p for p in data if "shampoo" in p["name"].lower())
    participants = seeded.get("/api/v1/participants").json()["items"]
    interviews = seeded.get("/api/v1/interviews").json()["items"]
    completed = next(i for i in interviews if i["status"] == "completed")
    return {
        "project_id": project["id"],
        "participant_id": participants[0]["id"],
        "interview_id": completed["id"],
        "user_id": seeded.get("/api/v1/session").json()["users"][1]["id"],
    }
