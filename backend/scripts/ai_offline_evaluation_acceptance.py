from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.ai_control_plane.dataset_builder import (
    ApprovedLearningInput,
    ingest_approved_learning_input,
)
from app.ai_control_plane.evaluation import (
    CompleteEvaluationRun,
    LocalFileMetricsArtifactReader,
    RequestEvaluationRun,
    TransitionEvaluationRun,
    complete_evaluation_run,
    request_evaluation_run,
    start_evaluation_run,
)
from app.ai_control_plane.models import (
    AIEvaluationResult,
    AIEvaluationRunState,
    AIModelVersion,
)
from app.db import SessionFactory
from app.errors import AppError
from app.platform.models import OutboxEvent

ORGANIZATION_CONTEXT_ID = UUID(
    "30000000-0000-0000-0000-000000000001"
)
EVALUATION_DATASET_NAME = "ci-governed-evaluation"
EVALUATION_PURPOSE = "MODEL_EVALUATION"
MODEL_FAMILY = "CI_INTERNAL_MODEL_REGISTRY"
SEMANTIC_VERSION = "ci-v1"
METRICS_PATH = Path("/tmp/parcham-ci-offline-evaluation.json")
METRICS_CONTENT = b'{"evaluation":"ci","status":"evidence-only"}\n'


async def _model_version() -> AIModelVersion:
    async with SessionFactory() as db:
        model = (
            await db.execute(
                select(AIModelVersion).where(
                    AIModelVersion.model_family == MODEL_FAMILY,
                    AIModelVersion.semantic_version == SEMANTIC_VERSION,
                )
            )
        ).scalar_one_or_none()
        if model is None:
            raise RuntimeError(
                "Model Registry acceptance must run before Offline Evaluation acceptance."
            )
        return model


async def _evaluation_dataset_version_id() -> UUID:
    async with SessionFactory() as db:
        result = await ingest_approved_learning_input(
            db,
            command=ApprovedLearningInput(
                organization_context_id=ORGANIZATION_CONTEXT_ID,
                dataset_name=EVALUATION_DATASET_NAME,
                purpose=EVALUATION_PURPOSE,
                source_policy_key="ci-evaluation-policy-input",
                source_policy_version="v1",
                source_type="CI_GOVERNED_EVALUATION_SOURCE",
                source_reference="ci-evaluation-source:1",
                source_version="1",
                source_payload_digest="f" * 64,
                approval_reference="ci-evaluation-approval-1",
                approval_event_id=UUID(
                    "50000000-0000-0000-0000-000000000001"
                ),
                data_classification="CONFIDENTIAL",
                approved_by_type="PERSON",
                approved_by_reference="ci-evaluation-data-reviewer",
                approved_at=datetime(2026, 10, 7, 12, 0, tzinfo=UTC),
                trace_id="ci-evaluation-dataset",
            ),
        )
        await db.commit()
        return result.dataset_version_id


def _request(
    *,
    model_version_id: UUID,
    evaluation_dataset_version_id: UUID,
    request_key: str,
) -> RequestEvaluationRun:
    return RequestEvaluationRun(
        organization_context_id=ORGANIZATION_CONTEXT_ID,
        request_key=request_key,
        model_version_id=model_version_id,
        evaluation_dataset_version_id=evaluation_dataset_version_id,
        evaluation_policy_key="ci-offline-evaluation",
        evaluation_policy_version="v1",
        requested_by_type="PERSON",
        requested_by_reference="ci-evaluation-reviewer",
        data_classification="CONFIDENTIAL",
        trace_id=f"ci-{request_key}",
    )


async def _successful_run(
    *,
    model_version_id: UUID,
    evaluation_dataset_version_id: UUID,
) -> UUID:
    METRICS_PATH.write_bytes(METRICS_CONTENT)
    digest = sha256(METRICS_CONTENT).hexdigest()

    async with SessionFactory() as db:
        requested = await request_evaluation_run(
            db,
            command=_request(
                model_version_id=model_version_id,
                evaluation_dataset_version_id=evaluation_dataset_version_id,
                request_key="ci-evaluation-success",
            ),
        )
        replay = await request_evaluation_run(
            db,
            command=_request(
                model_version_id=model_version_id,
                evaluation_dataset_version_id=evaluation_dataset_version_id,
                request_key="ci-evaluation-success",
            ),
        )
        if replay.created or replay.evaluation_run_id != requested.evaluation_run_id:
            raise RuntimeError("Evaluation request retry was not idempotent.")

        await start_evaluation_run(
            db,
            command=TransitionEvaluationRun(
                organization_context_id=ORGANIZATION_CONTEXT_ID,
                evaluation_run_id=requested.evaluation_run_id,
                actor_type="SYSTEM",
                actor_reference="ci-offline-evaluator",
                trace_id="ci-evaluation-success",
            ),
        )
        completed = await complete_evaluation_run(
            db,
            command=CompleteEvaluationRun(
                organization_context_id=ORGANIZATION_CONTEXT_ID,
                evaluation_run_id=requested.evaluation_run_id,
                outcome="SUCCEEDED",
                actor_type="SYSTEM",
                actor_reference="ci-offline-evaluator",
                trace_id="ci-evaluation-success",
                metrics_artifact_reference=str(METRICS_PATH),
                metrics_digest=digest,
                metrics_byte_size=len(METRICS_CONTENT),
            ),
            artifact_reader=LocalFileMetricsArtifactReader(),
        )
        if completed.result_id is None:
            raise RuntimeError("Successful Evaluation Run produced no result.")

        terminal_retry = await complete_evaluation_run(
            db,
            command=CompleteEvaluationRun(
                organization_context_id=ORGANIZATION_CONTEXT_ID,
                evaluation_run_id=requested.evaluation_run_id,
                outcome="SUCCEEDED",
                actor_type="SYSTEM",
                actor_reference="ci-offline-evaluator",
                trace_id="ci-evaluation-success",
                metrics_artifact_reference=str(METRICS_PATH),
                metrics_digest=digest,
                metrics_byte_size=len(METRICS_CONTENT),
            ),
            artifact_reader=LocalFileMetricsArtifactReader(),
        )
        if terminal_retry.created:
            raise RuntimeError("Successful completion retry created duplicate evidence.")

        await db.commit()
        return requested.evaluation_run_id


async def _failed_run(
    *,
    model_version_id: UUID,
    evaluation_dataset_version_id: UUID,
) -> UUID:
    async with SessionFactory() as db:
        requested = await request_evaluation_run(
            db,
            command=_request(
                model_version_id=model_version_id,
                evaluation_dataset_version_id=evaluation_dataset_version_id,
                request_key="ci-evaluation-failure",
            ),
        )
        await start_evaluation_run(
            db,
            command=TransitionEvaluationRun(
                organization_context_id=ORGANIZATION_CONTEXT_ID,
                evaluation_run_id=requested.evaluation_run_id,
                actor_type="SYSTEM",
                actor_reference="ci-offline-evaluator",
                trace_id="ci-evaluation-failure",
            ),
        )
        completed = await complete_evaluation_run(
            db,
            command=CompleteEvaluationRun(
                organization_context_id=ORGANIZATION_CONTEXT_ID,
                evaluation_run_id=requested.evaluation_run_id,
                outcome="FAILED",
                actor_type="SYSTEM",
                actor_reference="ci-offline-evaluator",
                trace_id="ci-evaluation-failure",
                failure_code="CI_EXPECTED_EVALUATION_FAILURE",
            ),
            artifact_reader=LocalFileMetricsArtifactReader(),
        )
        if completed.result_id is not None:
            raise RuntimeError("Failed Evaluation Run produced result evidence.")
        await db.commit()
        return requested.evaluation_run_id


async def _prove_same_dataset_rejected(model: AIModelVersion) -> None:
    async with SessionFactory() as db:
        try:
            await request_evaluation_run(
                db,
                command=_request(
                    model_version_id=model.id,
                    evaluation_dataset_version_id=model.dataset_version_id,
                    request_key="ci-evaluation-same-dataset",
                ),
            )
        except AppError as error:
            await db.rollback()
            if error.code != "AI_EVALUATION_DATASET_NOT_INDEPENDENT":
                raise
        else:
            raise RuntimeError(
                "Training Dataset Version was accepted as Evaluation Dataset Version."
            )


async def _prove_premature_result_rejected(
    *,
    model_version_id: UUID,
    evaluation_dataset_version_id: UUID,
) -> UUID:
    async with SessionFactory() as db:
        requested = await request_evaluation_run(
            db,
            command=_request(
                model_version_id=model_version_id,
                evaluation_dataset_version_id=evaluation_dataset_version_id,
                request_key="ci-evaluation-premature-result",
            ),
        )
        await db.commit()
        run_id = requested.evaluation_run_id

    async with SessionFactory() as db:
        db.add(
            AIEvaluationResult(
                id=uuid4(),
                evaluation_run_id=run_id,
                metrics_artifact_reference="/tmp/invalid-premature-result.json",
                metrics_digest="a" * 64,
                metrics_byte_size=1,
                attested_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
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
                "Database accepted Evaluation Result before SUCCEEDED state."
            )
    return run_id


async def _prove_tamper_detection(evaluation_run_id: UUID) -> None:
    METRICS_PATH.write_bytes(METRICS_CONTENT + b"tampered")
    digest = sha256(METRICS_CONTENT).hexdigest()

    async with SessionFactory() as db:
        try:
            await complete_evaluation_run(
                db,
                command=CompleteEvaluationRun(
                    organization_context_id=ORGANIZATION_CONTEXT_ID,
                    evaluation_run_id=evaluation_run_id,
                    outcome="SUCCEEDED",
                    actor_type="SYSTEM",
                    actor_reference="ci-offline-evaluator",
                    trace_id="ci-evaluation-tamper",
                    metrics_artifact_reference=str(METRICS_PATH),
                    metrics_digest=digest,
                    metrics_byte_size=len(METRICS_CONTENT),
                ),
                artifact_reader=LocalFileMetricsArtifactReader(),
            )
        except AppError as error:
            await db.rollback()
            if error.code != "AI_EVALUATION_RESULT_ATTESTATION_FAILED":
                raise
        else:
            raise RuntimeError("Tampered Evaluation Result artifact was accepted.")


async def _states(evaluation_run_id: UUID) -> list[str]:
    async with SessionFactory() as db:
        return list(
            (
                await db.execute(
                    select(AIEvaluationRunState.state)
                    .where(
                        AIEvaluationRunState.evaluation_run_id
                        == evaluation_run_id
                    )
                    .order_by(AIEvaluationRunState.sequence)
                )
            ).scalars().all()
        )


async def _result_count(evaluation_run_id: UUID) -> int:
    async with SessionFactory() as db:
        return (
            await db.execute(
                select(func.count())
                .select_from(AIEvaluationResult)
                .where(
                    AIEvaluationResult.evaluation_run_id
                    == evaluation_run_id
                )
            )
        ).scalar_one()


async def _event_count() -> int:
    async with SessionFactory() as db:
        return (
            await db.execute(
                select(func.count())
                .select_from(OutboxEvent)
                .where(
                    OutboxEvent.event_type.in_(
                        (
                            "ai.evaluation_run_requested.v1",
                            "ai.evaluation_run_started.v1",
                            "ai.evaluation_run_succeeded.v1",
                            "ai.evaluation_run_failed.v1",
                        )
                    )
                )
            )
        ).scalar_one()


async def main() -> None:
    model = await _model_version()
    evaluation_dataset_version_id = await _evaluation_dataset_version_id()

    await _prove_same_dataset_rejected(model)
    success_id = await _successful_run(
        model_version_id=model.id,
        evaluation_dataset_version_id=evaluation_dataset_version_id,
    )
    failed_id = await _failed_run(
        model_version_id=model.id,
        evaluation_dataset_version_id=evaluation_dataset_version_id,
    )
    premature_id = await _prove_premature_result_rejected(
        model_version_id=model.id,
        evaluation_dataset_version_id=evaluation_dataset_version_id,
    )
    await _prove_tamper_detection(success_id)

    if await _states(success_id) != ["REQUESTED", "RUNNING", "SUCCEEDED"]:
        raise RuntimeError("Unexpected successful Evaluation lifecycle.")
    if await _states(failed_id) != ["REQUESTED", "RUNNING", "FAILED"]:
        raise RuntimeError("Unexpected failed Evaluation lifecycle.")
    if await _states(premature_id) != ["REQUESTED"]:
        raise RuntimeError("Unexpected premature-result Evaluation lifecycle.")
    if await _result_count(success_id) != 1:
        raise RuntimeError("Successful Evaluation Run result count must be one.")
    if await _result_count(failed_id) != 0:
        raise RuntimeError("Failed Evaluation Run result count must be zero.")
    if await _result_count(premature_id) != 0:
        raise RuntimeError("Premature Evaluation Run result count must be zero.")
    if await _event_count() < 7:
        raise RuntimeError("Evaluation lifecycle outbox evidence is incomplete.")

    print("evaluation_lifecycle=REQUESTED>RUNNING>SUCCEEDED")
    print("failure_lifecycle=REQUESTED>RUNNING>FAILED")
    print("training_evaluation_dataset_separation=PASS")
    print("result_sha256_attestation=PASS")
    print("result_byte_size_attestation=PASS")
    print("result_tamper_detection=PASS")
    print("idempotent_evaluation_request=PASS")
    print("premature_result_db_rejection=PASS")
    print("automatic_pass_policy=NOT_IMPLEMENTED")
    print("automatic_promotion=NOT_IMPLEMENTED")
    print("production_activation=NOT_IMPLEMENTED")


if __name__ == "__main__":
    asyncio.run(main())
