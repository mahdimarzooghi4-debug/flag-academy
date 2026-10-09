"""P23-09B live Assessor class discovery contract and privacy."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.assessor_classes_api import list_my_assessor_classes
from app.identity.auth import ActorContext
from app.main import app

ORG = UUID(int=7101)
PERSON = UUID(int=7102)
CLASS = UUID(int=7103)
COHORT = UUID(int=7104)
NOW = datetime.now(UTC)


def actor() -> ActorContext:
    return ActorContext(
        actor_id=str(PERSON),
        person_id=PERSON,
        organization_context_id=ORG,
        roles=frozenset({"ASSESSOR"}),
    )


class Result:
    def __init__(self, rows: list[object]):
        self.rows = rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class DB:
    def __init__(self, batches: list[list[object]]):
        self.batches = batches
        self.statements: list[object] = []

    async def execute(self, statement):
        self.statements.append(statement)
        assert self.batches, "Unexpected discovery query"
        return Result(self.batches.pop(0))


def row(num: int):
    grant = SimpleNamespace(
        id=UUID(int=num), version=num, starts_at=NOW - timedelta(days=1),
        ends_at=NOW + timedelta(days=2), revoked_at=None,
    )
    offering = SimpleNamespace(id=UUID(int=CLASS.int + num - 1), title="Class A")
    cohort = SimpleNamespace(id=COHORT)
    return grant, offering, cohort


def test_discovery_openapi_is_assessor_only_bounded_read():
    path = app.openapi()["paths"]["/api/v1/me/academy/assessor-classes"]
    assert set(path) == {"get"}
    parameters = {p["name"]: p for p in path["get"]["parameters"]}
    assert parameters["limit"]["schema"]["minimum"] == 1
    assert parameters["limit"]["schema"]["maximum"] == 100
    assert parameters["offset"]["schema"]["minimum"] == 0
    assert "security" in path["get"]


@pytest.mark.asyncio
async def test_authorized_class_page_filters_person_org_live_status_and_window():
    db = DB([[UUID(int=1)], [row(1), row(2)]])
    page = await list_my_assessor_classes(
        actor(), cast(AsyncSession, db), limit=1, offset=4
    )
    assert len(page.items) == 1
    assert page.items[0].class_offering_id == CLASS
    assert page.items[0].cohort_id == COHORT
    assert page.items[0].grant_version == 1
    assert page.next_offset == 5
    membership = set(db.statements[0].compile().params.values())
    assert ORG in membership and PERSON in membership and "ASSESSOR" in membership
    criteria = str(db.statements[1])
    assert "assessor_person_id" in criteria
    assert "revoked_at IS NULL" in criteria
    assert "starts_at <=" in criteria
    assert "ends_at >" in criteria
    assert "cohorts.status" in criteria and "class_offerings.status" in criteria
    params = set(db.statements[1].compile().params.values())
    assert ORG in params and PERSON in params


@pytest.mark.asyncio
async def test_empty_grants_never_fall_back_to_organization_class_catalog():
    db = DB([[UUID(int=1)], []])
    page = await list_my_assessor_classes(
        actor(), cast(AsyncSession, db), limit=50, offset=0
    )
    assert page.items == [] and page.next_offset is None


@pytest.mark.asyncio
async def test_removed_identity_role_skips_private_class_query():
    db = DB([[]])
    page = await list_my_assessor_classes(
        actor(), cast(AsyncSession, db), limit=50, offset=0
    )
    assert page.items == [] and page.next_offset is None
    assert len(db.statements) == 1
