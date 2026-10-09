"""Offline, no-GPU tests for the governed Trainer input materializer."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.ai_control_plane.dataset_builder import (
    ApprovedLearningInput,
    approval_provenance_digest,
    dataset_version_digest,
)
from app.ai_control_plane.seed_learning import (
    APPROVAL_AGGREGATE_TYPE,
    load_decision_seed_artifact,
    seed_approval_aggregate_id,
)
from app.ai_control_plane.training_content import materialize_training_dataset
from app.errors import AppError


class Result:
    def __init__(self, value: object) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object:
        return self.value

    def scalars(self) -> Result:
        return self

    def all(self) -> object:
        return self.value


class FakeSession:
    def __init__(self, *values: object) -> None:
        self.values = list(values)

    async def execute(self, statement: object) -> Result:
        del statement
        return Result(self.values.pop(0))


def fixtures() -> tuple[object, ...]:
    org = uuid4()
    run_id = uuid4()
    dataset_id = uuid4()
    version_id = uuid4()
    item_id = uuid4()
    approval_id = uuid4()
    event_id = uuid4()
    reviewer = str(uuid4())
    when = datetime.now(UTC)
    seed = load_decision_seed_artifact()
    approval_command = ApprovedLearningInput(
        organization_context_id=org,
        dataset_name=seed.dataset_name,
        purpose=seed.purpose,
        source_policy_key=seed.source_policy_key,
        source_policy_version=seed.source_policy_version,
        source_type=seed.source_type,
        source_reference=seed.source_reference,
        source_version=seed.source_version,
        source_payload_digest=seed.source_payload_digest,
        approval_reference="reviewed-seed",
        approval_event_id=event_id,
        data_classification=seed.data_classification,
        approved_by_type="PERSON",
        approved_by_reference=reviewer,
        approved_at=when,
        trace_id="local-test",
    )
    provenance = approval_provenance_digest(approval_command)
    digest = dataset_version_digest(
        organization_context_id=org,
        dataset_name=seed.dataset_name,
        purpose=seed.purpose,
        parent_dataset_digest=None,
        provenance_digest=provenance,
    )
    run = SimpleNamespace(id=run_id, dataset_version_id=version_id, model_family="Gemma 4 12B Unified")
    state = SimpleNamespace(state="RUNNING")
    dataset = SimpleNamespace(id=dataset_id, name=seed.dataset_name, purpose=seed.purpose)
    version = SimpleNamespace(
        id=version_id, dataset_id=dataset_id, version_number=1,
        parent_dataset_version_id=None, source_policy_key=seed.source_policy_key,
        source_policy_version=seed.source_policy_version, dataset_digest=digest,
    )
    item = SimpleNamespace(
        id=item_id, position=1, learning_source_approval_id=approval_id,
        approval_reference=approval_command.approval_reference,
        source_type=seed.source_type, source_reference=seed.source_reference,
        source_version=seed.source_version, data_classification=seed.data_classification,
        source_payload_digest=seed.source_payload_digest, provenance_digest=provenance,
    )
    approval = SimpleNamespace(
        approved_by_type="PERSON", approved_by_reference=reviewer,
        approved_at=when, approval_reference=approval_command.approval_reference,
        source_policy_key=seed.source_policy_key,
        source_policy_version=seed.source_policy_version,
        source_type=seed.source_type, source_reference=seed.source_reference,
        source_version=seed.source_version, data_classification=seed.data_classification,
        source_payload_digest=seed.source_payload_digest, provenance_digest=provenance,
        approval_event_id=event_id,
    )
    payload = {
        "dataset_name": seed.dataset_name, "purpose": seed.purpose,
        "source_policy_key": seed.source_policy_key,
        "source_policy_version": seed.source_policy_version,
        "source_type": seed.source_type, "source_reference": seed.source_reference,
        "source_version": seed.source_version,
        "source_payload_digest": seed.source_payload_digest,
        "approval_reference": approval_command.approval_reference,
    }
    event = SimpleNamespace(
        event_id=event_id, actor={"type": "PERSON", "id": reviewer},
        payload=payload, occurred_at=when, trace_id="local-test",
        aggregate_type=APPROVAL_AGGREGATE_TYPE,
        aggregate_id=seed_approval_aggregate_id(org),
        data_classification=seed.data_classification,
    )
    return org, run_id, [run, state, dataset, version, [item], approval, event]


@pytest.mark.asyncio
async def test_materialize_only_human_approved_seed_bytes() -> None:
    org, run_id, values = fixtures()
    result = await materialize_training_dataset(
        FakeSession(*values),  # type: ignore[arg-type]
        organization_context_id=org, training_run_id=run_id,
    )
    assert result.training_run_id == run_id
    assert len(result.items) == 1
    assert result.items[0].content.startswith(b'{"id":"DM-SEED-001"')
    assert result.items[0].source_payload_digest == load_decision_seed_artifact().source_payload_digest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("index", "field", "replacement"),
    [
        (0, "model_family", "UNKNOWN"),
        (1, "state", "REQUESTED"),
        (2, "purpose", "MODEL_EVALUATION"),
        (3, "dataset_digest", "0" * 64),
        (4, "position", 7),
        (5, "approved_by_type", "SYSTEM"),
        (5, "source_payload_digest", "0" * 64),
        (6, "aggregate_type", "OtherAggregate"),
        (6, "data_classification", "PUBLIC"),
    ],
)
async def test_materialize_rejects_bad_lineage(
    index: int, field: str, replacement: str | int,
) -> None:
    org, run_id, values = fixtures()
    target = values[index]
    if isinstance(target, list):
        target = target[0]
    setattr(target, field, replacement)
    with pytest.raises(AppError) as exc:
        await materialize_training_dataset(
            FakeSession(*values),  # type: ignore[arg-type]
            organization_context_id=org, training_run_id=run_id,
        )
    assert exc.value.code == "AI_TRAINING_CONTENT_NOT_VERIFIED"


@pytest.mark.asyncio
async def test_materialize_rejects_missing_run_and_missing_event() -> None:
    org, run_id, values = fixtures()
    for index in (0, 6):
        changed = list(values)
        changed[index] = None
        with pytest.raises(AppError, match=""):
            await materialize_training_dataset(
                FakeSession(*changed),  # type: ignore[arg-type]
                organization_context_id=org, training_run_id=run_id,
            )


@pytest.mark.asyncio
async def test_materialize_rejects_missing_source_bytes(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    import app.ai_control_plane.training_content as module

    org, run_id, values = fixtures()
    monkeypatch.setattr(module, "_SEED_BYTES", tmp_path / "missing.jsonl")  # type: ignore[operator]
    with pytest.raises(AppError) as exc:
        await materialize_training_dataset(
            FakeSession(*values),  # type: ignore[arg-type]
            organization_context_id=org, training_run_id=run_id,
        )
    assert exc.value.code == "AI_TRAINING_CONTENT_NOT_VERIFIED"


def test_training_materializer_does_not_expose_http_or_auto_promotion() -> None:
    from pathlib import Path

    source = Path("app/ai_control_plane/training_content.py").read_text()
    assert "await db.commit()" not in source
    assert "APIRouter" not in source
    assert "httpx" not in source
    assert "torch" not in source
    assert "transformers" not in source
