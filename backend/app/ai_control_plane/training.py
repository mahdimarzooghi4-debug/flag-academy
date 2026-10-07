from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_control_plane.domain import GovernanceActorType, TrainingRunState
from app.ai_control_plane.models import (
    AIDataset,
    AIDatasetVersion,
    AIModelArtifact,
    AITrainingRun,
    AITrainingRunState,
)
from app.errors import AppError
from app.platform.events import new_event, record_event

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class RequestTrainingRun:
    organization_context_id: UUID
    request_key: str
    dataset_version_id: UUID
    model_family: str
    training_recipe_digest: str
    requested_by_type: str
    requested_by_reference: str
    data_classification: str
    trace_id: str


@dataclass(frozen=True)
class TransitionTrainingRun:
    organization_context_id: UUID
    training_run_id: UUID
    actor_type: str
    actor_reference: str
    trace_id: str


@dataclass(frozen=True)
class CompleteTrainingRun:
    organization_context_id: UUID
    training_run_id: UUID
    outcome: str
    actor_type: str
    actor_reference: str
    trace_id: str
    failure_code: str | None = None
    artifact_format: str | None = None
    artifact_reference: str | None = None
    content_sha256: str | None = None
    byte_size: int | None = None


@dataclass(frozen=True)
class TrainingRunResult:
    training_run_id: UUID
    state: str
    sequence: int
    artifact_id: UUID | None = None
    created: bool = True


def _required_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise AppError(
            "AI_TRAINING_INPUT_INVALID",
            f"{field} is required.",
            status_code=422,
            details={"field": field},
        )
    return normalized


def _actor_type(value: str) -> str:
    normalized = _required_text(value, "actor_type")
    if normalized not in {item.value for item in GovernanceActorType}:
        raise AppError(
            "AI_TRAINING_INPUT_INVALID",
            "actor_type must be PERSON or SYSTEM.",
            status_code=422,
            details={"field": "actor_type"},
        )
    return normalized


def _sha256(value: str, field: str) -> str:
    normalized = value.strip().lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise AppError(
            "AI_TRAINING_INPUT_INVALID",
            f"{field} must be a lowercase SHA-256 digest.",
            status_code=422,
            details={"field": field},
        )
    return normalized


def _run_lock_key(training_run_id: UUID) -> int:
    raw = hashlib.sha256(str(training_run_id).encode()).digest()[:8]
    return int.from_bytes(raw, byteorder="big", signed=True)


async def _latest_state(
    db: AsyncSession,
    *,
    training_run_id: UUID,
) -> AITrainingRunState:
    row = (
        await db.execute(
            select(AITrainingRunState)
            .where(AITrainingRunState.training_run_id == training_run_id)
            .order_by(AITrainingRunState.sequence.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise AppError(
            "AI_TRAINING_STATE_MISSING",
            "Training Run has no lifecycle state.",
            status_code=409,
            details={"training_run_id": str(training_run_id)},
        )
    return row


async def _load_run(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    training_run_id: UUID,
) -> AITrainingRun:
    run = (
        await db.execute(
            select(AITrainingRun).where(
                AITrainingRun.id == training_run_id,
                AITrainingRun.organization_context_id == organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if run is None:
        raise AppError(
            "AI_TRAINING_RUN_NOT_FOUND",
            "Training Run was not found in this organization context.",
            status_code=404,
        )
    return run


async def request_training_run(
    db: AsyncSession,
    *,
    command: RequestTrainingRun,
) -> TrainingRunResult:
    request_key = _required_text(command.request_key, "request_key")
    model_family = _required_text(command.model_family, "model_family")
    recipe_digest = _sha256(
        command.training_recipe_digest,
        "training_recipe_digest",
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

    lock_identity = (
        f"{command.organization_context_id}:{request_key}".encode()
    )
    lock_key = int.from_bytes(
        hashlib.sha256(lock_identity).digest()[:8],
        byteorder="big",
        signed=True,
    )
    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": lock_key},
    )

    existing = (
        await db.execute(
            select(AITrainingRun).where(
                AITrainingRun.organization_context_id
                == command.organization_context_id,
                AITrainingRun.request_key == request_key,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        same_request = (
            existing.dataset_version_id == command.dataset_version_id
            and existing.model_family == model_family
            and existing.training_recipe_digest == recipe_digest
            and existing.requested_by_type == requested_by_type
            and existing.requested_by_reference == requested_by_reference
            and existing.data_classification == data_classification
        )
        if not same_request:
            raise AppError(
                "AI_TRAINING_REQUEST_KEY_REUSED",
                "Training request key was reused with different semantics.",
                status_code=409,
                details={"request_key": request_key},
            )
        state = await _latest_state(
            db,
            training_run_id=existing.id,
        )
        artifact = (
            await db.execute(
                select(AIModelArtifact).where(
                    AIModelArtifact.training_run_id == existing.id
                )
            )
        ).scalar_one_or_none()
        return TrainingRunResult(
            training_run_id=existing.id,
            state=state.state,
            sequence=state.sequence,
            artifact_id=None if artifact is None else artifact.id,
            created=False,
        )

    dataset_version = (
        await db.execute(
            select(AIDatasetVersion, AIDataset)
            .join(AIDataset, AIDataset.id == AIDatasetVersion.dataset_id)
            .where(
                AIDatasetVersion.id == command.dataset_version_id,
                AIDataset.organization_context_id
                == command.organization_context_id,
            )
        )
    ).one_or_none()
    if dataset_version is None:
        raise AppError(
            "AI_TRAINING_DATASET_VERSION_NOT_FOUND",
            "Exact governed Dataset Version was not found in this organization context.",
            status_code=404,
        )

    now = datetime.now(UTC)
    run = AITrainingRun(
        id=uuid4(),
        organization_context_id=command.organization_context_id,
        request_key=request_key,
        data_classification=data_classification,
        dataset_version_id=command.dataset_version_id,
        model_family=model_family,
        training_recipe_digest=recipe_digest,
        requested_by_type=requested_by_type,
        requested_by_reference=requested_by_reference,
        requested_at=now,
    )
    db.add(run)
    await db.flush()

    state = AITrainingRunState(
        id=uuid4(),
        training_run_id=run.id,
        sequence=1,
        state=TrainingRunState.REQUESTED.value,
        changed_at=now,
        failure_code=None,
    )
    db.add(state)

    record_event(
        db,
        new_event(
            event_type="ai.training_run_requested.v1",
            aggregate_type="AITrainingRun",
            aggregate_id=run.id,
            aggregate_version=1,
            actor={
                "type": requested_by_type,
                "id": requested_by_reference,
            },
            organization_context_id=command.organization_context_id,
            data_classification=data_classification,
            payload={
                "training_run_id": str(run.id),
                "dataset_version_id": str(run.dataset_version_id),
                "model_family": run.model_family,
                "training_recipe_digest": run.training_recipe_digest,
                "request_key": run.request_key,
            },
            trace_id=trace_id,
        ),
    )

    return TrainingRunResult(
        training_run_id=run.id,
        state=state.state,
        sequence=state.sequence,
    )


async def start_training_run(
    db: AsyncSession,
    *,
    command: TransitionTrainingRun,
) -> TrainingRunResult:
    actor_type = _actor_type(command.actor_type)
    actor_reference = _required_text(
        command.actor_reference,
        "actor_reference",
    )
    trace_id = _required_text(command.trace_id, "trace_id")

    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _run_lock_key(command.training_run_id)},
    )
    run = await _load_run(
        db,
        organization_context_id=command.organization_context_id,
        training_run_id=command.training_run_id,
    )
    latest = await _latest_state(db, training_run_id=run.id)

    if latest.state == TrainingRunState.RUNNING.value:
        return TrainingRunResult(
            training_run_id=run.id,
            state=latest.state,
            sequence=latest.sequence,
            created=False,
        )
    if latest.state != TrainingRunState.REQUESTED.value:
        raise AppError(
            "AI_TRAINING_INVALID_TRANSITION",
            "Only REQUESTED Training Runs can transition to RUNNING.",
            status_code=409,
            details={"current_state": latest.state},
        )

    state = AITrainingRunState(
        id=uuid4(),
        training_run_id=run.id,
        sequence=latest.sequence + 1,
        state=TrainingRunState.RUNNING.value,
        changed_at=datetime.now(UTC),
        failure_code=None,
    )
    db.add(state)

    record_event(
        db,
        new_event(
            event_type="ai.training_run_started.v1",
            aggregate_type="AITrainingRun",
            aggregate_id=run.id,
            aggregate_version=state.sequence,
            actor={"type": actor_type, "id": actor_reference},
            organization_context_id=run.organization_context_id,
            data_classification=run.data_classification,
            payload={
                "training_run_id": str(run.id),
                "dataset_version_id": str(run.dataset_version_id),
                "model_family": run.model_family,
            },
            trace_id=trace_id,
        ),
    )
    return TrainingRunResult(
        training_run_id=run.id,
        state=state.state,
        sequence=state.sequence,
    )


async def complete_training_run(
    db: AsyncSession,
    *,
    command: CompleteTrainingRun,
) -> TrainingRunResult:
    actor_type = _actor_type(command.actor_type)
    actor_reference = _required_text(
        command.actor_reference,
        "actor_reference",
    )
    trace_id = _required_text(command.trace_id, "trace_id")
    outcome = _required_text(command.outcome, "outcome")
    allowed = {
        TrainingRunState.SUCCEEDED.value,
        TrainingRunState.FAILED.value,
    }
    if outcome not in allowed:
        raise AppError(
            "AI_TRAINING_INPUT_INVALID",
            "outcome must be SUCCEEDED or FAILED.",
            status_code=422,
            details={"field": "outcome"},
        )

    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _run_lock_key(command.training_run_id)},
    )
    run = await _load_run(
        db,
        organization_context_id=command.organization_context_id,
        training_run_id=command.training_run_id,
    )
    latest = await _latest_state(db, training_run_id=run.id)

    if latest.state in allowed:
        artifact = (
            await db.execute(
                select(AIModelArtifact).where(
                    AIModelArtifact.training_run_id == run.id
                )
            )
        ).scalar_one_or_none()
        if latest.state != outcome:
            raise AppError(
                "AI_TRAINING_INVALID_TRANSITION",
                "Completed Training Run cannot change terminal outcome.",
                status_code=409,
                details={"current_state": latest.state},
            )
        return TrainingRunResult(
            training_run_id=run.id,
            state=latest.state,
            sequence=latest.sequence,
            artifact_id=None if artifact is None else artifact.id,
            created=False,
        )

    if latest.state != TrainingRunState.RUNNING.value:
        raise AppError(
            "AI_TRAINING_INVALID_TRANSITION",
            "Only RUNNING Training Runs can complete.",
            status_code=409,
            details={"current_state": latest.state},
        )

    artifact: AIModelArtifact | None = None
    failure_code: str | None = None
    if outcome == TrainingRunState.SUCCEEDED.value:
        if command.failure_code is not None:
            raise AppError(
                "AI_TRAINING_INPUT_INVALID",
                "Successful Training Run cannot include failure_code.",
                status_code=422,
            )
        artifact_format = _required_text(
            command.artifact_format or "",
            "artifact_format",
        )
        artifact_reference = _required_text(
            command.artifact_reference or "",
            "artifact_reference",
        )
        content_sha256 = _sha256(
            command.content_sha256 or "",
            "content_sha256",
        )
        if command.byte_size is None or command.byte_size < 0:
            raise AppError(
                "AI_TRAINING_INPUT_INVALID",
                "byte_size must be a non-negative integer.",
                status_code=422,
                details={"field": "byte_size"},
            )
        artifact = AIModelArtifact(
            id=uuid4(),
            training_run_id=run.id,
            artifact_format=artifact_format,
            artifact_reference=artifact_reference,
            content_sha256=content_sha256,
            byte_size=command.byte_size,
            created_at=datetime.now(UTC),
        )
        db.add(artifact)
    else:
        failure_code = _required_text(
            command.failure_code or "",
            "failure_code",
        )
        if any(
            value is not None
            for value in (
                command.artifact_format,
                command.artifact_reference,
                command.content_sha256,
                command.byte_size,
            )
        ):
            raise AppError(
                "AI_TRAINING_INPUT_INVALID",
                "Failed Training Run cannot produce a model artifact.",
                status_code=422,
            )

    state = AITrainingRunState(
        id=uuid4(),
        training_run_id=run.id,
        sequence=latest.sequence + 1,
        state=outcome,
        changed_at=datetime.now(UTC),
        failure_code=failure_code,
    )
    db.add(state)

    event_type = (
        "ai.training_run_succeeded.v1"
        if outcome == TrainingRunState.SUCCEEDED.value
        else "ai.training_run_failed.v1"
    )
    payload = {
        "training_run_id": str(run.id),
        "dataset_version_id": str(run.dataset_version_id),
        "model_family": run.model_family,
        "failure_code": failure_code,
    }
    if artifact is not None:
        payload.update(
            {
                "model_artifact_id": str(artifact.id),
                "artifact_format": artifact.artifact_format,
                "artifact_reference": artifact.artifact_reference,
                "content_sha256": artifact.content_sha256,
                "byte_size": artifact.byte_size,
            }
        )

    record_event(
        db,
        new_event(
            event_type=event_type,
            aggregate_type="AITrainingRun",
            aggregate_id=run.id,
            aggregate_version=state.sequence,
            actor={"type": actor_type, "id": actor_reference},
            organization_context_id=run.organization_context_id,
            data_classification=run.data_classification,
            payload=payload,
            trace_id=trace_id,
        ),
    )

    return TrainingRunResult(
        training_run_id=run.id,
        state=state.state,
        sequence=state.sequence,
        artifact_id=None if artifact is None else artifact.id,
    )
