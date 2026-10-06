from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.identity.auth import ActorContext, require_role
from app.patterns.models import (
    BehaviourPattern,
    EvidenceSet,
    EvidenceSetMember,
    PatternCandidate,
    PatternCandidateEvidence,
    PatternReview,
)

router = APIRouter(prefix="/api/v1", tags=["patterns"])


class PatternSummaryResponse(BaseModel):
    id: UUID
    version: int
    subject_person_id: UUID
    behaviour_code: str
    behaviour_description: str
    pattern_status: str
    scope: str
    reviewed_by: UUID
    reviewed_at: datetime
    updated_at: datetime


class PatternCandidateLineageResponse(BaseModel):
    id: UUID
    version: int
    proposed_pattern_status: str
    behaviour_code: str
    behaviour_description: str
    scope: str
    rationale: str
    created_by: UUID
    created_at: datetime


class EvidenceSetLineageResponse(BaseModel):
    id: UUID
    evidence_set_key: UUID
    version_number: int
    created_by: UUID
    created_at: datetime


class PatternReviewLineageResponse(BaseModel):
    id: UUID
    reviewer_id: UUID
    resulting_pattern_status: str
    rationale: str
    created_at: datetime


class PatternSourceLineageResponse(BaseModel):
    source_observation_id: str
    source_context: str
    source_reference: str
    observation_type: str


class PatternEvidenceLineageResponse(BaseModel):
    relationship: str
    evidence_set_member_id: UUID
    evidence_case_id: UUID
    interpretation_id: UUID
    interpretation_version: int
    behaviour_code: str
    signal: str
    scope: str
    confidence: str
    context_difficulty: str
    prompt_contamination: str
    source_independence_group: str
    accepted_at: datetime
    target_links: list[dict]
    source_lineage: PatternSourceLineageResponse


class ReviewedPatternLineageResponse(BaseModel):
    id: UUID
    version: int
    organization_context_id: UUID
    subject_person_id: UUID
    behaviour_code: str
    behaviour_description: str
    pattern_status: str
    scope: str
    rationale: str
    reviewed_by: UUID
    reviewed_at: datetime
    created_at: datetime
    updated_at: datetime
    candidate: PatternCandidateLineageResponse
    evidence_set: EvidenceSetLineageResponse
    review: PatternReviewLineageResponse
    evidence: list[PatternEvidenceLineageResponse]


def _source_lineage_response(value: dict) -> PatternSourceLineageResponse:
    try:
        return PatternSourceLineageResponse(
            source_observation_id=str(value["source_observation_id"]),
            source_context=str(value["source_context"]),
            source_reference=str(value["source_reference"]),
            observation_type=str(value["observation_type"]),
        )
    except KeyError as exc:
        raise AppError(
            "PATTERN_LINEAGE_INCOMPLETE",
            "Pattern source lineage is incomplete.",
            status_code=409,
        ) from exc


async def _load_pattern(
    db: AsyncSession,
    *,
    actor: ActorContext,
    pattern_id: UUID,
) -> BehaviourPattern:
    pattern = (
        await db.execute(
            select(BehaviourPattern).where(
                BehaviourPattern.id == pattern_id,
                BehaviourPattern.organization_context_id
                == actor.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if pattern is None:
        raise AppError(
            "PATTERN_NOT_FOUND",
            "Reviewed Pattern not found.",
            status_code=404,
        )
    return pattern


async def _lineage_response(
    db: AsyncSession,
    pattern: BehaviourPattern,
) -> ReviewedPatternLineageResponse:
    candidate = (
        await db.execute(
            select(PatternCandidate).where(
                PatternCandidate.id == pattern.source_pattern_candidate_id,
                PatternCandidate.organization_context_id
                == pattern.organization_context_id,
                PatternCandidate.subject_person_id == pattern.subject_person_id,
            )
        )
    ).scalar_one_or_none()
    evidence_set = (
        await db.execute(
            select(EvidenceSet).where(
                EvidenceSet.id == pattern.evidence_set_id,
                EvidenceSet.organization_context_id
                == pattern.organization_context_id,
                EvidenceSet.subject_person_id == pattern.subject_person_id,
            )
        )
    ).scalar_one_or_none()
    review = (
        await db.execute(
            select(PatternReview).where(
                PatternReview.pattern_candidate_id
                == pattern.source_pattern_candidate_id,
                PatternReview.resulting_pattern_id == pattern.id,
            )
        )
    ).scalar_one_or_none()

    if candidate is None or evidence_set is None or review is None:
        raise AppError(
            "PATTERN_LINEAGE_INCOMPLETE",
            "Reviewed Pattern lineage is incomplete.",
            status_code=409,
        )

    rows = (
        await db.execute(
            select(PatternCandidateEvidence, EvidenceSetMember)
            .join(
                EvidenceSetMember,
                EvidenceSetMember.id
                == PatternCandidateEvidence.evidence_set_member_id,
            )
            .where(
                PatternCandidateEvidence.pattern_candidate_id == candidate.id,
                EvidenceSetMember.evidence_set_id == evidence_set.id,
            )
            .order_by(EvidenceSetMember.created_at, EvidenceSetMember.id)
        )
    ).all()
    if not rows:
        raise AppError(
            "PATTERN_LINEAGE_INCOMPLETE",
            "Reviewed Pattern has no Evidence lineage.",
            status_code=409,
        )

    evidence = [
        PatternEvidenceLineageResponse(
            relationship=relation.relationship,
            evidence_set_member_id=member.id,
            evidence_case_id=member.evidence_case_id,
            interpretation_id=member.interpretation_id,
            interpretation_version=member.interpretation_version,
            behaviour_code=member.behaviour_code,
            signal=member.signal,
            scope=member.scope,
            confidence=member.confidence,
            context_difficulty=member.context_difficulty,
            prompt_contamination=member.prompt_contamination,
            source_independence_group=member.source_independence_group,
            accepted_at=member.accepted_at,
            target_links=member.target_links,
            source_lineage=_source_lineage_response(member.source_lineage),
        )
        for relation, member in rows
    ]

    return ReviewedPatternLineageResponse(
        id=pattern.id,
        version=pattern.version,
        organization_context_id=pattern.organization_context_id,
        subject_person_id=pattern.subject_person_id,
        behaviour_code=pattern.behaviour_code,
        behaviour_description=pattern.behaviour_description,
        pattern_status=pattern.pattern_status,
        scope=pattern.scope,
        rationale=pattern.rationale,
        reviewed_by=pattern.reviewed_by,
        reviewed_at=pattern.reviewed_at,
        created_at=pattern.created_at,
        updated_at=pattern.updated_at,
        candidate=PatternCandidateLineageResponse(
            id=candidate.id,
            version=candidate.version,
            proposed_pattern_status=candidate.proposed_pattern_status,
            behaviour_code=candidate.behaviour_code,
            behaviour_description=candidate.behaviour_description,
            scope=candidate.scope,
            rationale=candidate.rationale,
            created_by=candidate.created_by,
            created_at=candidate.created_at,
        ),
        evidence_set=EvidenceSetLineageResponse(
            id=evidence_set.id,
            evidence_set_key=evidence_set.evidence_set_key,
            version_number=evidence_set.version_number,
            created_by=evidence_set.created_by,
            created_at=evidence_set.created_at,
        ),
        review=PatternReviewLineageResponse(
            id=review.id,
            reviewer_id=review.reviewer_id,
            resulting_pattern_status=review.resulting_pattern_status,
            rationale=review.rationale,
            created_at=review.created_at,
        ),
        evidence=evidence,
    )


@router.get("/patterns", response_model=list[PatternSummaryResponse])
async def list_reviewed_patterns(
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> list[PatternSummaryResponse]:
    patterns = (
        await db.execute(
            select(BehaviourPattern)
            .where(
                BehaviourPattern.organization_context_id
                == actor.organization_context_id
            )
            .order_by(BehaviourPattern.updated_at.desc(), BehaviourPattern.id)
        )
    ).scalars().all()
    return [
        PatternSummaryResponse(
            id=pattern.id,
            version=pattern.version,
            subject_person_id=pattern.subject_person_id,
            behaviour_code=pattern.behaviour_code,
            behaviour_description=pattern.behaviour_description,
            pattern_status=pattern.pattern_status,
            scope=pattern.scope,
            reviewed_by=pattern.reviewed_by,
            reviewed_at=pattern.reviewed_at,
            updated_at=pattern.updated_at,
        )
        for pattern in patterns
    ]


@router.get(
    "/patterns/{pattern_id}/lineage",
    response_model=ReviewedPatternLineageResponse,
)
async def get_reviewed_pattern_lineage(
    pattern_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ReviewedPatternLineageResponse:
    pattern = await _load_pattern(
        db,
        actor=actor,
        pattern_id=pattern_id,
    )
    return await _lineage_response(db, pattern)
