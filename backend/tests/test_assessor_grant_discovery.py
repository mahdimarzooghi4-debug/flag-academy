"""P23-09: admin grant discovery never crosses class/tenant boundaries."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.assessor_grants_api import list_assessor_class_grants
from app.errors import AppError
from app.identity.auth import ActorContext
from app.main import app

ORG, CLASS, ADMIN = UUID(int=9101), UUID(int=9102), UUID(int=9103)
NOW = datetime(2026, 10, 9, tzinfo=UTC)


def actor() -> ActorContext:
    return ActorContext(
        actor_id=str(ADMIN), person_id=ADMIN,
        organization_context_id=ORG,
        roles=frozenset({"ACADEMY_ADMIN"}),
    )


class Result:
    def __init__(self, rows):
        self.rows = rows

    def first(self):
        return self.rows[0] if self.rows else None

    def scalars(self):
        return self

    def all(self):
        return self.rows


class DB:
    def __init__(self, batches):
        self.batches = list(batches)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        assert self.batches, "Unexpected read"
        return Result(self.batches.pop(0))


def item(n):
    return SimpleNamespace(
        id=UUID(int=n), version=n, organization_context_id=ORG,
        class_offering_id=CLASS, assessor_person_id=UUID(int=n + 100),
        starts_at=NOW, ends_at=NOW + timedelta(days=2),
        revoked_at=None,
    )


def test_discovery_contract_is_get_only_and_bounded():
    route = "/api/v1/admin/academy/classes/{class_offering_id}/assessor-grants"
    assert set(app.openapi()["paths"][route]) == {"get", "post"}
    op = app.openapi()["paths"][route]["get"]
    params = {p["name"]: p for p in op["parameters"]}
    assert params["limit"]["schema"]["minimum"] == 1
    assert params["limit"]["schema"]["maximum"] == 100
    assert params["offset"]["schema"]["minimum"] == 0


@pytest.mark.asyncio
async def test_list_is_tenant_scoped_and_paginated():
    cls = SimpleNamespace(id=CLASS, status="ACTIVE")
    cohort = SimpleNamespace(status="ACTIVE")
    db = DB([[(cls, cohort)], [item(1), item(2)]])
    response = await list_assessor_class_grants(
        CLASS, actor(), cast(AsyncSession, db), limit=1, offset=5
    )
    assert [x.grant_id for x in response.items] == [UUID(int=1)]
    assert response.next_offset == 6
    assert len(db.statements) == 2
    first, second = [set(stmt.compile().params.values()) for stmt in db.statements]
    assert ORG in first and CLASS in first
    assert ORG in second and CLASS in second


@pytest.mark.asyncio
async def test_cross_tenant_class_hidden_before_grants_read():
    db = DB([[]])
    with pytest.raises(AppError) as error:
        await list_assessor_class_grants(
            CLASS, actor(), cast(AsyncSession, db), limit=25, offset=0
        )
    assert error.value.status_code == 404
    assert len(db.statements) == 1


@pytest.mark.asyncio
async def test_empty_class_grants_are_not_inferred():
    cls = SimpleNamespace(id=CLASS, status="ACTIVE")
    cohort = SimpleNamespace(status="ACTIVE")
    db = DB([[(cls, cohort)], []])
    data = await list_assessor_class_grants(
        CLASS, actor(), cast(AsyncSession, db), limit=25, offset=0
    )
    assert data.items == [] and data.next_offset is None
