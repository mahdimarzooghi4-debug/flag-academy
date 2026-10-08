from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_control_plane.read_models import (
    AIGovernanceRead,
    load_ai_governance_read,
)
from app.ai_control_plane.seed_learning import (
    ApproveDecisionSeedLearning,
    approve_decision_seed_learning,
    get_existing_seed_learning_approval,
    load_decision_seed_artifact,
)
from app.db import get_session
from app.identity.auth import ActorContext, require_role

router = APIRouter(prefix="/api/v1/admin/ai", tags=["ai-governance"])


class DatasetVersionResponse(BaseModel):
    id: UUID
    dataset_id: UUID
    dataset_name: str
    purpose: str
    version_number: int
    dataset_digest: str
    item_count: int
    created_at: datetime


class TrainingRunResponse(BaseModel):
    id: UUID
    dataset_version_id: UUID
    model_family: str
    state: str
    requested_at: datetime
    model_artifact_id: UUID | None
    model_version_id: UUID | None


class ModelVersionResponse(BaseModel):
    id: UUID
    training_run_id: UUID
    dataset_version_id: UUID
    model_family: str
    semantic_version: str
    attestation_sha256: str
    attestation_byte_size: int
    attested_at: datetime
    created_at: datetime


class EvaluationRunResponse(BaseModel):
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


class PromotionDecisionResponse(BaseModel):
    id: UUID
    model_version_id: UUID
    evaluation_run_id: UUID
    reviewer_id: UUID
    rationale: str
    decision: str
    target_environment: str
    prior_active_model_version_id: UUID | None
    decided_at: datetime





class SeedLearningPreviewResponse(BaseModel):
    seed_key: str
    source_reference: str
    source_version: str
    source_payload_digest: str
    record_count: int
    dataset_name: str
    purpose: str
    source_policy_key: str
    source_policy_version: str
    source_type: str
    data_classification: str
    approved: bool
    approval_event_id: UUID | None
    approved_by: UUID | None


class SeedLearningApprovalRequest(BaseModel):
    expected_source_payload_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )
    approval_reference: str = Field(min_length=1, max_length=255)


class SeedLearningApprovalResponse(BaseModel):
    approval_event_id: UUID
    source_payload_digest: str
    record_count: int
    dataset_name: str
    purpose: str
    source_reference: str
    source_version: str
    approval_reference: str
    reviewer_id: UUID
    created: bool
    dataset_creation_pending: bool


class AIGovernanceResponse(BaseModel):
    organization_context_id: UUID
    dataset_versions: list[DatasetVersionResponse]
    training_runs: list[TrainingRunResponse]
    model_versions: list[ModelVersionResponse]
    evaluation_runs: list[EvaluationRunResponse]
    promotion_decisions: list[PromotionDecisionResponse]


def _response(read: AIGovernanceRead) -> AIGovernanceResponse:
    return AIGovernanceResponse(
        organization_context_id=read.organization_context_id,
        dataset_versions=[
            DatasetVersionResponse(**item.__dict__)
            for item in read.dataset_versions
        ],
        training_runs=[
            TrainingRunResponse(**item.__dict__)
            for item in read.training_runs
        ],
        model_versions=[
            ModelVersionResponse(**item.__dict__)
            for item in read.model_versions
        ],
        evaluation_runs=[
            EvaluationRunResponse(**item.__dict__)
            for item in read.evaluation_runs
        ],
        promotion_decisions=[
            PromotionDecisionResponse(**item.__dict__)
            for item in read.promotion_decisions
        ],
    )


@router.get("/governance", response_model=AIGovernanceResponse)
async def get_ai_governance(
    actor: Annotated[
        ActorContext,
        Depends(require_role("ACADEMY_ADMIN")),
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> AIGovernanceResponse:
    read = await load_ai_governance_read(
        db,
        organization_context_id=actor.organization_context_id,
    )
    return _response(read)



@router.get(
    "/seed-learning/decision-making-v1",
    response_model=SeedLearningPreviewResponse,
)
async def get_decision_seed_learning_preview(
    actor: Annotated[
        ActorContext,
        Depends(require_role("ACADEMY_ADMIN")),
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SeedLearningPreviewResponse:
    artifact = load_decision_seed_artifact()
    existing = await get_existing_seed_learning_approval(
        db,
        organization_context_id=actor.organization_context_id,
    )
    approved_by: UUID | None = None
    if existing is not None and existing.actor.get("type") == "PERSON":
        try:
            approved_by = UUID(str(existing.actor.get("id")))
        except (TypeError, ValueError):
            approved_by = None

    return SeedLearningPreviewResponse(
        seed_key=artifact.key,
        source_reference=artifact.source_reference,
        source_version=artifact.source_version,
        source_payload_digest=artifact.source_payload_digest,
        record_count=artifact.record_count,
        dataset_name=artifact.dataset_name,
        purpose=artifact.purpose,
        source_policy_key=artifact.source_policy_key,
        source_policy_version=artifact.source_policy_version,
        source_type=artifact.source_type,
        data_classification=artifact.data_classification,
        approved=existing is not None,
        approval_event_id=None if existing is None else existing.event_id,
        approved_by=approved_by,
    )


@router.post(
    "/seed-learning/decision-making-v1/approve",
    response_model=SeedLearningApprovalResponse,
)
async def approve_decision_seed_for_learning(
    body: SeedLearningApprovalRequest,
    actor: Annotated[
        ActorContext,
        Depends(require_role("ACADEMY_ADMIN")),
    ],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> SeedLearningApprovalResponse:
    result = await approve_decision_seed_learning(
        db,
        command=ApproveDecisionSeedLearning(
            organization_context_id=actor.organization_context_id,
            reviewer_id=actor.person_id,
            expected_source_payload_digest=(
                body.expected_source_payload_digest
            ),
            approval_reference=body.approval_reference,
            trace_id=actor.trace_id,
        ),
    )
    await db.commit()
    return SeedLearningApprovalResponse(
        approval_event_id=result.approval_event_id,
        source_payload_digest=result.source_payload_digest,
        record_count=result.record_count,
        dataset_name=result.dataset_name,
        purpose=result.purpose,
        source_reference=result.source_reference,
        source_version=result.source_version,
        approval_reference=result.approval_reference,
        reviewer_id=result.reviewer_id,
        created=result.created,
        dataset_creation_pending=True,
    )
