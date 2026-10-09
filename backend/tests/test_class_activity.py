"""Class activity read-model contract and role scope tests."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.activity_api import class_activity
from app.errors import AppError
from app.identity.auth import ActorContext
from app.main import app

ORG = UUID("61000000-0000-0000-0000-000000000001")
CLASS = UUID("61000000-0000-0000-0000-000000000002")
COHORT = UUID("61000000-0000-0000-0000-000000000003")
CANDIDATE = UUID("61000000-0000-0000-0000-000000000004")
OTHER_CANDIDATE = UUID("61000000-0000-0000-0000-000000000005")
INSTRUCTOR = UUID("61000000-0000-0000-0000-000000000006")
ASSESSOR = UUID("61000000-0000-0000-0000-000000000007")
NOW = datetime(2026, 10, 8, 10, tzinfo=UTC)


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


class FakeSession:
    def __init__(self, results: list[list]):
        self.results = list(results)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        assert self.results, "Unexpected extra database read"
        return FakeResult(self.results.pop(0))


def actor(person: UUID, *roles: str, org: UUID = ORG) -> ActorContext:
    return ActorContext(
        actor_id=str(person),
        person_id=person,
        organization_context_id=org,
        roles=frozenset(roles),
    )


def class_rows() -> list:
    return [(SimpleNamespace(id=CLASS), SimpleNamespace(id=COHORT))]


def test_class_activity_contract_is_get_only_and_non_sensitive() -> None:
    path = "/api/v1/class-offerings/{class_offering_id}/activity"
    paths = app.openapi()["paths"]
    assert set(paths[path]) == {"get"}
    schemas = app.openapi()["components"]["schemas"]
    props = schemas["ClassActivityItem"]["properties"]
    assert {
        "source_type",
        "source_id",
        "source_parent_id",
        "person_id",
        "class_offering_id",
        "capability_version_id",
        "session_id",
        "occurred_at",
        "state",
    }.issubset(props)
    for forbidden in ("feedback_text", "response_text", "reasoning", "grade", "score"):
        assert forbidden not in props


@pytest.mark.asyncio
async def test_candidate_sees_only_own_source_linked_activity_and_real_attendance() -> None:
    unit = SimpleNamespace(id=UUID(int=21), capability_version_id=UUID(int=22))
    progress = SimpleNamespace(
        id=UUID(int=23), candidate_id=CANDIDATE, updated_at=NOW, state="IN_PROGRESS"
    )
    class_session = SimpleNamespace(id=UUID(int=24))
    attendance = SimpleNamespace(
        id=UUID(int=25),
        person_id=CANDIDATE,
        status="PRESENT",
        updated_at=NOW + timedelta(minutes=1),
    )
    db = FakeSession(
        [
            class_rows(),
            [CANDIDATE, OTHER_CANDIDATE],
            [(progress, unit)],
            [],
            [],
            [],
            [],
            [(attendance, class_session)],
        ]
    )
    response = await class_activity(CLASS, actor(CANDIDATE, "CANDIDATE"), cast(AsyncSession, db), limit=50)

    assert [item.source_type for item in response.items] == [
        "ATTENDANCE_RECORD",
        "LEARNING_UNIT_PROGRESS",
    ]
    assert {item.person_id for item in response.items} == {CANDIDATE}
    assert response.items[0].session_id == class_session.id
    assert response.items[0].state == "PRESENT"
    assert response.items[1].source_parent_id == unit.id
    assert response.items[1].capability_version_id == unit.capability_version_id
    assert response.is_truncated is False
    assert not db.results

    # Each source read must bind the *authorized* person, not all cohort members.
    for stmt in db.statements[2:]:
        params = stmt.compile().params.values()
        assert [CANDIDATE] in params
        assert [OTHER_CANDIDATE] not in params
    class_statement = db.statements[0]
    assert ORG in class_statement.compile().params.values()


@pytest.mark.asyncio
async def test_admin_can_read_bounded_class_activity_but_not_other_classes() -> None:
    own = SimpleNamespace(
        id=UUID(int=30), candidate_id=CANDIDATE, updated_at=NOW, state="COMPLETED"
    )
    other = SimpleNamespace(
        id=UUID(int=31),
        candidate_id=OTHER_CANDIDATE,
        updated_at=NOW + timedelta(seconds=1),
        state="IN_PROGRESS",
    )
    unit = SimpleNamespace(id=UUID(int=32), capability_version_id=UUID(int=33))
    db = FakeSession(
        [
            class_rows(),
            [CANDIDATE, OTHER_CANDIDATE],
            [(other, unit), (own, unit)],
            [],
            [],
            [],
            [],
            [],
        ]
    )
    response = await class_activity(CLASS, actor(INSTRUCTOR, "ACADEMY_ADMIN"), cast(AsyncSession, db), limit=1)
    assert len(response.items) == 1
    assert response.items[0].person_id == OTHER_CANDIDATE
    assert response.is_truncated is True
    assert [CANDIDATE, OTHER_CANDIDATE] in db.statements[2].compile().params.values()


@pytest.mark.asyncio
async def test_unassigned_instructor_and_global_assessor_fail_closed() -> None:
    instructor_db = FakeSession([class_rows(), [CANDIDATE], []])
    with pytest.raises(AppError) as instructor_error:
        await class_activity(CLASS, actor(INSTRUCTOR, "INSTRUCTOR"), cast(AsyncSession, instructor_db), limit=50)
    assert instructor_error.value.status_code == 404
    assert len(instructor_db.statements) == 3

    assessor_db = FakeSession([class_rows(), []])
    with pytest.raises(AppError) as assessor_error:
        await class_activity(CLASS, actor(ASSESSOR, "ASSESSOR"), cast(AsyncSession, assessor_db), limit=50)
    assert assessor_error.value.status_code == 404
    assert len(assessor_db.statements) == 2


@pytest.mark.asyncio
async def test_cross_tenant_class_rejected_before_any_activity_read() -> None:
    db = FakeSession([[]])
    with pytest.raises(AppError) as error:
        await class_activity(CLASS, actor(INSTRUCTOR, "ACADEMY_ADMIN"), cast(AsyncSession, db), limit=50)
    assert error.value.status_code == 404
    assert len(db.statements) == 1
    assert ORG in db.statements[0].compile().params.values()


def test_activity_provenance_does_not_invent_mission_link_or_formal_proof() -> None:
    source = Path("app/academy/activity_api.py").read_text()
    assert "LearningUnit.class_offering_id == class_offering_id" in source
    assert "Assignment.class_offering_id == class_offering_id" in source
    assert "Session.class_offering_id == class_offering_id" in source
    assert "AttendanceRecord.organization_context_id" in source
    for forbidden in (
        "MissionAssignment(",
        "MissionInstance(",
        "db.add(",
        "db.commit(",
        "record_event(",
        "CapabilityClaim",
        "GateAssessment(",
    ):
        assert forbidden not in source
