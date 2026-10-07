from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_control_plane.domain import EvaluationRunState, PromotionDecisionState
from app.ai_control_plane.models import (
    AIEvaluationResult,
    AIEvaluationRun,
    AIEvaluationRunState,
    AIModelPromotionDecision,
    AIModelVersion,
    AITrainingRun,
)
from app.errors import AppError
from app.platform.events import new_event, record_event


@dataclass(frozen=True)
class RecordHumanPromotionDecision:
    organization_context_id: UUID
    model_version_id: UUID
    evaluation_run_id: UUID
    reviewer_id: UUID
    rationale: str
    decision: str
    target_environment: str
    prior_active_model_version_id: UUID | None
    trace_id: str


@dataclass(frozen=True)
class PromotionDecisionResult:
    promotion_decision_id: UUID
    model_version_id: UUID
    evaluation_run_id: UUID
    reviewer_id: UUID
    decision: str
    target_environment: str
    prior_active_model_version_id: UUID | None
    created: bool


def _required_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise AppError(
            "AI_PROMOTION_INPUT_INVALID",
            f"{field} is required.",
            status_code=422,
            details={"field": field},
        )
    return normalized


def _decision(value: str) -> str:
    normalized = _required_text(value, "decision")
    allowed = {item.value for item in PromotionDecisionState}
    if normalized not in allowed:
        raise AppError(
            "AI_PROMOTION_INPUT_INVALID",
            "decision must be APPROVED or REJECTED.",
            status_code=422,
            details={"field": "decision"},
        )
    return normalized


def _lock_key(
    *,
    evaluation_run_id: UUID,
    target_environment: str,
) -> int:
    identity = f"{evaluation_run_id}:{target_environment}".encode()
    raw = hashlib.sha256(identity).digest()[:8]
    return int.from_bytes(raw, byteorder="big", signed=True)


async def _model_in_organization(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    model_version_id: UUID,
) -> AIModelVersion:
    model = (
        await db.execute(
            select(AIModelVersion)
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
    ).scalar_one_or_none()
    if model is None:
        raise AppError(
            "AI_PROMOTION_MODEL_VERSION_NOT_FOUND",
            "Model Version was not found in this organization context.",
            status_code=404,
        )
    return model


async def _evaluation_run(
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
            "AI_PROMOTION_EVALUATION_RUN_NOT_FOUND",
            "Evaluation Run was not found in this organization context.",
            status_code=404,
        )
    return run


async def _latest_evaluation_state(
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
            "AI_PROMOTION_EVALUATION_STATE_MISSING",
            "Evaluation Run has no lifecycle state.",
            status_code=409,
        )
    return state


async def _require_successful_evaluation(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    model_version_id: UUID,
    evaluation_run_id: UUID,
) -> AIEvaluationRun:
    await _model_in_organization(
        db,
        organization_context_id=organization_context_id,
        model_version_id=model_version_id,
    )
    run = await _evaluation_run(
        db,
        organization_context_id=organization_context_id,
        evaluation_run_id=evaluation_run_id,
    )
    if run.model_version_id != model_version_id:
        raise AppError(
            "AI_PROMOTION_MODEL_EVALUATION_MISMATCH",
            "Promotion Model Version must match the Evaluation Run Model Version.",
            status_code=409,
        )

    state = await _latest_evaluation_state(
        db,
        evaluation_run_id=run.id,
    )
    if state.state != EvaluationRunState.SUCCEEDED.value:
        raise AppError(
            "AI_PROMOTION_EVALUATION_NOT_SUCCEEDED",
            "Human Promotion Decision requires a SUCCEEDED Evaluation Run.",
            status_code=409,
            details={"current_state": state.state},
        )

    result_exists = (
        await db.execute(
            select(AIEvaluationResult.id).where(
                AIEvaluationResult.evaluation_run_id == run.id
            )
        )
    ).scalar_one_or_none()
    if result_exists is None:
        raise AppError(
            "AI_PROMOTION_EVALUATION_RESULT_MISSING",
            "Successful Evaluation Run has no immutable Evaluation Result.",
            status_code=409,
        )
    return run


def _result(
    decision: AIModelPromotionDecision,
    *,
    created: bool,
) -> PromotionDecisionResult:
    return PromotionDecisionResult(
        promotion_decision_id=decision.id,
        model_version_id=decision.model_version_id,
        evaluation_run_id=decision.evaluation_run_id,
        reviewer_id=decision.reviewer_id,
        decision=decision.decision,
        target_environment=decision.target_environment,
        prior_active_model_version_id=(
            decision.prior_active_model_version_id
        ),
        created=created,
    )


async def record_human_promotion_decision(
    db: AsyncSession,
    *,
    command: RecordHumanPromotionDecision,
) -> PromotionDecisionResult:
    rationale = _required_text(command.rationale, "rationale")
    decision_value = _decision(command.decision)
    target_environment = _required_text(
        command.target_environment,
        "target_environment",
    )
    trace_id = _required_text(command.trace_id, "trace_id")

    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {
            "lock_key": _lock_key(
                evaluation_run_id=command.evaluation_run_id,
                target_environment=target_environment,
            )
        },
    )

    run = await _require_successful_evaluation(
        db,
        organization_context_id=command.organization_context_id,
        model_version_id=command.model_version_id,
        evaluation_run_id=command.evaluation_run_id,
    )

    if command.prior_active_model_version_id is not None:
        await _model_in_organization(
            db,
            organization_context_id=command.organization_context_id,
            model_version_id=command.prior_active_model_version_id,
        )

    existing = (
        await db.execute(
            select(AIModelPromotionDecision).where(
                AIModelPromotionDecision.evaluation_run_id
                == command.evaluation_run_id,
                AIModelPromotionDecision.target_environment
                == target_environment,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        exact_retry = (
            existing.model_version_id == command.model_version_id
            and existing.reviewer_id == command.reviewer_id
            and existing.rationale == rationale
            and existing.decision == decision_value
            and existing.prior_active_model_version_id
            == command.prior_active_model_version_id
        )
        if not exact_retry:
            raise AppError(
                "AI_PROMOTION_DECISION_CONFLICT",
                (
                    "Promotion decision already exists for this Evaluation "
                    "Run and target environment with different semantics."
                ),
                status_code=409,
            )
        return _result(existing, created=False)

    now = datetime.now(UTC)
    promotion = AIModelPromotionDecision(
        id=uuid4(),
        model_version_id=command.model_version_id,
        evaluation_run_id=command.evaluation_run_id,
        reviewer_id=command.reviewer_id,
        rationale=rationale,
        decision=decision_value,
        target_environment=target_environment,
        prior_active_model_version_id=(
            command.prior_active_model_version_id
        ),
        decided_at=now,
    )
    db.add(promotion)
    await db.flush()

    record_event(
        db,
        new_event(
            event_type="ai.model_promotion_decision_recorded.v1",
            aggregate_type="AIModelPromotionDecision",
            aggregate_id=promotion.id,
            aggregate_version=1,
            actor={"type": "PERSON", "id": str(command.reviewer_id)},
            organization_context_id=run.organization_context_id,
            data_classification=run.data_classification,
            payload={
                "promotion_decision_id": str(promotion.id),
                "model_version_id": str(promotion.model_version_id),
                "evaluation_run_id": str(promotion.evaluation_run_id),
                "reviewer_id": str(promotion.reviewer_id),
                "decision": promotion.decision,
                "target_environment": promotion.target_environment,
                "prior_active_model_version_id": (
                    None
                    if promotion.prior_active_model_version_id is None
                    else str(promotion.prior_active_model_version_id)
                ),
                "authorization_only": True,
                "runtime_activation": False,
            },
            trace_id=trace_id,
        ),
    )

    return _result(promotion, created=True)
