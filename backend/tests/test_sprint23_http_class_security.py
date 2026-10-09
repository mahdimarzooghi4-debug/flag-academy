"""ASGI-bound security regression for Academy class read boundaries.

These tests go through FastAPI's dependency graph, rather than calling
permission-dependent route functions with an already-authorized Actor.
"""

from contextlib import contextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.identity.auth import ActorContext, get_actor
from app.main import app

ORG = UUID(int=7101)
CLASS = UUID(int=7102)
COHORT = UUID(int=7103)
CANDIDATE = UUID(int=7104)
OTHER_CANDIDATE = UUID(int=7105)
INSTRUCTOR = UUID(int=7106)
ASSESSOR = UUID(int=7107)


class FakeResult:
    def __init__(self, rows: list):
        self.rows = rows

    def first(self):
        return self.rows[0] if self.rows else None

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        assert len(self.rows) <= 1
        return self.rows[0] if self.rows else None


class FakeDb:
    def __init__(self, batches: list[list]):
        self.batches = list(batches)
        self.statements = []

    async def execute(self, query):
        self.statements.append(query)
        assert self.batches, "Unauthorized reads must not fetch additional data"
        return FakeResult(self.batches.pop(0))


def fake_actor(person: UUID, role: str) -> ActorContext:
    return ActorContext(
        actor_id=str(person),
        person_id=person,
        organization_context_id=ORG,
        roles=frozenset({role}),
    )


@contextmanager
def as_actor(person: UUID, role: str, db: FakeDb):
    async def current_actor():
        return fake_actor(person, role)

    async def current_session():
        yield db

    original = app.dependency_overrides.copy()
    app.dependency_overrides[get_actor] = current_actor
    app.dependency_overrides[get_session] = current_session
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original)


@pytest.mark.parametrize(
    "role",
    ["CANDIDATE", "INSTRUCTOR", "ASSESSOR"],
)
def test_admin_catalog_rejects_other_roles_before_any_query(role: str) -> None:
    db = FakeDb([])
    with as_actor(CANDIDATE, role, db) as client:
        response = client.get("/api/v1/admin/academy/cohorts")
        assert response.status_code == 403
        classes = client.get(f"/api/v1/admin/academy/cohorts/{COHORT}/classes")
        assert classes.status_code == 403
    assert db.statements == []


def test_assessor_cannot_read_class_roster_even_with_valid_org_class() -> None:
    offering = SimpleNamespace(
        id=CLASS, cohort_id=COHORT, title="Authorized class",
        primary_capability_version_id=UUID(int=7110),
    )
    cohort = SimpleNamespace(id=COHORT)
    db = FakeDb([
        [(offering, cohort)],
        [(CANDIDATE, "CANDIDATE"), (OTHER_CANDIDATE, "CANDIDATE")],
        [INSTRUCTOR],
        [],  # No active Assessor grant for this class.
    ])
    with as_actor(ASSESSOR, "ASSESSOR", db) as client:
        response = client.get(f"/api/v1/class-offerings/{CLASS}/roster")
        assert response.status_code == 404
    assert len(db.statements) == 4
    assert db.batches == []


def test_candidate_roster_cannot_expose_another_candidate_or_instructor() -> None:
    offering = SimpleNamespace(
        id=CLASS, cohort_id=COHORT, title="Real class",
        primary_capability_version_id=UUID(int=7110),
    )
    db = FakeDb([
        [(offering, SimpleNamespace(id=COHORT))],
        [(CANDIDATE, "CANDIDATE"), (OTHER_CANDIDATE, "CANDIDATE")],
        [INSTRUCTOR],
    ])
    with as_actor(CANDIDATE, "CANDIDATE", db) as client:
        response = client.get(f"/api/v1/class-offerings/{CLASS}/roster")
        assert response.status_code == 200
        payload = response.json()
        assert payload["members"] == [
            {"person_id": str(CANDIDATE), "member_type": "CANDIDATE"}
        ]
        assert payload["instructor_person_ids"] == []
    assert db.batches == []


def test_unassigned_instructor_sessions_fail_before_session_lookup() -> None:
    db = FakeDb([[CLASS], []])
    with as_actor(INSTRUCTOR, "INSTRUCTOR", db) as client:
        response = client.get(f"/api/v1/class-offerings/{CLASS}/sessions")
        assert response.status_code == 404
    assert len(db.statements) == 2
    assert db.batches == []


def test_cross_tenant_admin_class_roster_denied_before_member_read() -> None:
    db = FakeDb([[]])
    with as_actor(CANDIDATE, "ACADEMY_ADMIN", db) as client:
        response = client.get(f"/api/v1/class-offerings/{CLASS}/roster")
        assert response.status_code == 404
    assert len(db.statements) == 1
