"""Existing Evidence org-wide APIs must fail closed for private classroom sources."""

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.evidence.api import (
    CLASSROOM_SOURCE_CONTEXT,
    _load_case,
    get_evidence_case,
    list_evidence_cases,
    list_my_evidence_cases,
)
from app.evidence.models import EvidenceCase
from app.identity.auth import ActorContext

ORG = UUID(int=10011)
ASSESSOR = UUID(int=10012)
CANDIDATE = UUID(int=10013)


class Result:
    def __init__(self, item: object | None = None) -> None:
        self.item = item

    def scalar_one_or_none(self) -> object | None:
        return self.item

    def scalars(self) -> "Result":
        return self

    def all(self) -> list[object]:
        return []


class FakeSession:
    def __init__(self, item: object | None = None) -> None:
        self.item = item
        self.sql: list[str] = []
        self.params: list[dict] = []

    async def execute(self, statement) -> Result:
        compiled = statement.compile()
        self.sql.append(str(compiled))
        self.params.append(dict(compiled.params))
        return Result(self.item)


def actor(person: UUID = ASSESSOR, role: str = "ASSESSOR") -> ActorContext:
    return ActorContext(
        actor_id=str(person), person_id=person,
        organization_context_id=ORG, roles=frozenset([role]),
    )


def classroom_case() -> EvidenceCase:
    return EvidenceCase(
        id=UUID(int=10015),
        organization_context_id=ORG,
        subject_person_id=CANDIDATE,
        source_observation_id=UUID(int=10016),
        source_context=CLASSROOM_SOURCE_CONTEXT,
    )


@pytest.mark.asyncio
async def test_generic_evidence_detail_denies_classroom_case_by_id() -> None:
    case = classroom_case()
    for invoke in ("direct", "get"):
        db = FakeSession(case)
        with pytest.raises(AppError) as exc:
            if invoke == "direct":
                await _load_case(
                    cast(AsyncSession, db), actor=actor(), case_id=case.id,
                )
            else:
                await get_evidence_case(
                    case.id, actor(), cast(AsyncSession, db),
                )
        assert exc.value.code == "EVIDENCE_CASE_NOT_FOUND"
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_generic_assessor_listing_filters_private_classroom_source_in_sql() -> None:
    db = FakeSession()
    assert await list_evidence_cases(actor(), cast(AsyncSession, db)) == []
    assert len(db.sql) == 1
    assert "source_context !=" in db.sql[0]
    assert CLASSROOM_SOURCE_CONTEXT in db.params[0].values()
    assert ORG in db.params[0].values()


@pytest.mark.asyncio
async def test_generic_candidate_listing_also_does_not_implicitly_publish_draft() -> None:
    db = FakeSession()
    assert await list_my_evidence_cases(
        actor(CANDIDATE, "CANDIDATE"), cast(AsyncSession, db),
    ) == []
    assert len(db.sql) == 1
    assert "source_context !=" in db.sql[0]
    assert CLASSROOM_SOURCE_CONTEXT in db.params[0].values()
    assert ORG in db.params[0].values()
    assert CANDIDATE in db.params[0].values()


@pytest.mark.asyncio
async def test_other_existing_evidence_sources_keep_prior_detail_lookup() -> None:
    case = classroom_case()
    case.source_context = "MISSION_RUNTIME"
    db = FakeSession(case)
    result = await _load_case(cast(AsyncSession, db), actor=actor(), case_id=case.id)
    assert result is case
