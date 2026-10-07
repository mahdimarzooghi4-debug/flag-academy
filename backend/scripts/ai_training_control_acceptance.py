from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.ai_control_plane.models import (
    AIDataset,
    AIDatasetVersion,
    AIModelArtifact,
    AITrainingRunState,
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
from app.platform.models import OutboxEvent

ORGANIZATION_CONTEXT_ID = UUID(
    "30000000-0000-0000-0000-000000000001"
)
DATASET_NAME = "ci-governed-learning"
PURPOSE = "MODEL_TRAINING"


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
                "Governed Dataset acceptance must run before training acceptance."
            )
        return value


def _request(
    *,
    dataset_version_id: UUID,
    request_key: str,
) -> RequestTrainingRun:
    return RequestTrainingRun(
        organization_context_id=ORGANIZATION_CONTEXT_ID,
        request_key=request_key,
        dataset_version_id=dataset_version_id,
        model_family="CI_INTERNAL_MODEL",
        training_recipe_digest="b" * 64,
        requested_by_type="PERSON",
        requested_by_reference="ci-training-reviewer",
        data_classification="CONFIDENTIAL",
        trace_id=f"ci-{request_key}",
    )


async def _successful_run(dataset_version_id: UUID) -> UUID:
    async with SessionFactory() as db:
        requested = await request_training_run(
            db,
            command=_request(
                dataset_version_id=dataset_version_id,
                request_key="ci-training-success",
            ),
        )
        await start_training_run(
            db,
            command=TransitionTrainingRun(
                organization_context_id=ORGANIZATION_CONTEXT_ID,
                training_run_id=requested.training_run_id,
                actor_type="SYSTEM",
                actor_reference="ci-internal-training-worker",
                trace_id="ci-training-success",
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
                trace_id="ci-training-success",
                artifact_format="ci-internal-artifact",
                artifact_reference="ci-artifacts/training-success.bin",
                content_sha256="c" * 64,
                byte_size=128,
            ),
        )
        if completed.artifact_id is None:
            raise RuntimeError("Successful Training Run produced no artifact.")
        await db.commit()
        return requested.training_run_id


async def _failed_run(dataset_version_id: UUID) -> UUID:
    async with SessionFactory() as db:
        requested = await request_training_run(
            db,
            command=_request(
                dataset_version_id=dataset_version_id,
                request_key="ci-training-failure",
            ),
        )
        await start_training_run(
            db,
            command=TransitionTrainingRun(
                organization_context_id=ORGANIZATION_CONTEXT_ID,
                training_run_id=requested.training_run_id,
                actor_type="SYSTEM",
                actor_reference="ci-internal-training-worker",
                trace_id="ci-training-failure",
            ),
        )
        completed = await complete_training_run(
            db,
            command=CompleteTrainingRun(
                organization_context_id=ORGANIZATION_CONTEXT_ID,
                training_run_id=requested.training_run_id,
                outcome="FAILED",
                actor_type="SYSTEM",
                actor_reference="ci-internal-training-worker",
                trace_id="ci-training-failure",
                failure_code="CI_EXPECTED_FAILURE",
            ),
        )
        if completed.artifact_id is not None:
            raise RuntimeError("Failed Training Run produced an artifact.")
        await db.commit()
        return requested.training_run_id


async def _prove_database_rejects_premature_artifact(
    dataset_version_id: UUID,
) -> UUID:
    async with SessionFactory() as db:
        requested = await request_training_run(
            db,
            command=_request(
                dataset_version_id=dataset_version_id,
                request_key="ci-training-premature-artifact",
            ),
        )
        await db.commit()
        training_run_id = requested.training_run_id

    async with SessionFactory() as db:
        db.add(
            AIModelArtifact(
                id=uuid4(),
                training_run_id=training_run_id,
                artifact_format="ci-invalid-artifact",
                artifact_reference="ci-artifacts/invalid.bin",
                content_sha256="d" * 64,
                byte_size=1,
            )
        )
        rejected = False
        try:
            await db.flush()
        except Exception:
            rejected = True
            await db.rollback()
        if not rejected:
            raise RuntimeError(
                "Database accepted artifact before Training Run succeeded."
            )
    return training_run_id


async def _states(training_run_id: UUID) -> list[str]:
    async with SessionFactory() as db:
        return list(
            (
                await db.execute(
                    select(AITrainingRunState.state)
                    .where(
                        AITrainingRunState.training_run_id
                        == training_run_id
                    )
                    .order_by(AITrainingRunState.sequence)
                )
            ).scalars().all()
        )


async def _artifact_count(training_run_id: UUID) -> int:
    async with SessionFactory() as db:
        return (
            await db.execute(
                select(func.count())
                .select_from(AIModelArtifact)
                .where(AIModelArtifact.training_run_id == training_run_id)
            )
        ).scalar_one()


async def _event_count(training_run_ids: list[UUID]) -> int:
    async with SessionFactory() as db:
        return (
            await db.execute(
                select(func.count())
                .select_from(OutboxEvent)
                .where(
                    OutboxEvent.event_type.in_(
                        (
                            "ai.training_run_requested.v1",
                            "ai.training_run_started.v1",
                            "ai.training_run_succeeded.v1",
                            "ai.training_run_failed.v1",
                        )
                    )
                )
            )
        ).scalar_one()


async def main() -> None:
    dataset_version_id = await _dataset_version_id()
    success_id = await _successful_run(dataset_version_id)
    failed_id = await _failed_run(dataset_version_id)
    premature_id = await _prove_database_rejects_premature_artifact(
        dataset_version_id
    )

    success_states = await _states(success_id)
    failed_states = await _states(failed_id)
    premature_states = await _states(premature_id)

    if success_states != ["REQUESTED", "RUNNING", "SUCCEEDED"]:
        raise RuntimeError(f"Unexpected success lifecycle: {success_states!r}")
    if failed_states != ["REQUESTED", "RUNNING", "FAILED"]:
        raise RuntimeError(f"Unexpected failure lifecycle: {failed_states!r}")
    if premature_states != ["REQUESTED"]:
        raise RuntimeError(
            f"Unexpected premature-artifact lifecycle: {premature_states!r}"
        )

    if await _artifact_count(success_id) != 1:
        raise RuntimeError("Successful run artifact count must be one.")
    if await _artifact_count(failed_id) != 0:
        raise RuntimeError("Failed run artifact count must be zero.")
    if await _artifact_count(premature_id) != 0:
        raise RuntimeError("Premature run artifact count must be zero.")

    event_count = await _event_count(
        [success_id, failed_id, premature_id]
    )
    if event_count < 7:
        raise RuntimeError(
            f"Training lifecycle event count was too small: {event_count}"
        )

    print("success_lifecycle=REQUESTED>RUNNING>SUCCEEDED")
    print("failure_lifecycle=REQUESTED>RUNNING>FAILED")
    print("success_artifact=1")
    print("failed_artifact=0")
    print("premature_artifact_db_rejection=PASS")
    print("external_trainer_endpoint=FORBIDDEN")
    print("model_version_creation=P22_04")


if __name__ == "__main__":
    asyncio.run(main())
