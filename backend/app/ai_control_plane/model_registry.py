from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_control_plane.domain import GovernanceActorType, TrainingRunState
from app.ai_control_plane.models import (
    AIDataset,
    AIDatasetVersion,
    AIModelArtifact,
    AIModelVersion,
    AITrainingRun,
    AITrainingRunState,
)
from app.errors import AppError
from app.platform.events import new_event, record_event


@dataclass(frozen=True)
class ArtifactAttestation:
    content_sha256: str
    byte_size: int


class ArtifactReader(Protocol):
    async def attest(
        self,
        *,
        artifact_reference: str,
    ) -> ArtifactAttestation: ...


class LocalFileArtifactReader:
    async def attest(
        self,
        *,
        artifact_reference: str,
    ) -> ArtifactAttestation:
        if "://" in artifact_reference:
            raise AppError(
                "AI_MODEL_ARTIFACT_REFERENCE_UNSUPPORTED",
                "Local artifact reader does not accept remote references.",
                status_code=422,
            )
        return await asyncio.to_thread(
            _attest_local_file,
            artifact_reference,
        )


@dataclass(frozen=True)
class RegisterModelVersion:
    organization_context_id: UUID
    model_artifact_id: UUID
    semantic_version: str
    actor_type: str
    actor_reference: str
    trace_id: str


@dataclass(frozen=True)
class ModelVersionResult:
    model_version_id: UUID
    model_artifact_id: UUID
    training_run_id: UUID
    dataset_version_id: UUID
    model_family: str
    semantic_version: str
    attestation_sha256: str
    attestation_byte_size: int
    created: bool


def _required_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise AppError(
            "AI_MODEL_REGISTRY_INPUT_INVALID",
            f"{field} is required.",
            status_code=422,
            details={"field": field},
        )
    return normalized


def _actor_type(value: str) -> str:
    normalized = _required_text(value, "actor_type")
    if normalized not in {item.value for item in GovernanceActorType}:
        raise AppError(
            "AI_MODEL_REGISTRY_INPUT_INVALID",
            "actor_type must be PERSON or SYSTEM.",
            status_code=422,
            details={"field": "actor_type"},
        )
    return normalized


def _attest_local_file(artifact_reference: str) -> ArtifactAttestation:
    path = Path(artifact_reference)
    if not path.is_file():
        raise AppError(
            "AI_MODEL_ARTIFACT_UNREADABLE",
            "Model artifact is not a readable local file.",
            status_code=409,
            details={"artifact_reference": artifact_reference},
        )

    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as artifact:
        while chunk := artifact.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)

    return ArtifactAttestation(
        content_sha256=digest.hexdigest(),
        byte_size=size,
    )


def _lock_key(model_artifact_id: UUID) -> int:
    raw = hashlib.sha256(str(model_artifact_id).encode()).digest()[:8]
    return int.from_bytes(raw, byteorder="big", signed=True)


async def _latest_training_state(
    db: AsyncSession,
    *,
    training_run_id: UUID,
) -> AITrainingRunState:
    state = (
        await db.execute(
            select(AITrainingRunState)
            .where(AITrainingRunState.training_run_id == training_run_id)
            .order_by(AITrainingRunState.sequence.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if state is None:
        raise AppError(
            "AI_MODEL_TRAINING_STATE_MISSING",
            "Model artifact Training Run has no lifecycle state.",
            status_code=409,
        )
    return state


def _result(
    version: AIModelVersion,
    *,
    created: bool,
) -> ModelVersionResult:
    return ModelVersionResult(
        model_version_id=version.id,
        model_artifact_id=version.model_artifact_id,
        training_run_id=version.training_run_id,
        dataset_version_id=version.dataset_version_id,
        model_family=version.model_family,
        semantic_version=version.semantic_version,
        attestation_sha256=version.attestation_sha256,
        attestation_byte_size=version.attestation_byte_size,
        created=created,
    )


async def register_model_version(
    db: AsyncSession,
    *,
    command: RegisterModelVersion,
    artifact_reader: ArtifactReader,
) -> ModelVersionResult:
    semantic_version = _required_text(
        command.semantic_version,
        "semantic_version",
    )
    actor_type = _actor_type(command.actor_type)
    actor_reference = _required_text(
        command.actor_reference,
        "actor_reference",
    )
    trace_id = _required_text(command.trace_id, "trace_id")

    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _lock_key(command.model_artifact_id)},
    )

    lineage = (
        await db.execute(
            select(AIModelArtifact, AITrainingRun, AIDatasetVersion, AIDataset)
            .join(
                AITrainingRun,
                AITrainingRun.id == AIModelArtifact.training_run_id,
            )
            .join(
                AIDatasetVersion,
                AIDatasetVersion.id == AITrainingRun.dataset_version_id,
            )
            .join(
                AIDataset,
                AIDataset.id == AIDatasetVersion.dataset_id,
            )
            .where(
                AIModelArtifact.id == command.model_artifact_id,
                AITrainingRun.organization_context_id
                == command.organization_context_id,
                AIDataset.organization_context_id
                == command.organization_context_id,
            )
        )
    ).one_or_none()
    if lineage is None:
        raise AppError(
            "AI_MODEL_ARTIFACT_NOT_FOUND",
            "Model artifact was not found in this organization context.",
            status_code=404,
        )

    artifact, training_run, dataset_version, _dataset = lineage
    state = await _latest_training_state(
        db,
        training_run_id=training_run.id,
    )
    if state.state != TrainingRunState.SUCCEEDED.value:
        raise AppError(
            "AI_MODEL_TRAINING_NOT_SUCCEEDED",
            "Model Version requires a SUCCEEDED Training Run.",
            status_code=409,
            details={"current_state": state.state},
        )

    attestation = await artifact_reader.attest(
        artifact_reference=artifact.artifact_reference,
    )
    if (
        attestation.content_sha256 != artifact.content_sha256
        or attestation.byte_size != artifact.byte_size
    ):
        raise AppError(
            "AI_MODEL_ARTIFACT_ATTESTATION_FAILED",
            "Observed model artifact content does not match the immutable registry.",
            status_code=409,
            details={
                "expected_sha256": artifact.content_sha256,
                "observed_sha256": attestation.content_sha256,
                "expected_byte_size": artifact.byte_size,
                "observed_byte_size": attestation.byte_size,
            },
        )

    existing_for_artifact = (
        await db.execute(
            select(AIModelVersion).where(
                AIModelVersion.model_artifact_id == artifact.id
            )
        )
    ).scalar_one_or_none()
    if existing_for_artifact is not None:
        if existing_for_artifact.semantic_version != semantic_version:
            raise AppError(
                "AI_MODEL_ARTIFACT_ALREADY_REGISTERED",
                "Model artifact is already registered under another semantic version.",
                status_code=409,
                details={
                    "semantic_version": existing_for_artifact.semantic_version,
                },
            )
        return _result(existing_for_artifact, created=False)

    existing_version = (
        await db.execute(
            select(AIModelVersion).where(
                AIModelVersion.model_family == training_run.model_family,
                AIModelVersion.semantic_version == semantic_version,
            )
        )
    ).scalar_one_or_none()
    if existing_version is not None:
        raise AppError(
            "AI_MODEL_VERSION_CONFLICT",
            "Semantic version is already registered for this model family.",
            status_code=409,
            details={
                "model_family": training_run.model_family,
                "semantic_version": semantic_version,
            },
        )

    now = datetime.now(UTC)
    version = AIModelVersion(
        id=uuid4(),
        model_artifact_id=artifact.id,
        training_run_id=training_run.id,
        dataset_version_id=training_run.dataset_version_id,
        model_family=training_run.model_family,
        semantic_version=semantic_version,
        attestation_sha256=attestation.content_sha256,
        attestation_byte_size=attestation.byte_size,
        attested_at=now,
        created_at=now,
    )
    db.add(version)
    await db.flush()

    record_event(
        db,
        new_event(
            event_type="ai.model_version_registered.v1",
            aggregate_type="AIModelVersion",
            aggregate_id=version.id,
            aggregate_version=1,
            actor={"type": actor_type, "id": actor_reference},
            organization_context_id=training_run.organization_context_id,
            data_classification=training_run.data_classification,
            payload={
                "model_version_id": str(version.id),
                "model_artifact_id": str(artifact.id),
                "training_run_id": str(training_run.id),
                "dataset_version_id": str(dataset_version.id),
                "model_family": training_run.model_family,
                "semantic_version": semantic_version,
                "attestation_sha256": attestation.content_sha256,
                "attestation_byte_size": attestation.byte_size,
                "training_recipe_digest": training_run.training_recipe_digest,
            },
            trace_id=trace_id,
        ),
    )

    return _result(version, created=True)
