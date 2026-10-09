"""Candidate class discovery must never reveal other cohort or tenant classes."""

from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.academy.candidate_class_api import candidate_cohort_class_offerings
from app.errors import AppError
from app.identity.auth import ActorContext
from app.main import app

ORG = UUID(int=101)
PERSON = UUID(int=102)
COHORT = UUID(int=103)
CLASS = UUID(int=104)
CAPABILITY_VERSION = UUID(int=105)


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
    def __init__(self, results: list[list]):
        self.results = results
        self.statements: list = []

    async def execute(self, stmt):
        self.statements.append(stmt)
        assert self.results
        return FakeResult(self.results.pop(0))


def actor() -> ActorContext:
    return ActorContext(
        actor_id=str(PERSON),
        person_id=PERSON,
        organization_context_id=ORG,
        roles=frozenset({"CANDIDATE"}),
    )


def test_candidate_class_discovery_openapi_is_get_only() -> None:
    path = "/api/v1/cohorts/{cohort_id}/class-offerings"
    assert set(app.openapi()["paths"][path]) == {"get"}
    schema = app.openapi()["components"]["schemas"]["CandidateClassOfferingResponse"]
    assert {
        "class_offering_id", "cohort_id", "title",
        "primary_capability_version_id", "status",
    }.issubset(schema["properties"])


@pytest.mark.asyncio
async def test_candidate_lists_real_classes_even_without_learning_tasks() -> None:
    offering = SimpleNamespace(
        id=CLASS, cohort_id=COHORT, title="Decision Lab",
        primary_capability_version_id=CAPABILITY_VERSION, status="ACTIVE",
    )
    db = FakeSession([[UUID(int=106)], [offering]])
    items = await candidate_cohort_class_offerings(
        COHORT, actor(), cast(AsyncSession, db)
    )
    assert len(items) == 1
    assert items[0].class_offering_id == CLASS
    assert items[0].title == "Decision Lab"
    assert not db.results
    membership_params = list(db.statements[0].compile().params.values())
    assert COHORT in membership_params
    assert ORG in membership_params
    assert PERSON in membership_params
    assert "CANDIDATE" in membership_params
    assert COHORT in db.statements[1].compile().params.values()


@pytest.mark.asyncio
async def test_other_cohort_is_concealed_before_listing_classes() -> None:
    db = FakeSession([[]])
    with pytest.raises(AppError) as error:
        await candidate_cohort_class_offerings(COHORT, actor(), cast(AsyncSession, db))
    assert error.value.status_code == 404
    assert error.value.code == "COHORT_NOT_FOUND"
    assert len(db.statements) == 1
    assert db.results == []
