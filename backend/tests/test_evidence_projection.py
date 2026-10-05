from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence import api as evidence_api
from app.evidence.models import EvidenceCase


class _EmptyScalarResult:
    def scalars(self):
        return self

    def all(self):
        return []


class _FakeDb:
    async def execute(self, _statement):
        return _EmptyScalarResult()


def _case() -> EvidenceCase:
    now = datetime.now(UTC)
    return cast(EvidenceCase, SimpleNamespace(
        id=UUID("90000000-0000-0000-0000-000000000001"),
        version=3,
        organization_context_id=UUID("00000000-0000-0000-0000-000000000001"),
        subject_person_id=UUID("00000000-0000-0000-0000-000000000101"),
        source_observation_id=UUID("90000000-0000-0000-0000-000000000002"),
        source_context="MISSION_RUNTIME",
        source_reference="MISSION_INSTANCE:90000000-0000-0000-0000-000000000003",
        source_runtime_event_id=UUID("90000000-0000-0000-0000-000000000004"),
        observation_type="INTERNAL_WORLD_FACT",
        observed_fact="Canonical source fact.",
        observed_payload={"hidden_world_truth": "SECRET", "safe": "value"},
        candidate_visible=True,
        candidate_visible_payload={"safe": "value"},
        occurred_at=now,
        source_independence_group="MISSION_INSTANCE:90000000-0000-0000-0000-000000000003",
        provenance={"internal": "lineage"},
        integrity_state="SEALED",
        status="DRAFT",
        context_request=None,
        created_at=now,
        updated_at=now,
        accepted_at=None,
        rejected_at=None,
    ))


@pytest.mark.asyncio
async def test_candidate_evidence_response_uses_only_candidate_safe_projection(
    monkeypatch,
) -> None:
    async def no_responses(_db, _case_id):
        return []

    monkeypatch.setattr(evidence_api, "_candidate_responses", no_responses)

    response = await evidence_api._candidate_case_response(
        cast(AsyncSession, _FakeDb()),
        _case(),
    )

    assert response.observed_payload == {"safe": "value"}
    assert "hidden_world_truth" not in response.observed_payload


@pytest.mark.asyncio
async def test_assessor_evidence_response_keeps_canonical_observation_snapshot(
    monkeypatch,
) -> None:
    async def no_responses(_db, _case_id):
        return []

    async def no_interpretation(_db, _case_id):
        return None

    monkeypatch.setattr(evidence_api, "_candidate_responses", no_responses)
    monkeypatch.setattr(evidence_api, "_active_interpretation", no_interpretation)

    response = await evidence_api._full_response(
        cast(AsyncSession, _FakeDb()),
        _case(),
    )

    assert response.observed_payload["hidden_world_truth"] == "SECRET"
    assert response.provenance == {"internal": "lineage"}
