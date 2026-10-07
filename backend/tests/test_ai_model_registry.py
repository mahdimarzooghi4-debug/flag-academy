from dataclasses import fields
from hashlib import sha256
from pathlib import Path

import pytest

from app.ai_control_plane.model_registry import (
    LocalFileArtifactReader,
    RegisterModelVersion,
)
from app.ai_control_plane.models import AIModelVersion
from app.errors import AppError


def test_model_registration_input_cannot_supply_lineage_facts() -> None:
    names = {field.name for field in fields(RegisterModelVersion)}
    assert names == {
        "organization_context_id",
        "model_artifact_id",
        "semantic_version",
        "actor_type",
        "actor_reference",
        "trace_id",
    }
    for forbidden in (
        "training_run_id",
        "dataset_version_id",
        "model_family",
        "content_sha256",
        "byte_size",
        "artifact_reference",
    ):
        assert forbidden not in names


def test_model_version_persists_attestation_evidence() -> None:
    columns = set(AIModelVersion.__table__.c.keys())
    assert {
        "model_artifact_id",
        "training_run_id",
        "dataset_version_id",
        "model_family",
        "semantic_version",
        "attestation_sha256",
        "attestation_byte_size",
        "attested_at",
        "created_at",
    }.issubset(columns)


@pytest.mark.asyncio
async def test_local_artifact_reader_recomputes_sha256_and_size(
    tmp_path: Path,
) -> None:
    content = b"parcham-model-artifact-v1\x00\x01"
    artifact = tmp_path / "model.bin"
    artifact.write_bytes(content)

    attestation = await LocalFileArtifactReader().attest(
        artifact_reference=str(artifact)
    )

    assert attestation.content_sha256 == sha256(content).hexdigest()
    assert attestation.byte_size == len(content)


@pytest.mark.asyncio
async def test_local_artifact_reader_rejects_remote_reference() -> None:
    with pytest.raises(AppError) as error:
        await LocalFileArtifactReader().attest(
            artifact_reference="https://models.example/model.bin"
        )

    assert error.value.code == "AI_MODEL_ARTIFACT_REFERENCE_UNSUPPORTED"


def test_model_registry_derives_lineage_from_immutable_records() -> None:
    source = Path("app/ai_control_plane/model_registry.py").read_text()
    register = source.split("async def register_model_version", 1)[1]

    assert "AIModelArtifact.id == command.model_artifact_id" in register
    assert "AITrainingRun.id == AIModelArtifact.training_run_id" in register
    assert "AIDatasetVersion.id == AITrainingRun.dataset_version_id" in register
    assert "AIDataset.organization_context_id" in register
    assert "TrainingRunState.SUCCEEDED.value" in register

    constructor = register.split("version = AIModelVersion(", 1)[1].split(
        "db.add(version)", 1
    )[0]
    assert "model_artifact_id=artifact.id" in constructor
    assert "training_run_id=training_run.id" in constructor
    assert "dataset_version_id=training_run.dataset_version_id" in constructor
    assert "model_family=training_run.model_family" in constructor


def test_model_registry_requires_live_artifact_attestation() -> None:
    source = Path("app/ai_control_plane/model_registry.py").read_text()
    register = source.split("async def register_model_version", 1)[1]

    assert "await artifact_reader.attest(" in register
    assert "attestation.content_sha256 != artifact.content_sha256" in register
    assert "attestation.byte_size != artifact.byte_size" in register
    assert "AI_MODEL_ARTIFACT_ATTESTATION_FAILED" in register
    assert 'event_type="ai.model_version_registered.v1"' in register
    assert "await db.commit()" not in register


def test_model_registry_has_no_external_provider_or_runtime() -> None:
    source = Path("app/ai_control_plane/model_registry.py").read_text().lower()

    for forbidden in (
        "openai",
        "anthropic",
        "httpx",
        "requests.",
        "boto",
        "endpoint_url",
        "api_key",
        "provider_token",
        "transformers",
        "torch",
        "peft",
        "safetensors",
        "generate(",
    ):
        assert forbidden not in source


def test_model_registry_database_enforces_exact_lineage_and_attestation() -> None:
    migration = Path(
        "alembic/versions/0027_model_registry_artifact_attestation.py"
    ).read_text()

    assert "require_valid_model_version_lineage" in migration
    assert "model version requires SUCCEEDED Training Run" in migration
    assert "model version Training Run lineage mismatch" in migration
    assert "model version Dataset Version lineage mismatch" in migration
    assert "model version model family lineage mismatch" in migration
    assert "model version artifact digest mismatch" in migration
    assert "model version artifact byte size mismatch" in migration
    assert "BEFORE INSERT ON ai_control_plane.model_versions" in migration
    assert "cannot add artifact attestation to existing Model Versions" in migration


def test_model_registry_keeps_context_local_foreign_keys() -> None:
    targets = {
        fk.target_fullname
        for fk in AIModelVersion.__table__.foreign_keys
    }
    assert targets == {
        "ai_control_plane.model_artifacts.id",
        "ai_control_plane.training_runs.id",
        "ai_control_plane.dataset_versions.id",
    }
