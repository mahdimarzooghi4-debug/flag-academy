from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_control_plane.read_models import (
    AIGovernanceRead,
    load_ai_governance_read,
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
