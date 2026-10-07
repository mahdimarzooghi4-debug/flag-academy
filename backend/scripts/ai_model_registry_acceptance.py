from __future__ import annotations

import asyncio
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select

from app.ai_control_plane.model_registry import (
    LocalFileArtifactReader,
    RegisterModelVersion,
    register_model_version,
)
from app.ai_control_plane.models import (
    AIDataset,
    AIDatasetVersion,
    AIModelVersion,
)
from app.ai_control_plane.training import (
    CompleteTrainingRun,
    RequestTrainingRun,
    TransitionTrainingRun,
    complete_training_run,
    request_training_run,
    start_training_run,
)
from app.db import SessionFactory
from app.errors import AppError
from app.platform.models import OutboxEvent

ORGANIZATION_CONTEXT_ID = UUID(
    "30000000-0000-0000-0000-000000000001"
)
DATASET_NAME = "ci-governed-learning"
PURPOSE = "MODEL_TRAINING"
ARTIFACT_PATH = Path("/tmp/parcham-ci-model-registry.bin")
ARTIFACT_CONTENT = b"parcham-ci-model-registry-v1\x00\x01\x02"


async def _dataset_version_id() -> UUID:
    async with SessionFactory() as db:
        value = (
            await db.execute(
                select(AIDatasetVersion.id)
                .join(
                    AIDataset,
                    AIDataset.id == AIDatasetVersion.dataset_id,
                )
                .where(
                    AIDataset.organization_context_id
                    == ORGANIZATION_CONTEXT_ID,
                    AIDataset.name == DATASET_NAME,
                    AIDataset.purpose == PURPOSE,
                )
                .order_by(AIDatasetVersion.version_number.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if value is None:
            raise RuntimeError(
                "Governed Dataset acceptance must run before model registry acceptance."
            )
        return value


async def _create_successful_training_run(
    dataset_version_id: UUID,
) -> tuple[UUID, UUID]:
    ARTIFACT_PATH.write_bytes(ARTIFACT_CONTENT)
    digest = sha256(ARTIFACT_CONTENT).hexdigest()

    async with SessionFactory() as db:
        requested = await request_training_run(
            db,
            command=RequestTrainingRun(
                organization_context_id=ORGANIZATION_CONTEXT_ID,
                request_key="ci-model-registry-training",
                dataset_version_id=dataset_version_id,
                model_family="CI_INTERNAL_MODEL_REGISTRY",
                training_recipe_digest="e" * 64,
                requested_by_type="PERSON",
                requested_by_reference="ci-model-registry-reviewer",
                data_classification="CONFIDENTIAL",
                trace_id="ci-model-registry-training",
            ),
        )
        await start_training_run(
            db,
            command=TransitionTrainingRun(
                organization_context_id=ORGANIZATION_CONTEXT_ID,
                training_run_id=requested.training_run_id,
                actor_type="SYSTEM",
                actor_reference="ci-internal-training-worker",
                trace_id="ci-model-registry-training",
            ),
        )
        completed = await complete_training_run(
            db,
            command=CompleteTrainingRun(
                organization_context_id=ORGANIZATION_CONTEXT_ID,
                training_run_id=requested.training_run_id,
                outcome="SUCCEEDED",
                actor_type="SYSTEM",
                actor_reference="ci-internal-training-worker",
                trace_id="ci-model-registry-training",
                artifact_format="ci-binary",
                artifact_reference=str(ARTIFACT_PATH),
                content_sha256=digest,
                byte_size=len(ARTIFACT_CONTENT),
            ),
        )
        if completed.artifact_id is None:
            raise RuntimeError("Successful Training Run produced no artifact.")
        await db.commit()
        return requested.training_run_id, completed.artifact_id


def _register_command(model_artifact_id: UUID) -> RegisterModelVersion:
    return RegisterModelVersion(
        organization_context_id=ORGANIZATION_CONTEXT_ID,
        model_artifact_id=model_artifact_id,
        semantic_version="ci-v1",
        actor_type="PERSON",
        actor_reference="ci-model-registry-reviewer",
        trace_id="ci-model-registry",
    )


async def _register(model_artifact_id: UUID) -> UUID:
    reader = LocalFileArtifactReader()
    async with SessionFactory() as db:
        result = await register_model_version(
            db,
            command=_register_command(model_artifact_id),
            artifact_reader=reader,
        )
        if not result.created:
            raise RuntimeError("Initial Model Version registration was not created.")
        if result.attestation_sha256 != sha256(ARTIFACT_CONTENT).hexdigest():
            raise RuntimeError("Model Version attestation SHA-256 mismatch.")
        if result.attestation_byte_size != len(ARTIFACT_CONTENT):
            raise RuntimeError("Model Version attestation byte size mismatch.")
        await db.commit()
        return result.model_version_id


async def _prove_idempotent_retry(
    model_artifact_id: UUID,
    model_version_id: UUID,
) -> None:
    async with SessionFactory() as db:
        result = await register_model_version(
            db,
            command=_register_command(model_artifact_id),
            artifact_reader=LocalFileArtifactReader(),
        )
        if result.created:
            raise RuntimeError("Model Version retry created a duplicate.")
        if result.model_version_id != model_version_id:
            raise RuntimeError("Model Version retry changed identity.")
        await db.rollback()


async def _prove_mutation_fails_closed(model_artifact_id: UUID) -> None:
    ARTIFACT_PATH.write_bytes(ARTIFACT_CONTENT + b"tampered")

    async with SessionFactory() as db:
        try:
            await register_model_version(
                db,
                command=_register_command(model_artifact_id),
                artifact_reader=LocalFileArtifactReader(),
            )
        except AppError as error:
            await db.rollback()
            if error.code != "AI_MODEL_ARTIFACT_ATTESTATION_FAILED":
                raise
        else:
            raise RuntimeError(
                "Mutated artifact passed Model Registry attestation."
            )


async def _counts(
    *,
    training_run_id: UUID,
    model_version_id: UUID,
) -> tuple[int, int]:
    async with SessionFactory() as db:
        versions = (
            await db.execute(
                select(func.count())
                .select_from(AIModelVersion)
                .where(AIModelVersion.id == model_version_id)
            )
        ).scalar_one()
        events = (
            await db.execute(
                select(func.count())
                .select_from(OutboxEvent)
                .where(
                    OutboxEvent.event_type
                    == "ai.model_version_registered.v1"
                )
            )
        ).scalar_one()
        training_lineage = (
            await db.execute(
                select(AIModelVersion.training_run_id).where(
                    AIModelVersion.id == model_version_id
                )
            )
        ).scalar_one()
        if training_lineage != training_run_id:
            raise RuntimeError("Model Version Training Run lineage mismatch.")
        return versions, events


async def main() -> None:
    dataset_version_id = await _dataset_version_id()
    training_run_id, artifact_id = await _create_successful_training_run(
        dataset_version_id
    )
    model_version_id = await _register(artifact_id)
    await _prove_idempotent_retry(artifact_id, model_version_id)
    await _prove_mutation_fails_closed(artifact_id)

    versions, events = await _counts(
        training_run_id=training_run_id,
        model_version_id=model_version_id,
    )
    if versions != 1:
        raise RuntimeError(f"Expected one Model Version, got {versions}.")
    if events < 1:
        raise RuntimeError("Model Version registration event is missing.")

    print("artifact_sha256_recomputed=PASS")
    print("artifact_byte_size_recomputed=PASS")
    print("model_version_lineage=PASS")
    print("idempotent_registration=PASS")
    print("artifact_mutation_fail_closed=PASS")
    print("external_model_registration=FORBIDDEN")
    print("runtime_activation=NOT_IMPLEMENTED")


if __name__ == "__main__":
    asyncio.run(main())
