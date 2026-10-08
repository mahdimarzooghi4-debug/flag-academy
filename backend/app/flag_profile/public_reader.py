"""Candidate-safe public read contract for explicitly applied CapabilityClaims.

Consumers must not access Flag Profile persistence directly or interpret a
learning-completion signal as an official CapabilityClaim.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.flag_profile.models import CapabilityClaim, FlagProfile

ReviewedClaimState = Literal["UNPROVEN", "EMERGING", "DEMONSTRATED", "PROVEN"]


@dataclass(frozen=True)
class CandidateSafeReviewedClaim:
    claim_id: UUID
    claim_version: int
    capability_id: UUID
    claim_state: ReviewedClaimState
    level: str
    reviewed_at: datetime


def _reviewed_claim_state(state: str) -> ReviewedClaimState:
    if state == "UNPROVEN":
        return "UNPROVEN"
    if state == "EMERGING":
        return "EMERGING"
    if state == "DEMONSTRATED":
        return "DEMONSTRATED"
    if state == "PROVEN":
        return "PROVEN"
    raise AppError(
        "PROFILE_CLAIM_STATE_INVALID",
        "Reviewed claim state is not recognized.",
        status_code=409,
    )


async def read_candidate_safe_reviewed_claims(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    subject_person_id: UUID,
    track_code: str,
    capability_definition_ids: set[UUID],
) -> dict[UUID, CandidateSafeReviewedClaim]:
    """Read only current, human-applied claims in the exact person/track/tenant."""
    if not capability_definition_ids:
        return {}

    claims = (
        await db.execute(
            select(CapabilityClaim)
            .join(FlagProfile, CapabilityClaim.flag_profile_id == FlagProfile.id)
            .where(
                FlagProfile.organization_context_id == organization_context_id,
                FlagProfile.subject_person_id == subject_person_id,
                FlagProfile.track_code == track_code,
                CapabilityClaim.organization_context_id == organization_context_id,
                CapabilityClaim.subject_person_id == subject_person_id,
                CapabilityClaim.track_code == track_code,
                CapabilityClaim.capability_id.in_(capability_definition_ids),
            )
            .order_by(CapabilityClaim.capability_id)
        )
    ).scalars().all()

    result: dict[UUID, CandidateSafeReviewedClaim] = {}
    for claim in claims:
        # Current CapabilityClaim rows are produced by explicit human Apply.
        # This public shape deliberately omits reviewer, rationale, evidence
        # provenance, confidence, and other assessment-private fields.
        result[claim.capability_id] = CandidateSafeReviewedClaim(
            claim_id=claim.id,
            claim_version=claim.version,
            capability_id=claim.capability_id,
            claim_state=_reviewed_claim_state(claim.state),
            level=claim.level,
            reviewed_at=claim.reviewed_at,
        )
    return result
