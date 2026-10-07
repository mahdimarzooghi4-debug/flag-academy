from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_control_plane.domain import EvaluationRunState, GovernanceActorType
from app.ai_control_plane.models import (
    AIDataset,
    AIDatasetVersion,
    AIEvaluationResult,
    AIEvaluationRun,
    AIEvaluationRunState,
    AIModelVersion,
    AITrainingRun,
)
from app.errors import AppError
from app.platform.events import new_event, record_event

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class MetricsArtifactAttestation:
    content_sha256: str
    byte_size: int


class MetricsArtifactReader(Protocol):
    async def attest(
        self,
        *,
        artifact_reference: str,
    ) -> MetricsArtifactAttestation: ...


class LocalFileMetricsArtifactReader:
    async def attest(
        self,
        *,
        artifact_reference: str,
    ) -> MetricsArtifactAttestation:
        if "://" in artifact_reference:
            raise AppError(
                "AI_EVALUATION_ARTIFACT_REFERENCE_UNSUPPORTED",
                "Local metrics artifact reader does not accept remote references.",
                status_code=422,
            )
        return await asyncio.to_thread(
            _attest_local_file,
            artifact_reference,
        )


@dataclass(frozen=True)
class RequestEvaluationRun:
    organization_context_id: UUID
    request_key: str
    model_version_id: UUID
    evaluation_dataset_version_id: UUID
    evaluation_policy_key: str
    evaluation_policy_version: str
    requested_by_type: str
    requested_by_reference: str
    data_classification: str
    trace_id: str


@dataclass(frozen=True)
class TransitionEvaluationRun:
    organization_context_id: UUID
    evaluation_run_id: UUID
    actor_type: str
    actor_reference: str
    trace_id: str


@dataclass(frozen=True)
class CompleteEvaluationRun:
    organization_context_id: UUID
    evaluation_run_id: UUID
    outcome: str
    actor_type: str
    actor_reference: str
    trace_id: str
    failure_code: str | None = None
    metrics_artifact_reference: str | None = None
    metrics_digest: str | None = None
    metrics_byte_size: int | None = None


@dataclass(frozen=True)
class EvaluationRunResult:
    evaluation_run_id: UUID
    state: str
    sequence: int
    result_id: UUID | None = None
    created: bool = True


def _required_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise AppError(
            "AI_EVALUATION_INPUT_INVALID",
            f"{field} is required.",
            status_code=422,
            details={"field": field},
        )
    return normalized


def _actor_type(value: str) -> str:
    normalized = _required_text(value, "actor_type")
    if normalized not in {item.value for item in GovernanceActorType}:
        raise AppError(
            "AI_EVALUATION_INPUT_INVALID",
            "actor_type must be PERSON or SYSTEM.",
            status_code=422,
            details={"field": "actor_type"},
        )
    return normalized


def _sha256(value: str, field: str) -> str:
    normalized = value.strip().lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise AppError(
            "AI_EVALUATION_INPUT_INVALID",
            f"{field} must be a lowercase SHA-256 digest.",
            status_code=422,
            details={"field": field},
        )
    return normalized


def _attest_local_file(artifact_reference: str) -> MetricsArtifactAttestation:
    path = Path(artifact_reference)
    if not path.is_file():
        raise AppError(
            "AI_EVALUATION_ARTIFACT_UNREADABLE",
            "Evaluation metrics artifact is not a readable local file.",
            status_code=409,
            details={"artifact_reference": artifact_reference},
        )

    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as artifact:
        while chunk := artifact.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)

    return MetricsArtifactAttestation(
        content_sha256=digest.hexdigest(),
        byte_size=size,
    )


def _request_lock_key(
    *,
    organization_context_id: UUID,
    request_key: str,
) -> int:
    identity = f"{organization_context_id}:{request_key}".encode()
    raw = hashlib.sha256(identity).digest()[:8]
    return int.from_bytes(raw, byteorder="big", signed=True)


def _run_lock_key(evaluation_run_id: UUID) -> int:
    raw = hashlib.sha256(str(evaluation_run_id).encode()).digest()[:8]
    return int.from_bytes(raw, byteorder="big", signed=True)


async def _latest_state(
    db: AsyncSession,
    *,
    evaluation_run_id: UUID,
) -> AIEvaluationRunState:
    state = (
        await db.execute(
            select(AIEvaluationRunState)
            .where(
                AIEvaluationRunState.evaluation_run_id == evaluation_run_id
            )
            .order_by(AIEvaluationRunState.sequence.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if state is None:
        raise AppError(
            "AI_EVALUATION_STATE_MISSING",
            "Evaluation Run has no lifecycle state.",
            status_code=409,
            details={"evaluation_run_id": str(evaluation_run_id)},
        )
    return state


async def _load_run(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    evaluation_run_id: UUID,
) -> AIEvaluationRun:
    run = (
        await db.execute(
            select(AIEvaluationRun).where(
                AIEvaluationRun.id == evaluation_run_id,
                AIEvaluationRun.organization_context_id
                == organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if run is None:
        raise AppError(
            "AI_EVALUATION_RUN_NOT_FOUND",
            "Evaluation Run was not found in this organization context.",
            status_code=404,
        )
    return run


async def _model_lineage(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    model_version_id: UUID,
) -> tuple[AIModelVersion, AITrainingRun]:
    lineage = (
        await db.execute(
            select(AIModelVersion, AITrainingRun)
            .join(
                AITrainingRun,
                AITrainingRun.id == AIModelVersion.training_run_id,
            )
            .where(
                AIModelVersion.id == model_version_id,
                AITrainingRun.organization_context_id
                == organization_context_id,
            )
        )
    ).one_or_none()
    if lineage is None:
        raise AppError(
            "AI_EVALUATION_MODEL_VERSION_NOT_FOUND",
            "Model Version was not found in this organization context.",
            status_code=404,
        )
    return lineage[0], lineage[1]


async def _evaluation_dataset(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    dataset_version_id: UUID,
) -> AIDatasetVersion:
    lineage = (
        await db.execute(
            select(AIDatasetVersion, AIDataset)
            .join(AIDataset, AIDataset.id == AIDatasetVersion.dataset_id)
            .where(
                AIDatasetVersion.id == dataset_version_id,
                AIDataset.organization_context_id
                == organization_context_id,
            )
        )
    ).one_or_none()
    if lineage is None:
        raise AppError(
            "AI_EVALUATION_DATASET_VERSION_NOT_FOUND",
            "Evaluation Dataset Version was not found in this organization context.",
            status_code=404,
        )
    return lineage[0]


async def _existing_result(
    db: AsyncSession,
    *,
    evaluation_run_id: UUID,
) -> AIEvaluationResult | None:
    return (
        await db.execute(
            select(AIEvaluationResult).where(
                AIEvaluationResult.evaluation_run_id == evaluation_run_id
            )
        )
    ).scalar_one_or_none()


def _result(
    run: AIEvaluationRun,
    state: AIEvaluationRunState,
    evaluation_result: AIEvaluationResult | None,
    *,
    created: bool,
) -> EvaluationRunResult:
    return EvaluationRunResult(
        evaluation_run_id=run.id,
        state=state.state,
        sequence=state.sequence,
        result_id=(
            None if evaluation_result is None else evaluation_result.id
        ),
        created=created,
    )


async def request_evaluation_run(
    db: AsyncSession,
    *,
    command: RequestEvaluationRun,
) -> EvaluationRunResult:
    request_key = _required_text(command.request_key, "request_key")
    evaluation_policy_key = _required_text(
        command.evaluation_policy_key,
        "evaluation_policy_key",
    )
    evaluation_policy_version = _required_text(
        command.evaluation_policy_version,
        "evaluation_policy_version",
    )
    requested_by_type = _actor_type(command.requested_by_type)
    requested_by_reference = _required_text(
        command.requested_by_reference,
        "requested_by_reference",
    )
    data_classification = _required_text(
        command.data_classification,
        "data_classification",
    )
    trace_id = _required_text(command.trace_id, "trace_id")

    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {
            "lock_key": _request_lock_key(
                organization_context_id=command.organization_context_id,
                request_key=request_key,
            )
        },
    )

    existing = (
        await db.execute(
            select(AIEvaluationRun).where(
                AIEvaluationRun.organization_context_id
                == command.organization_context_id,
                AIEvaluationRun.request_key == request_key,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        same_request = (
            existing.model_version_id == command.model_version_id
            and existing.evaluation_dataset_version_id
            == command.evaluation_dataset_version_id
            and existing.evaluation_policy_key == evaluation_policy_key
            and existing.evaluation_policy_version
            == evaluation_policy_version
            and existing.requested_by_type == requested_by_type
            and existing.requested_by_reference == requested_by_reference
            and existing.data_classification == data_classification
        )
        if not same_request:
            raise AppError(
                "AI_EVALUATION_REQUEST_KEY_REUSED",
                "Evaluation request key was reused with different semantics.",
                status_code=409,
                details={"request_key": request_key},
            )
        state = await _latest_state(
            db,
            evaluation_run_id=existing.id,
        )
        return _result(
            existing,
            state,
            await _existing_result(db, evaluation_run_id=existing.id),
            created=False,
        )

    model_version, _training_run = await _model_lineage(
        db,
        organization_context_id=command.organization_context_id,
        model_version_id=command.model_version_id,
    )
    await _evaluation_dataset(
        db,
        organization_context_id=command.organization_context_id,
        dataset_version_id=command.evaluation_dataset_version_id,
    )
    if (
        model_version.dataset_version_id
        == command.evaluation_dataset_version_id
    ):
        raise AppError(
            "AI_EVALUATION_DATASET_NOT_INDEPENDENT",
            "Evaluation Dataset Version must differ from the Training Dataset Version.",
            status_code=409,
            details={
                "training_dataset_version_id": str(
                    model_version.dataset_version_id
                ),
                "evaluation_dataset_version_id": str(
                    command.evaluation_dataset_version_id
                ),
            },
        )

    now = datetime.now(UTC)
    run = AIEvaluationRun(
        id=uuid4(),
        organization_context_id=command.organization_context_id,
        request_key=request_key,
        data_classification=data_classification,
        model_version_id=model_version.id,
        evaluation_dataset_version_id=command.evaluation_dataset_version_id,
        evaluation_policy_key=evaluation_policy_key,
        evaluation_policy_version=evaluation_policy_version,
        requested_by_type=requested_by_type,
        requested_by_reference=requested_by_reference,
        requested_at=now,
    )
    db.add(run)
    await db.flush()

    state = AIEvaluationRunState(
        id=uuid4(),
        evaluation_run_id=run.id,
        sequence=1,
        state=EvaluationRunState.REQUESTED.value,
        changed_at=now,
        failure_code=None,
    )
    db.add(state)

    record_event(
        db,
        new_event(
            event_type="ai.evaluation_run_requested.v1",
            aggregate_type="AIEvaluationRun",
            aggregate_id=run.id,
            aggregate_version=1,
            actor={
                "type": requested_by_type,
                "id": requested_by_reference,
            },
            organization_context_id=run.organization_context_id,
            data_classification=run.data_classification,
            payload={
                "evaluation_run_id": str(run.id),
                "model_version_id": str(run.model_version_id),
                "training_dataset_version_id": str(
                    model_version.dataset_version_id
                ),
                "evaluation_dataset_version_id": str(
                    run.evaluation_dataset_version_id
                ),
                "evaluation_policy_key": run.evaluation_policy_key,
                "evaluation_policy_version": run.evaluation_policy_version,
                "request_key": run.request_key,
            },
            trace_id=trace_id,
        ),
    )

    return _result(run, state, None, created=True)


async def start_evaluation_run(
    db: AsyncSession,
    *,
    command: TransitionEvaluationRun,
) -> EvaluationRunResult:
    actor_type = _actor_type(command.actor_type)
    actor_reference = _required_text(
        command.actor_reference,
        "actor_reference",
    )
    trace_id = _required_text(command.trace_id, "trace_id")

    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _run_lock_key(command.evaluation_run_id)},
    )
    run = await _load_run(
        db,
        organization_context_id=command.organization_context_id,
        evaluation_run_id=command.evaluation_run_id,
    )
    latest = await _latest_state(db, evaluation_run_id=run.id)

    if latest.state == EvaluationRunState.RUNNING.value:
        return _result(
            run,
            latest,
            await _existing_result(db, evaluation_run_id=run.id),
            created=False,
        )
    if latest.state != EvaluationRunState.REQUESTED.value:
        raise AppError(
            "AI_EVALUATION_INVALID_TRANSITION",
            "Only REQUESTED Evaluation Runs can transition to RUNNING.",
            status_code=409,
            details={"current_state": latest.state},
        )

    state = AIEvaluationRunState(
        id=uuid4(),
        evaluation_run_id=run.id,
        sequence=latest.sequence + 1,
        state=EvaluationRunState.RUNNING.value,
        changed_at=datetime.now(UTC),
        failure_code=None,
    )
    db.add(state)

    model_version = (
        await db.execute(
            select(AIModelVersion).where(
                AIModelVersion.id == run.model_version_id
            )
        )
    ).scalar_one()

    record_event(
        db,
        new_event(
            event_type="ai.evaluation_run_started.v1",
            aggregate_type="AIEvaluationRun",
            aggregate_id=run.id,
            aggregate_version=state.sequence,
            actor={"type": actor_type, "id": actor_reference},
            organization_context_id=run.organization_context_id,
            data_classification=run.data_classification,
            payload={
                "evaluation_run_id": str(run.id),
                "model_version_id": str(run.model_version_id),
                "training_dataset_version_id": str(
                    model_version.dataset_version_id
                ),
                "evaluation_dataset_version_id": str(
                    run.evaluation_dataset_version_id
                ),
                "evaluation_policy_key": run.evaluation_policy_key,
                "evaluation_policy_version": run.evaluation_policy_version,
            },
            trace_id=trace_id,
        ),
    )
    return _result(run, state, None, created=True)


async def complete_evaluation_run(
    db: AsyncSession,
    *,
    command: CompleteEvaluationRun,
    artifact_reader: MetricsArtifactReader,
) -> EvaluationRunResult:
    actor_type = _actor_type(command.actor_type)
    actor_reference = _required_text(
        command.actor_reference,
        "actor_reference",
    )
    trace_id = _required_text(command.trace_id, "trace_id")
    outcome = _required_text(command.outcome, "outcome")
    allowed = {
        EvaluationRunState.SUCCEEDED.value,
        EvaluationRunState.FAILED.value,
    }
    if outcome not in allowed:
        raise AppError(
            "AI_EVALUATION_INPUT_INVALID",
            "outcome must be SUCCEEDED or FAILED.",
            status_code=422,
            details={"field": "outcome"},
        )

    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _run_lock_key(command.evaluation_run_id)},
    )
    run = await _load_run(
        db,
        organization_context_id=command.organization_context_id,
        evaluation_run_id=command.evaluation_run_id,
    )
    latest = await _latest_state(db, evaluation_run_id=run.id)
    evaluation_result = await _existing_result(
        db,
        evaluation_run_id=run.id,
    )

    if latest.state in allowed:
        if latest.state != outcome:
            raise AppError(
                "AI_EVALUATION_INVALID_TRANSITION",
                "Completed Evaluation Run cannot change terminal outcome.",
                status_code=409,
                details={"current_state": latest.state},
            )
        if outcome == EvaluationRunState.SUCCEEDED.value:
            retry_reference = _required_text(
                command.metrics_artifact_reference or "",
                "metrics_artifact_reference",
            )
            retry_digest = _sha256(
                command.metrics_digest or "",
                "metrics_digest",
            )
            if (
                command.metrics_byte_size is None
                or command.metrics_byte_size < 0
            ):
                raise AppError(
                    "AI_EVALUATION_INPUT_INVALID",
                    "metrics_byte_size must be a non-negative integer.",
                    status_code=422,
                    details={"field": "metrics_byte_size"},
                )
            attestation = await artifact_reader.attest(
                artifact_reference=retry_reference
            )
            if (
                attestation.content_sha256 != retry_digest
                or attestation.byte_size != command.metrics_byte_size
            ):
                raise AppError(
                    "AI_EVALUATION_RESULT_ATTESTATION_FAILED",
                    "Observed evaluation result does not match supplied immutable metadata.",
                    status_code=409,
                )
            exact_retry = (
                evaluation_result is not None
                and command.failure_code is None
                and evaluation_result.metrics_artifact_reference
                == retry_reference
                and evaluation_result.metrics_digest
                == attestation.content_sha256
                and evaluation_result.metrics_byte_size
                == attestation.byte_size
            )
        else:
            retry_failure_code = _required_text(
                command.failure_code or "",
                "failure_code",
            )
            exact_retry = (
                evaluation_result is None
                and latest.failure_code == retry_failure_code
                and command.metrics_artifact_reference is None
                and command.metrics_digest is None
                and command.metrics_byte_size is None
            )
        if not exact_retry:
            raise AppError(
                "AI_EVALUATION_TERMINAL_RETRY_MISMATCH",
                "Terminal Evaluation Run retry does not match recorded outcome.",
                status_code=409,
            )
        return _result(
            run,
            latest,
            evaluation_result,
            created=False,
        )

    if latest.state != EvaluationRunState.RUNNING.value:
        raise AppError(
            "AI_EVALUATION_INVALID_TRANSITION",
            "Only RUNNING Evaluation Runs can complete.",
            status_code=409,
            details={"current_state": latest.state},
        )

    attestation: MetricsArtifactAttestation | None = None
    metrics_reference: str | None = None
    failure_code: str | None = None

    if outcome == EvaluationRunState.SUCCEEDED.value:
        if command.failure_code is not None:
            raise AppError(
                "AI_EVALUATION_INPUT_INVALID",
                "Successful Evaluation Run cannot include failure_code.",
                status_code=422,
            )
        metrics_reference = _required_text(
            command.metrics_artifact_reference or "",
            "metrics_artifact_reference",
        )
        expected_digest = _sha256(
            command.metrics_digest or "",
            "metrics_digest",
        )
        if command.metrics_byte_size is None or command.metrics_byte_size < 0:
            raise AppError(
                "AI_EVALUATION_INPUT_INVALID",
                "metrics_byte_size must be a non-negative integer.",
                status_code=422,
                details={"field": "metrics_byte_size"},
            )
        attestation = await artifact_reader.attest(
            artifact_reference=metrics_reference
        )
        if (
            attestation.content_sha256 != expected_digest
            or attestation.byte_size != command.metrics_byte_size
        ):
            raise AppError(
                "AI_EVALUATION_RESULT_ATTESTATION_FAILED",
                "Observed evaluation result does not match supplied immutable metadata.",
                status_code=409,
                details={
                    "expected_sha256": expected_digest,
                    "observed_sha256": attestation.content_sha256,
                    "expected_byte_size": command.metrics_byte_size,
                    "observed_byte_size": attestation.byte_size,
                },
            )
    else:
        failure_code = _required_text(
            command.failure_code or "",
            "failure_code",
        )
        if any(
            value is not None
            for value in (
                command.metrics_artifact_reference,
                command.metrics_digest,
                command.metrics_byte_size,
            )
        ):
            raise AppError(
                "AI_EVALUATION_INPUT_INVALID",
                "Failed Evaluation Run cannot produce an evaluation result.",
                status_code=422,
            )

    now = datetime.now(UTC)
    state = AIEvaluationRunState(
        id=uuid4(),
        evaluation_run_id=run.id,
        sequence=latest.sequence + 1,
        state=outcome,
        changed_at=now,
        failure_code=failure_code,
    )
    db.add(state)
    await db.flush()

    if attestation is not None and metrics_reference is not None:
        evaluation_result = AIEvaluationResult(
            id=uuid4(),
            evaluation_run_id=run.id,
            metrics_artifact_reference=metrics_reference,
            metrics_digest=attestation.content_sha256,
            metrics_byte_size=attestation.byte_size,
            attested_at=now,
            created_at=now,
        )
        db.add(evaluation_result)
        await db.flush()

    model_version = (
        await db.execute(
            select(AIModelVersion).where(
                AIModelVersion.id == run.model_version_id
            )
        )
    ).scalar_one()
    event_type = (
        "ai.evaluation_run_succeeded.v1"
        if outcome == EvaluationRunState.SUCCEEDED.value
        else "ai.evaluation_run_failed.v1"
    )
    payload = {
        "evaluation_run_id": str(run.id),
        "model_version_id": str(run.model_version_id),
        "training_dataset_version_id": str(
            model_version.dataset_version_id
        ),
        "evaluation_dataset_version_id": str(
            run.evaluation_dataset_version_id
        ),
        "evaluation_policy_key": run.evaluation_policy_key,
        "evaluation_policy_version": run.evaluation_policy_version,
        "failure_code": failure_code,
    }
    if evaluation_result is not None:
        payload.update(
            {
                "evaluation_result_id": str(evaluation_result.id),
                "metrics_artifact_reference": (
                    evaluation_result.metrics_artifact_reference
                ),
                "metrics_digest": evaluation_result.metrics_digest,
                "metrics_byte_size": evaluation_result.metrics_byte_size,
            }
        )

    record_event(
        db,
        new_event(
            event_type=event_type,
            aggregate_type="AIEvaluationRun",
            aggregate_id=run.id,
            aggregate_version=state.sequence,
            actor={"type": actor_type, "id": actor_reference},
            organization_context_id=run.organization_context_id,
            data_classification=run.data_classification,
            payload=payload,
            trace_id=trace_id,
        ),
    )

    return _result(
        run,
        state,
        evaluation_result,
        created=True,
    )
