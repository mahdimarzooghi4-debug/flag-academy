from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.errors import AppError
from app.flag_profile.application import (
    ApplyProfileUpdateCaseCommand,
    ApproveProfileUpdateCaseCommand,
    CreateProfileUpdateCaseCommand,
    ProfileUpdatePatternInput,
    RequestProfileUpdateReviewCommand,
    apply_profile_update_case,
    approve_profile_update_case,
    create_profile_update_case,
    request_profile_update_review,
)
from app.flag_profile.domain import (
    CapabilityClaimState,
    CapabilityLevel,
    ClaimPatternRelationship,
)
from app.flag_profile.models import (
    CapabilityClaim,
    CapabilityClaimPattern,
    FlagProfile,
    ProfileUpdateCase,
    ProfileUpdatePattern,
    ProfileUpdatePatternEvidence,
)
from app.flag_profile.pattern_reader import ReviewedPatternReader
from app.identity.auth import ActorContext, require_role

router = APIRouter(prefix="/api/v1", tags=["flag-profile"])


class ProfileUpdatePatternRequest(BaseModel):
    pattern_id: UUID
    relationship: ClaimPatternRelationship


class ProfileUpdateCaseCreateRequest(BaseModel):
    subject_person_id: UUID
    track_code: str = Field(min_length=1, max_length=128)
    capability_id: UUID
    patterns: list[ProfileUpdatePatternRequest] = Field(min_length=1)
    proposed_claim_state: CapabilityClaimState
    proposed_level: CapabilityLevel
    proposed_proven_scope: str = Field(min_length=1, max_length=255)
    proposed_evidence_recency: str = Field(min_length=1, max_length=255)
    proposed_confidence_in_claim: str = Field(min_length=1, max_length=64)
    proposed_next_evidence_needed: str = Field(min_length=1, max_length=8000)
    rationale: str = Field(min_length=1, max_length=8000)
    expected_version: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=160)


class ProfileUpdateReviewRequest(BaseModel):
    expected_version: int = Field(ge=1)


class ProfileUpdateApprovalRequest(BaseModel):
    reviewed_claim_state: CapabilityClaimState
    reviewed_level: CapabilityLevel
    reviewed_proven_scope: str = Field(min_length=1, max_length=255)
    reviewed_evidence_recency: str = Field(min_length=1, max_length=255)
    reviewed_confidence_in_claim: str = Field(min_length=1, max_length=64)
    reviewed_next_evidence_needed: str = Field(min_length=1, max_length=8000)
    rationale: str = Field(min_length=1, max_length=8000)
    expected_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=160)


class ProfileUpdateApplyRequest(BaseModel):
    expected_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=160)


class ProfileUpdatePatternSummaryResponse(BaseModel):
    pattern_id: UUID
    pattern_version: int
    relationship: str
    pattern_status: str
    behaviour_code: str
    scope: str
    reviewed_at: datetime


class ProfileUpdateCaseResponse(BaseModel):
    id: UUID
    version: int
    subject_person_id: UUID
    track_code: str
    capability_id: UUID
    state: str
    current_claim_id: UUID | None
    current_claim_version: int | None
    current_claim_state: str | None
    current_level: str | None
    current_proven_scope: str | None
    current_evidence_recency: str | None
    current_confidence_in_claim: str | None
    current_next_evidence_needed: str | None
    proposed_claim_state: str
    proposed_level: str
    proposed_proven_scope: str
    proposed_evidence_recency: str
    proposed_confidence_in_claim: str
    proposed_next_evidence_needed: str
    rationale: str
    reviewed_claim_state: str | None
    reviewed_level: str | None
    reviewed_proven_scope: str | None
    reviewed_evidence_recency: str | None
    reviewed_confidence_in_claim: str | None
    reviewed_next_evidence_needed: str | None
    review_rationale: str | None
    created_by: UUID
    reviewed_by: UUID | None
    reviewed_at: datetime | None
    applied_by: UUID | None
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime
    patterns: list[ProfileUpdatePatternSummaryResponse]


class ProfileUpdateEvidenceLineageResponse(BaseModel):
    evidence_set_member_id: UUID
    evidence_case_id: UUID
    interpretation_id: UUID
    interpretation_version: int
    evidence_relationship: str
    signal: str
    scope: str
    confidence: str
    context_difficulty: str
    prompt_contamination: str
    source_independence_group: str
    accepted_at: datetime
    source_observation_id: UUID
    source_context: str
    source_reference: str
    observation_type: str


class ProfileUpdatePatternLineageResponse(ProfileUpdatePatternSummaryResponse):
    evidence: list[ProfileUpdateEvidenceLineageResponse]


class ProfileUpdateLineageResponse(BaseModel):
    profile_update_case: ProfileUpdateCaseResponse
    patterns: list[ProfileUpdatePatternLineageResponse]


class CapabilityClaimPatternResponse(BaseModel):
    pattern_id: UUID
    pattern_version: int
    relationship: str


class CapabilityClaimResponse(BaseModel):
    id: UUID
    version: int
    capability_id: UUID
    state: str
    level: str
    proven_scope: str
    evidence_recency: str
    confidence_in_claim: str
    reviewed_at: datetime
    reviewed_by: UUID
    next_evidence_needed: str
    source_profile_update_case_id: UUID
    updated_at: datetime
    patterns: list[CapabilityClaimPatternResponse]


class FlagProfileResponse(BaseModel):
    id: UUID
    version: int
    subject_person_id: UUID
    track_code: str
    updated_at: datetime
    claims: list[CapabilityClaimResponse]


class PersonFlagProfileResponse(BaseModel):
    subject_person_id: UUID
    profiles: list[FlagProfileResponse]


class CapabilityClaimLineageResponse(BaseModel):
    claim: CapabilityClaimResponse
    source_profile_update_case_id: UUID
    source_profile_update_case_state: str
    source_profile_update_reviewed_by: UUID
    source_profile_update_reviewed_at: datetime
    patterns: list[ProfileUpdatePatternLineageResponse]


async def _case_patterns(
    db: AsyncSession,
    *,
    case_id: UUID,
) -> list[ProfileUpdatePattern]:
    return list(
        (
            await db.execute(
                select(ProfileUpdatePattern)
                .where(ProfileUpdatePattern.profile_update_case_id == case_id)
                .order_by(
                    ProfileUpdatePattern.pattern_reviewed_at,
                    ProfileUpdatePattern.pattern_id,
                )
            )
        ).scalars().all()
    )


async def _case_response(
    db: AsyncSession,
    update_case: ProfileUpdateCase,
) -> ProfileUpdateCaseResponse:
    patterns = await _case_patterns(db, case_id=update_case.id)
    return ProfileUpdateCaseResponse(
        id=update_case.id,
        version=update_case.version,
        subject_person_id=update_case.subject_person_id,
        track_code=update_case.track_code,
        capability_id=update_case.capability_id,
        state=update_case.state,
        current_claim_id=update_case.current_claim_id,
        current_claim_version=update_case.current_claim_version,
        current_claim_state=update_case.current_claim_state,
        current_level=update_case.current_level,
        current_proven_scope=update_case.current_proven_scope,
        current_evidence_recency=update_case.current_evidence_recency,
        current_confidence_in_claim=update_case.current_confidence_in_claim,
        current_next_evidence_needed=update_case.current_next_evidence_needed,
        proposed_claim_state=update_case.proposed_claim_state,
        proposed_level=update_case.proposed_level,
        proposed_proven_scope=update_case.proposed_proven_scope,
        proposed_evidence_recency=update_case.proposed_evidence_recency,
        proposed_confidence_in_claim=update_case.proposed_confidence_in_claim,
        proposed_next_evidence_needed=update_case.proposed_next_evidence_needed,
        rationale=update_case.rationale,
        reviewed_claim_state=update_case.reviewed_claim_state,
        reviewed_level=update_case.reviewed_level,
        reviewed_proven_scope=update_case.reviewed_proven_scope,
        reviewed_evidence_recency=update_case.reviewed_evidence_recency,
        reviewed_confidence_in_claim=update_case.reviewed_confidence_in_claim,
        reviewed_next_evidence_needed=update_case.reviewed_next_evidence_needed,
        review_rationale=update_case.review_rationale,
        created_by=update_case.created_by,
        reviewed_by=update_case.reviewed_by,
        reviewed_at=update_case.reviewed_at,
        applied_by=update_case.applied_by,
        applied_at=update_case.applied_at,
        created_at=update_case.created_at,
        updated_at=update_case.updated_at,
        patterns=[
            ProfileUpdatePatternSummaryResponse(
                pattern_id=pattern.pattern_id,
                pattern_version=pattern.pattern_version,
                relationship=pattern.relationship,
                pattern_status=pattern.pattern_status,
                behaviour_code=pattern.behaviour_code,
                scope=pattern.pattern_scope,
                reviewed_at=pattern.pattern_reviewed_at,
            )
            for pattern in patterns
        ],
    )


async def _load_case(
    db: AsyncSession,
    *,
    actor: ActorContext,
    case_id: UUID,
) -> ProfileUpdateCase:
    update_case = (
        await db.execute(
            select(ProfileUpdateCase).where(
                ProfileUpdateCase.id == case_id,
                ProfileUpdateCase.organization_context_id
                == actor.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if update_case is None:
        raise AppError(
            "PROFILE_UPDATE_CASE_NOT_FOUND",
            "Profile update case not found.",
            status_code=404,
        )
    return update_case


async def _profile_update_lineage_response(
    db: AsyncSession,
    update_case: ProfileUpdateCase,
) -> ProfileUpdateLineageResponse:
    pattern_rows = await _case_patterns(db, case_id=update_case.id)
    if not pattern_rows:
        raise AppError(
            "PROFILE_UPDATE_LINEAGE_INCOMPLETE",
            "Profile update case has no Reviewed Pattern lineage.",
            status_code=409,
        )

    patterns: list[ProfileUpdatePatternLineageResponse] = []
    for pattern in pattern_rows:
        evidence_rows = list(
            (
                await db.execute(
                    select(ProfileUpdatePatternEvidence)
                    .where(
                        ProfileUpdatePatternEvidence.profile_update_pattern_id
                        == pattern.id
                    )
                    .order_by(
                        ProfileUpdatePatternEvidence.accepted_at,
                        ProfileUpdatePatternEvidence.evidence_set_member_id,
                    )
                )
            ).scalars().all()
        )
        if not evidence_rows:
            raise AppError(
                "PROFILE_UPDATE_LINEAGE_INCOMPLETE",
                "Profile update Pattern has no Evidence lineage.",
                status_code=409,
                details={"pattern_id": str(pattern.pattern_id)},
            )
        patterns.append(
            ProfileUpdatePatternLineageResponse(
                pattern_id=pattern.pattern_id,
                pattern_version=pattern.pattern_version,
                relationship=pattern.relationship,
                pattern_status=pattern.pattern_status,
                behaviour_code=pattern.behaviour_code,
                scope=pattern.pattern_scope,
                reviewed_at=pattern.pattern_reviewed_at,
                evidence=[
                    ProfileUpdateEvidenceLineageResponse(
                        evidence_set_member_id=evidence.evidence_set_member_id,
                        evidence_case_id=evidence.evidence_case_id,
                        interpretation_id=evidence.interpretation_id,
                        interpretation_version=evidence.interpretation_version,
                        evidence_relationship=evidence.evidence_relationship,
                        signal=evidence.signal,
                        scope=evidence.evidence_scope,
                        confidence=evidence.confidence,
                        context_difficulty=evidence.context_difficulty,
                        prompt_contamination=evidence.prompt_contamination,
                        source_independence_group=evidence.source_independence_group,
                        accepted_at=evidence.accepted_at,
                        source_observation_id=evidence.source_observation_id,
                        source_context=evidence.source_context,
                        source_reference=evidence.source_reference,
                        observation_type=evidence.observation_type,
                    )
                    for evidence in evidence_rows
                ],
            )
        )

    return ProfileUpdateLineageResponse(
        profile_update_case=await _case_response(db, update_case),
        patterns=patterns,
    )


async def _claim_response(
    db: AsyncSession,
    claim: CapabilityClaim,
) -> CapabilityClaimResponse:
    refs = list(
        (
            await db.execute(
                select(CapabilityClaimPattern)
                .where(CapabilityClaimPattern.capability_claim_id == claim.id)
                .order_by(CapabilityClaimPattern.pattern_id)
            )
        ).scalars().all()
    )
    return CapabilityClaimResponse(
        id=claim.id,
        version=claim.version,
        capability_id=claim.capability_id,
        state=claim.state,
        level=claim.level,
        proven_scope=claim.proven_scope,
        evidence_recency=claim.evidence_recency,
        confidence_in_claim=claim.confidence_in_claim,
        reviewed_at=claim.reviewed_at,
        reviewed_by=claim.reviewed_by,
        next_evidence_needed=claim.next_evidence_needed,
        source_profile_update_case_id=claim.source_profile_update_case_id,
        updated_at=claim.updated_at,
        patterns=[
            CapabilityClaimPatternResponse(
                pattern_id=ref.pattern_id,
                pattern_version=ref.pattern_version,
                relationship=ref.relationship,
            )
            for ref in refs
        ],
    )


@router.get("/profile-update-cases", response_model=list[ProfileUpdateCaseResponse])
async def list_profile_update_cases(
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    subject_person_id: UUID | None = None,
) -> list[ProfileUpdateCaseResponse]:
    query = select(ProfileUpdateCase).where(
        ProfileUpdateCase.organization_context_id == actor.organization_context_id
    )
    if subject_person_id is not None:
        query = query.where(ProfileUpdateCase.subject_person_id == subject_person_id)
    cases = list(
        (
            await db.execute(
                query.order_by(
                    ProfileUpdateCase.updated_at.desc(),
                    ProfileUpdateCase.id,
                )
            )
        ).scalars().all()
    )
    return [await _case_response(db, item) for item in cases]


@router.get(
    "/profile-update-cases/{case_id}",
    response_model=ProfileUpdateCaseResponse,
)
async def get_profile_update_case(
    case_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProfileUpdateCaseResponse:
    return await _case_response(
        db,
        await _load_case(db, actor=actor, case_id=case_id),
    )


@router.get(
    "/profile-update-cases/{case_id}/lineage",
    response_model=ProfileUpdateLineageResponse,
)
async def get_profile_update_case_lineage(
    case_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProfileUpdateLineageResponse:
    update_case = await _load_case(db, actor=actor, case_id=case_id)
    return await _profile_update_lineage_response(db, update_case)


@router.post(
    "/profile-update-cases",
    response_model=ProfileUpdateCaseResponse,
    status_code=201,
)
async def create_profile_update_case_api(
    body: ProfileUpdateCaseCreateRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProfileUpdateCaseResponse:
    update_case = await create_profile_update_case(
        db,
        reader=ReviewedPatternReader(db),
        command=CreateProfileUpdateCaseCommand(
            organization_context_id=actor.organization_context_id,
            subject_person_id=body.subject_person_id,
            track_code=body.track_code,
            capability_id=body.capability_id,
            patterns=tuple(
                ProfileUpdatePatternInput(
                    pattern_id=item.pattern_id,
                    relationship=item.relationship.value,
                )
                for item in body.patterns
            ),
            proposed_claim_state=body.proposed_claim_state.value,
            proposed_level=body.proposed_level.value,
            proposed_proven_scope=body.proposed_proven_scope,
            proposed_evidence_recency=body.proposed_evidence_recency,
            proposed_confidence_in_claim=body.proposed_confidence_in_claim,
            proposed_next_evidence_needed=body.proposed_next_evidence_needed,
            rationale=body.rationale,
            created_by=actor.person_id,
            expected_version=body.expected_version,
            idempotency_key=body.idempotency_key,
            trace_id=actor.trace_id,
        ),
    )
    return await _case_response(db, update_case)


@router.post(
    "/profile-update-cases/{case_id}/request-review",
    response_model=ProfileUpdateCaseResponse,
)
async def request_profile_update_case_review_api(
    case_id: UUID,
    body: ProfileUpdateReviewRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProfileUpdateCaseResponse:
    update_case = await request_profile_update_review(
        db,
        command=RequestProfileUpdateReviewCommand(
            organization_context_id=actor.organization_context_id,
            profile_update_case_id=case_id,
            expected_version=body.expected_version,
            trace_id=actor.trace_id,
        ),
    )
    return await _case_response(db, update_case)


@router.post(
    "/profile-update-cases/{case_id}/approve",
    response_model=ProfileUpdateCaseResponse,
)
async def approve_profile_update_case_api(
    case_id: UUID,
    body: ProfileUpdateApprovalRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> ProfileUpdateCaseResponse:
    update_case = await approve_profile_update_case(
        db,
        command=ApproveProfileUpdateCaseCommand(
            organization_context_id=actor.organization_context_id,
            profile_update_case_id=case_id,
            reviewer_id=actor.person_id,
            reviewed_claim_state=body.reviewed_claim_state.value,
            reviewed_level=body.reviewed_level.value,
            reviewed_proven_scope=body.reviewed_proven_scope,
            reviewed_evidence_recency=body.reviewed_evidence_recency,
            reviewed_confidence_in_claim=body.reviewed_confidence_in_claim,
            reviewed_next_evidence_needed=body.reviewed_next_evidence_needed,
            rationale=body.rationale,
            expected_version=body.expected_version,
            idempotency_key=body.idempotency_key,
            trace_id=actor.trace_id,
        ),
    )
    return await _case_response(db, update_case)


@router.post(
    "/profile-update-cases/{case_id}/apply",
    response_model=CapabilityClaimResponse,
)
async def apply_profile_update_case_api(
    case_id: UUID,
    body: ProfileUpdateApplyRequest,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CapabilityClaimResponse:
    claim = await apply_profile_update_case(
        db,
        command=ApplyProfileUpdateCaseCommand(
            organization_context_id=actor.organization_context_id,
            profile_update_case_id=case_id,
            applied_by=actor.person_id,
            expected_version=body.expected_version,
            idempotency_key=body.idempotency_key,
            trace_id=actor.trace_id,
        ),
    )
    return await _claim_response(db, claim)


@router.get(
    "/people/{person_id}/flag-profile",
    response_model=PersonFlagProfileResponse,
)
async def get_flag_profile(
    person_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PersonFlagProfileResponse:
    profiles = list(
        (
            await db.execute(
                select(FlagProfile)
                .where(
                    FlagProfile.organization_context_id
                    == actor.organization_context_id,
                    FlagProfile.subject_person_id == person_id,
                )
                .order_by(FlagProfile.track_code, FlagProfile.id)
            )
        ).scalars().all()
    )

    responses: list[FlagProfileResponse] = []
    for profile in profiles:
        claims = list(
            (
                await db.execute(
                    select(CapabilityClaim)
                    .where(
                        CapabilityClaim.flag_profile_id == profile.id,
                        CapabilityClaim.organization_context_id
                        == actor.organization_context_id,
                    )
                    .order_by(CapabilityClaim.capability_id)
                )
            ).scalars().all()
        )
        responses.append(
            FlagProfileResponse(
                id=profile.id,
                version=profile.version,
                subject_person_id=profile.subject_person_id,
                track_code=profile.track_code,
                updated_at=profile.updated_at,
                claims=[await _claim_response(db, claim) for claim in claims],
            )
        )

    return PersonFlagProfileResponse(
        subject_person_id=person_id,
        profiles=responses,
    )


@router.get(
    "/profile/claims/{claim_id}/lineage",
    response_model=CapabilityClaimLineageResponse,
)
async def get_capability_claim_lineage(
    claim_id: UUID,
    actor: Annotated[ActorContext, Depends(require_role("ASSESSOR"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CapabilityClaimLineageResponse:
    claim = (
        await db.execute(
            select(CapabilityClaim).where(
                CapabilityClaim.id == claim_id,
                CapabilityClaim.organization_context_id
                == actor.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if claim is None:
        raise AppError(
            "PROFILE_CLAIM_NOT_FOUND",
            "Capability Claim not found.",
            status_code=404,
        )

    update_case = (
        await db.execute(
            select(ProfileUpdateCase).where(
                ProfileUpdateCase.id == claim.source_profile_update_case_id,
                ProfileUpdateCase.organization_context_id
                == actor.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if (
        update_case is None
        or update_case.reviewed_by is None
        or update_case.reviewed_at is None
    ):
        raise AppError(
            "PROFILE_CLAIM_LINEAGE_INCOMPLETE",
            "Capability Claim Profile Update lineage is incomplete.",
            status_code=409,
        )

    lineage = await _profile_update_lineage_response(db, update_case)
    return CapabilityClaimLineageResponse(
        claim=await _claim_response(db, claim),
        source_profile_update_case_id=update_case.id,
        source_profile_update_case_state=update_case.state,
        source_profile_update_reviewed_by=update_case.reviewed_by,
        source_profile_update_reviewed_at=update_case.reviewed_at,
        patterns=lineage.patterns,
    )
