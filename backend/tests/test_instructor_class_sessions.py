"""Class session reads require assignment and exact organization scope."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.class_sessions_api import class_offering_sessions
from app.errors import AppError
from app.identity.auth import ActorContext
from app.main import app

ORG = UUID(int=201)
PERSON = UUID(int=202)
CLASS = UUID(int=203)
NOW = datetime(2026, 10, 9, tzinfo=UTC)


class FakeResult:
    def __init__(self, values: list):
        self.values = values

    def scalar_one_or_none(self):
        assert len(self.values) <= 1
        return self.values[0] if self.values else None

    def scalars(self):
        return self

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, batches: list[list]):
        self.batches = batches
        self.statements: list = []

    async def execute(self, statement):
        self.statements.append(statement)
        assert self.batches, "Unexpected database read"
        return FakeResult(self.batches.pop(0))


def actor(*roles: str) -> ActorContext:
    return ActorContext(
        actor_id=str(PERSON),
        person_id=PERSON,
        organization_context_id=ORG,
        roles=frozenset(roles),
    )


def test_sessions_contract_is_get_only() -> None:
    path = "/api/v1/class-offerings/{class_offering_id}/sessions"
    assert set(app.openapi()["paths"][path]) == {"get"}
    fields = app.openapi()["components"]["schemas"]["ClassSessionRead"]["properties"]
    assert {"session_id", "class_offering_id", "title", "starts_at", "ends_at",
            "delivery_mode", "status"}.issubset(fields)


@pytest.mark.asyncio
async def test_assigned_instructor_sees_only_real_sessions() -> None:
    session = SimpleNamespace(
        id=UUID(int=204), class_offering_id=CLASS, title="Decision Lab",
        starts_at=NOW, ends_at=NOW, delivery_mode="IN_PERSON",
        status="SCHEDULED",
    )
    db = FakeSession([[CLASS], [UUID(int=205)], [session]])
    result = await class_offering_sessions(
        CLASS, actor("INSTRUCTOR"), cast(AsyncSession, db)
    )
    assert len(result) == 1
    assert result[0].session_id == session.id
    assert result[0].class_offering_id == CLASS
    assert result[0].status == "SCHEDULED"
    assert not db.batches
    params = list(db.statements[0].compile().params.values())
    assert ORG in params and CLASS in params
    assigned = list(db.statements[1].compile().params.values())
    assert PERSON in assigned and CLASS in assigned
    assert CLASS in db.statements[2].compile().params.values()


@pytest.mark.asyncio
async def test_missing_or_cross_org_class_fails_before_assignment_lookup() -> None:
    db = FakeSession([[]])
    with pytest.raises(AppError) as error:
        await class_offering_sessions(
            CLASS, actor("INSTRUCTOR"), cast(AsyncSession, db)
        )
    assert error.value.status_code == 404
    assert len(db.statements) == 1


@pytest.mark.asyncio
async def test_unassigned_instructor_fails_before_session_query() -> None:
    db = FakeSession([[CLASS], []])
    with pytest.raises(AppError) as error:
        await class_offering_sessions(
            CLASS, actor("INSTRUCTOR"), cast(AsyncSession, db)
        )
    assert error.value.status_code == 404
    assert len(db.statements) == 2


@pytest.mark.asyncio
async def test_admin_can_see_org_classes_without_instructor_assignment() -> None:
    db = FakeSession([[CLASS], []])
    assert await class_offering_sessions(
        CLASS, actor("ACADEMY_ADMIN"), cast(AsyncSession, db)
    ) == []
    assert len(db.statements) == 2
