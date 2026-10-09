"""Admin Academy catalog contracts, paging, and tenant/role isolation."""

from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.admin_operations_api import (
    admin_academy_cohort_classes,
    admin_academy_cohorts,
)
from app.errors import AppError
from app.identity.auth import ActorContext
from app.main import app

ORG = UUID(int=3001)
COHORT = UUID(int=3002)
CLASS = UUID(int=3003)
ADMIN = UUID(int=3004)
OTHER = UUID(int=3005)


class FakeResult:
    def __init__(self, rows: list):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        assert len(self.rows) <= 1
        return self.rows[0] if self.rows else None


class FakeSession:
    def __init__(self, batches: list[list]):
        self.batches = batches
        self.statements = []

    async def execute(self, query):
        self.statements.append(query)
        assert self.batches, "Unexpected database read"
        return FakeResult(self.batches.pop(0))


def actor(role: str = "ACADEMY_ADMIN") -> ActorContext:
    return ActorContext(
        actor_id=str(ADMIN),
        person_id=ADMIN,
        organization_context_id=ORG,
        roles=frozenset({role}),
    )


def cohort(code: str, ident: UUID = COHORT):
    return SimpleNamespace(
        id=ident,
        code=code,
        name="Verified cohort",
        track_code="PRODUCT",
        status="ACTIVE",
    )


def offering(ident: UUID = CLASS):
    return SimpleNamespace(
        id=ident, cohort_id=COHORT, title="Real class",
        primary_capability_version_id=UUID(int=3006), status="ACTIVE",
    )


def test_admin_catalog_is_get_only_and_paging_bounded() -> None:
    paths = app.openapi()["paths"]
    assert set(paths["/api/v1/admin/academy/cohorts"]) == {"get"}
    assert set(paths["/api/v1/admin/academy/cohorts/{cohort_id}/classes"]) == {"get"}
    for path in (
        "/api/v1/admin/academy/cohorts",
        "/api/v1/admin/academy/cohorts/{cohort_id}/classes",
    ):
        operation = paths[path]["get"]
        query = {p["name"]: p for p in operation["parameters"] if p["in"] == "query"}
        assert query["limit"]["schema"]["maximum"] == 100
        assert query["limit"]["schema"]["minimum"] == 1
        assert query["offset"]["schema"]["minimum"] == 0


@pytest.mark.asyncio
async def test_only_real_org_cohorts_are_returned_with_explicit_next_page() -> None:
    db = FakeSession([[cohort("A"), cohort("B", OTHER)]])
    response = await admin_academy_cohorts(
        actor(), cast(AsyncSession, db), limit=1, offset=20
    )
    assert [x.code for x in response.items] == ["A"]
    assert response.next_offset == 21
    params = list(db.statements[0].compile().params.values())
    assert ORG in params
    assert not db.batches


@pytest.mark.asyncio
async def test_class_discovery_checks_cohort_organization_first() -> None:
    db = FakeSession([[COHORT], [offering(), offering(OTHER)]])
    response = await admin_academy_cohort_classes(
        COHORT, actor(), cast(AsyncSession, db), limit=1, offset=0
    )
    assert len(response.items) == 1
    assert response.items[0].class_offering_id == CLASS
    assert response.next_offset == 1
    params = list(db.statements[0].compile().params.values())
    assert ORG in params and COHORT in params
    assert COHORT in db.statements[1].compile().params.values()
    assert not db.batches


@pytest.mark.asyncio
async def test_other_org_cohort_is_non_disclosing_and_blocks_class_read() -> None:
    db = FakeSession([[]])
    with pytest.raises(AppError) as error:
        await admin_academy_cohort_classes(
            COHORT, actor(), cast(AsyncSession, db), limit=20, offset=0
        )
    assert error.value.status_code == 404
    assert error.value.code == "COHORT_NOT_FOUND"
    assert len(db.statements) == 1
    assert not db.batches


@pytest.mark.asyncio
async def test_empty_org_catalog_and_empty_cohort_are_distinct() -> None:
    empty_org = FakeSession([[]])
    result = await admin_academy_cohorts(
        actor(), cast(AsyncSession, empty_org), limit=20, offset=0
    )
    assert result.items == [] and result.next_offset is None
    empty_classes = FakeSession([[COHORT], []])
    result = await admin_academy_cohort_classes(
        COHORT, actor(), cast(AsyncSession, empty_classes), limit=20, offset=0
    )
    assert result.items == [] and result.next_offset is None
