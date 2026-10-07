from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_control_plane.models import (
    AIDataset,
    AIDatasetItem,
    AIDatasetVersion,
    AIEvaluationResult,
    AIEvaluationRun,
    AIEvaluationRunState,
    AIModelArtifact,
    AIModelPromotionDecision,
    AIModelVersion,
    AITrainingRun,
    AITrainingRunState,
)


@dataclass(frozen=True)
class DatasetVersionRead:
    id: UUID
    dataset_id: UUID
    dataset_name: str
    purpose: str
    version_number: int
    dataset_digest: str
    item_count: int
    created_at: datetime


@dataclass(frozen=True)
class TrainingRunRead:
    id: UUID
    dataset_version_id: UUID
    model_family: str
    state: str
    requested_at: datetime
    model_artifact_id: UUID | None
    model_version_id: UUID | None


@dataclass(frozen=True)
class ModelVersionRead:
    id: UUID
    training_run_id: UUID
    dataset_version_id: UUID
    model_family: str
    semantic_version: str
    attestation_sha256: str
    attestation_byte_size: int
    attested_at: datetime
    created_at: datetime


@dataclass(frozen=True)
class EvaluationRunRead:
    id: UUID
    model_version_id: UUID
    evaluation_dataset_version_id: UUID
    evaluation_policy_key: str
    evaluation_policy_version: str
    state: str
    requested_at: datetime
    result_digest: str | None
    result_byte_size: int | None
    result_attested_at: datetime | None


@dataclass(frozen=True)
class PromotionDecisionRead:
    id: UUID
    model_version_id: UUID
    evaluation_run_id: UUID
    reviewer_id: UUID
    rationale: str
    decision: str
    target_environment: str
    prior_active_model_version_id: UUID | None
    decided_at: datetime


@dataclass(frozen=True)
class AIGovernanceRead:
    organization_context_id: UUID
    dataset_versions: tuple[DatasetVersionRead, ...]
    training_runs: tuple[TrainingRunRead, ...]
    model_versions: tuple[ModelVersionRead, ...]
    evaluation_runs: tuple[EvaluationRunRead, ...]
    promotion_decisions: tuple[PromotionDecisionRead, ...]


async def load_ai_governance_read(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
) -> AIGovernanceRead:
    dataset_rows = (
        await db.execute(
            select(
                AIDatasetVersion,
                AIDataset,
                func.count(AIDatasetItem.id),
            )
            .join(
                AIDataset,
                AIDataset.id == AIDatasetVersion.dataset_id,
            )
            .outerjoin(
                AIDatasetItem,
                AIDatasetItem.dataset_version_id == AIDatasetVersion.id,
            )
            .where(
                AIDataset.organization_context_id
                == organization_context_id
            )
            .group_by(AIDatasetVersion.id, AIDataset.id)
            .order_by(
                AIDatasetVersion.created_at.desc(),
                AIDatasetVersion.id.desc(),
            )
        )
    ).all()

    training_runs = (
        await db.execute(
            select(AITrainingRun)
            .where(
                AITrainingRun.organization_context_id
                == organization_context_id
            )
            .order_by(
                AITrainingRun.requested_at.desc(),
                AITrainingRun.id.desc(),
            )
        )
    ).scalars().all()
    training_ids = [item.id for item in training_runs]

    training_states: dict[UUID, str] = {}
    if training_ids:
        state_rows = (
            await db.execute(
                select(AITrainingRunState)
                .where(
                    AITrainingRunState.training_run_id.in_(training_ids)
                )
                .order_by(
                    AITrainingRunState.training_run_id,
                    AITrainingRunState.sequence.desc(),
                )
            )
        ).scalars().all()
        for state in state_rows:
            training_states.setdefault(state.training_run_id, state.state)

    artifact_by_training: dict[UUID, UUID] = {}
    version_by_training: dict[UUID, UUID] = {}
    if training_ids:
        artifacts = (
            await db.execute(
                select(AIModelArtifact).where(
                    AIModelArtifact.training_run_id.in_(training_ids)
                )
            )
        ).scalars().all()
        artifact_by_training = {
            item.training_run_id: item.id for item in artifacts
        }

        versions_for_training = (
            await db.execute(
                select(AIModelVersion).where(
                    AIModelVersion.training_run_id.in_(training_ids)
                )
            )
        ).scalars().all()
        version_by_training = {
            item.training_run_id: item.id
            for item in versions_for_training
        }

    model_versions = (
        await db.execute(
            select(AIModelVersion)
            .join(
                AITrainingRun,
                AITrainingRun.id == AIModelVersion.training_run_id,
            )
            .where(
                AITrainingRun.organization_context_id
                == organization_context_id
            )
            .order_by(
                AIModelVersion.created_at.desc(),
                AIModelVersion.id.desc(),
            )
        )
    ).scalars().all()

    evaluation_runs = (
        await db.execute(
            select(AIEvaluationRun)
            .where(
                AIEvaluationRun.organization_context_id
                == organization_context_id
            )
            .order_by(
                AIEvaluationRun.requested_at.desc(),
                AIEvaluationRun.id.desc(),
            )
        )
    ).scalars().all()
    evaluation_ids = [item.id for item in evaluation_runs]

    evaluation_states: dict[UUID, str] = {}
    results_by_evaluation: dict[UUID, AIEvaluationResult] = {}
    if evaluation_ids:
        evaluation_state_rows = (
            await db.execute(
                select(AIEvaluationRunState)
                .where(
                    AIEvaluationRunState.evaluation_run_id.in_(
                        evaluation_ids
                    )
                )
                .order_by(
                    AIEvaluationRunState.evaluation_run_id,
                    AIEvaluationRunState.sequence.desc(),
                )
            )
        ).scalars().all()
        for state in evaluation_state_rows:
            evaluation_states.setdefault(
                state.evaluation_run_id,
                state.state,
            )

        evaluation_results = (
            await db.execute(
                select(AIEvaluationResult).where(
                    AIEvaluationResult.evaluation_run_id.in_(
                        evaluation_ids
                    )
                )
            )
        ).scalars().all()
        results_by_evaluation = {
            item.evaluation_run_id: item
            for item in evaluation_results
        }

    promotion_decisions: list[AIModelPromotionDecision] = []
    if evaluation_ids:
        promotion_decisions = list(
            (
                await db.execute(
                    select(AIModelPromotionDecision)
                    .where(
                        AIModelPromotionDecision.evaluation_run_id.in_(
                            evaluation_ids
                        )
                    )
                    .order_by(
                        AIModelPromotionDecision.decided_at.desc(),
                        AIModelPromotionDecision.id.desc(),
                    )
                )
            ).scalars().all()
        )

    return AIGovernanceRead(
        organization_context_id=organization_context_id,
        dataset_versions=tuple(
            DatasetVersionRead(
                id=version.id,
                dataset_id=dataset.id,
                dataset_name=dataset.name,
                purpose=dataset.purpose,
                version_number=version.version_number,
                dataset_digest=version.dataset_digest,
                item_count=item_count,
                created_at=version.created_at,
            )
            for version, dataset, item_count in dataset_rows
        ),
        training_runs=tuple(
            TrainingRunRead(
                id=run.id,
                dataset_version_id=run.dataset_version_id,
                model_family=run.model_family,
                state=training_states.get(run.id, "UNKNOWN"),
                requested_at=run.requested_at,
                model_artifact_id=artifact_by_training.get(run.id),
                model_version_id=version_by_training.get(run.id),
            )
            for run in training_runs
        ),
        model_versions=tuple(
            ModelVersionRead(
                id=version.id,
                training_run_id=version.training_run_id,
                dataset_version_id=version.dataset_version_id,
                model_family=version.model_family,
                semantic_version=version.semantic_version,
                attestation_sha256=version.attestation_sha256,
                attestation_byte_size=version.attestation_byte_size,
                attested_at=version.attested_at,
                created_at=version.created_at,
            )
            for version in model_versions
        ),
        evaluation_runs=tuple(
            EvaluationRunRead(
                id=run.id,
                model_version_id=run.model_version_id,
                evaluation_dataset_version_id=(
                    run.evaluation_dataset_version_id
                ),
                evaluation_policy_key=run.evaluation_policy_key,
                evaluation_policy_version=run.evaluation_policy_version,
                state=evaluation_states.get(run.id, "UNKNOWN"),
                requested_at=run.requested_at,
                result_digest=(
                    results_by_evaluation[run.id].metrics_digest
                    if run.id in results_by_evaluation
                    else None
                ),
                result_byte_size=(
                    results_by_evaluation[run.id].metrics_byte_size
                    if run.id in results_by_evaluation
                    else None
                ),
                result_attested_at=(
                    results_by_evaluation[run.id].attested_at
                    if run.id in results_by_evaluation
                    else None
                ),
            )
            for run in evaluation_runs
        ),
        promotion_decisions=tuple(
            PromotionDecisionRead(
                id=decision.id,
                model_version_id=decision.model_version_id,
                evaluation_run_id=decision.evaluation_run_id,
                reviewer_id=decision.reviewer_id,
                rationale=decision.rationale,
                decision=decision.decision,
                target_environment=decision.target_environment,
                prior_active_model_version_id=(
                    decision.prior_active_model_version_id
                ),
                decided_at=decision.decided_at,
            )
            for decision in promotion_decisions
        ),
    )
