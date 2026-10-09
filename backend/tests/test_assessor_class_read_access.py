"""P23-09B: a global Assessor role is never an Academy classroom permission.

Exercises the public ASGI routes and real SQL query predicates through a
controlled AsyncSession, including positive role-scoped reads and fail-closed cases.
No private classroom read is allowed by a stale/revoked/other-class grant.
"""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Iterator, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.assessor_access import has_live_assessor_class_access
from app.db import get_session
from app.identity.auth import ActorContext, get_actor
from app.main import app

ORG = UUID(int=8401)
COHORT = UUID(int=8402)
CLASS = UUID(int=8403)
SECOND_CLASS = UUID(int=8404)
ASSESSOR = UUID(int=8405)
LEARNER = UUID(int=8406)
SESSION = UUID(int=8407)


class Result:
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


class DB:
    def __init__(self, batches: list[list], *, empty_tail: bool = False):
        self.batches = list(batches)
        self.empty_tail = empty_tail
        self.queries = []

    async def execute(self, query):
        self.queries.append(query)
        if self.batches:
            return Result(self.batches.pop(0))
        assert self.empty_tail, "Unauthorized private source lookup"
        return Result([])


def actor(*roles: str, org: UUID = ORG) -> ActorContext:
    return ActorContext(
        actor_id=str(ASSESSOR), person_id=ASSESSOR,
        organization_context_id=org, roles=frozenset(roles),
    )


def grant_rows(*, starts_at=None, ends_at=None, revoked_at=None,
               class_status="ACTIVE", cohort_status="ACTIVE"):
    now = datetime.now(UTC)
    return [(
        SimpleNamespace(
            id=UUID(int=8408), organization_context_id=ORG,
            class_offering_id=CLASS, assessor_person_id=ASSESSOR,
            starts_at=starts_at or now - timedelta(hours=1),
            ends_at=ends_at or now + timedelta(hours=1),
            revoked_at=revoked_at,
        ),
        SimpleNamespace(id=CLASS, cohort_id=COHORT, status=class_status),
        SimpleNamespace(id=COHORT, status=cohort_status),
    )]


@pytest.mark.asyncio
async def test_only_live_mandate_with_current_identity_membership_grants_access():
    db = DB([grant_rows(), [UUID(int=8409)]])
    allowed = await has_live_assessor_class_access(
        cast(AsyncSession, db), actor=actor("ASSESSOR"), class_offering_id=CLASS
    )
    assert allowed and not db.batches
    sql_params = db.queries[0].compile().params.values()
    assert {ORG, CLASS, ASSESSOR}.issubset(set(sql_params))
    assert "ASSESSOR" in db.queries[1].compile().params.values()


@pytest.mark.asyncio
@pytest.mark.parametrize("batches,expected_reads", [
    ([[]], 1),
    ([grant_rows(ends_at=datetime.now(UTC) - timedelta(minutes=1))], 1),
    ([grant_rows(starts_at=datetime.now(UTC) + timedelta(days=1),
                 ends_at=datetime.now(UTC) + timedelta(days=2))], 1),
    ([grant_rows(revoked_at=datetime.now(UTC))], 1),
    ([grant_rows(class_status="COMPLETED")], 1),
    ([grant_rows(cohort_status="CANCELLED")], 1),
    ([grant_rows(), []], 2),
])
async def test_missing_expired_revoked_completed_or_identityless_grant_denied(
    batches: list[list], expected_reads: int
):
    db = DB(batches)
    assert not await has_live_assessor_class_access(
        cast(AsyncSession, db), actor=actor("ASSESSOR"), class_offering_id=CLASS
    )
    assert len(db.queries) == expected_reads
    assert not db.batches


@pytest.mark.asyncio
async def test_no_role_short_circuits_and_other_class_cannot_use_the_grant():
    no_role = DB([])
    assert not await has_live_assessor_class_access(
        cast(AsyncSession, no_role), actor=actor("CANDIDATE"), class_offering_id=CLASS
    )
    assert no_role.queries == []
    other_class = DB([[]])
    assert not await has_live_assessor_class_access(
        cast(AsyncSession, other_class),
        actor=actor("ASSESSOR"), class_offering_id=SECOND_CLASS
    )
    assert SECOND_CLASS in other_class.queries[0].compile().params.values()


@contextmanager
def as_assessor(db: DB) -> Iterator[TestClient]:
    async def current_actor():
        return actor("ASSESSOR")

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


def test_live_assessor_roster_has_exact_class_scope_without_grade_or_evidence():
    offering = SimpleNamespace(
        id=CLASS, cohort_id=COHORT, title="Authorized class",
        primary_capability_version_id=UUID(int=8410), status="ACTIVE",
    )
    db = DB([
        [(offering, SimpleNamespace(id=COHORT, status="ACTIVE"))],
        [(LEARNER, "CANDIDATE")],
        [],
        grant_rows(),
        [UUID(int=8411)],
    ])
    with as_assessor(db) as client:
        result = client.get(f"/api/v1/class-offerings/{CLASS}/roster")
    assert result.status_code == 200
    assert result.json()["members"] == [
        {"person_id": str(LEARNER), "member_type": "CANDIDATE"}
    ]
    assert result.json()["class_offering_id"] == str(CLASS)
    assert not db.batches


def test_global_assessor_without_grant_cannot_read_roster():
    offering = SimpleNamespace(
        id=CLASS, cohort_id=COHORT, title="Real class",
        primary_capability_version_id=UUID(int=8410), status="ACTIVE",
    )
    db = DB([
        [(offering, SimpleNamespace(id=COHORT, status="ACTIVE"))],
        [(LEARNER, "CANDIDATE")], [], [],
    ])
    with as_assessor(db) as client:
        result = client.get(f"/api/v1/class-offerings/{CLASS}/roster")
    assert result.status_code == 404
    assert not db.batches


def test_live_assessor_reads_real_sessions_and_recorded_attendance_without_mutation():
    offering = SimpleNamespace(id=CLASS, status="ACTIVE")
    cohort = SimpleNamespace(id=COHORT, status="ACTIVE")
    sessions_db = DB([[CLASS], grant_rows(), [UUID(int=8411)], []])
    with as_assessor(sessions_db) as client:
        result = client.get(f"/api/v1/class-offerings/{CLASS}/sessions")
    assert result.status_code == 200 and result.json() == []
    assert not sessions_db.batches

    attendance_db = DB([
        [(SimpleNamespace(id=SESSION), offering, cohort)],
        grant_rows(), [UUID(int=8411)], [],
    ])
    with as_assessor(attendance_db) as client:
        result = client.get(f"/api/v1/sessions/{SESSION}/attendance")
        forbidden = client.post(
            f"/api/v1/sessions/{SESSION}/attendance/{LEARNER}",
            json={"status": "PRESENT", "expected_version": 0, "idempotency_key": "denied"},
        )
    assert result.status_code == 200
    assert result.json()["items"] == []
    assert forbidden.status_code == 403
    assert not attendance_db.batches


def test_live_assessor_activity_and_private_report_are_class_member_scoped():
    offering = SimpleNamespace(
        id=CLASS, cohort_id=COHORT, status="ACTIVE",
        primary_capability_version_id=UUID(int=8410),
    )
    cohort = SimpleNamespace(id=COHORT, status="ACTIVE", track_code="PM")
    activity_db = DB([
        [(offering, cohort)], [LEARNER], grant_rows(), [UUID(int=8411)],
    ], empty_tail=True)
    with as_assessor(activity_db) as client:
        activity = client.get(f"/api/v1/class-offerings/{CLASS}/activity")
    assert activity.status_code == 200
    assert activity.json()["items"] == []

    report_db = DB([
        [(offering, cohort)], [UUID(int=8411)], grant_rows(), [UUID(int=8412)],
    ], empty_tail=True)
    with as_assessor(report_db) as client:
        report = client.get(f"/api/v1/class-offerings/{CLASS}/report-cards/{LEARNER}")
    assert report.status_code == 200
    assert report.json()["person_id"] == str(LEARNER)
    assert all(item["proof_state"] is None for item in report.json()["subjects"])

    unregistered_member_db = DB([[(offering, cohort)], []])
    with as_assessor(unregistered_member_db) as client:
        denied = client.get(
            f"/api/v1/class-offerings/{CLASS}/report-cards/{UUID(int=8500)}"
        )
    assert denied.status_code == 404
    assert len(unregistered_member_db.queries) == 2
