"""Flag Profile public read contract: tenant, person, track, and accepted lineage."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.flag_profile.public_reader import read_candidate_safe_reviewed_claims

ORG = UUID(int=100)
PERSON = UUID(int=101)
CAPABILITY = UUID(int=102)
NOW = datetime(2026, 10, 8, tzinfo=UTC)


class FakeResult:
    def __init__(self, items: list):
        self.items = items

    def scalars(self):
        return self

    def all(self):
        return self.items


class FakeSession:
    def __init__(self, items: list):
        self.items = items
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return FakeResult(self.items)


@pytest.mark.asyncio
async def test_empty_definition_set_does_not_read_profiles() -> None:
    db = FakeSession([])
    value = await read_candidate_safe_reviewed_claims(
        cast(AsyncSession, db),
        organization_context_id=ORG,
        subject_person_id=PERSON,
        track_code="FLAG",
        capability_definition_ids=set(),
    )
    assert value == {}
    assert db.statements == []


@pytest.mark.asyncio
async def test_reviewed_claim_projection_preserves_source_and_scopes() -> None:
    claim = SimpleNamespace(
        id=UUID(int=103),
        version=4,
        capability_id=CAPABILITY,
        state="PROVEN",
        level="L3",
        reviewed_at=NOW,
        reviewed_by=UUID(int=104),
        confidence_in_claim="INTERNAL",
    )
    db = FakeSession([claim])
    result = await read_candidate_safe_reviewed_claims(
        cast(AsyncSession, db),
        organization_context_id=ORG,
        subject_person_id=PERSON,
        track_code="FLAG",
        capability_definition_ids={CAPABILITY},
    )
    public = result[CAPABILITY]
    assert public.claim_id == claim.id
    assert public.claim_version == 4
    assert public.claim_state == "PROVEN"
    assert public.level == "L3"
    assert public.reviewed_at == NOW
    assert not hasattr(public, "reviewed_by")
    assert not hasattr(public, "confidence_in_claim")
    assert len(db.statements) == 1
    params = list(db.statements[0].compile().params.values())
    assert ORG in params
    assert PERSON in params
    assert "FLAG" in params
    assert [CAPABILITY] in params


@pytest.mark.asyncio
async def test_invalid_stored_claim_vocabulary_fails_closed() -> None:
    db = FakeSession([SimpleNamespace(
        id=UUID(int=103), version=1, capability_id=CAPABILITY,
        state="INFERRED", level="L3", reviewed_at=NOW,
    )])
    with pytest.raises(AppError) as error:
        await read_candidate_safe_reviewed_claims(
            cast(AsyncSession, db),
            organization_context_id=ORG,
            subject_person_id=PERSON,
            track_code="FLAG",
            capability_definition_ids={CAPABILITY},
        )
    assert error.value.code == "PROFILE_CLAIM_STATE_INVALID"
    assert error.value.status_code == 409
