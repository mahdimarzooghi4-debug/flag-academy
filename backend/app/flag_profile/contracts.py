from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.flag_profile.domain import ProfileUpdateCaseState
from app.flag_profile.models import (
    CapabilityClaim,
    CapabilityClaimPattern,
    FlagProfile,
    ProfileUpdateCase,
    ProfileUpdatePattern,
    ProfileUpdatePatternEvidence,
)


@dataclass(frozen=True)
class CapabilityClaimEvidenceLineageContract:
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


@dataclass(frozen=True)
class CapabilityClaimPatternLineageContract:
    pattern_id: UUID
    pattern_version: int
    relationship: str
    pattern_status: str
    behaviour_code: str
    scope: str
    reviewed_at: datetime
    evidence: tuple[CapabilityClaimEvidenceLineageContract, ...]


@dataclass(frozen=True)
class CurrentCapabilityClaimContract:
    claim_id: UUID
    claim_version: int
    capability_id: UUID
    state: str
    level: str
    proven_scope: str
    evidence_recency: str
    confidence_in_claim: str
    reviewed_at: datetime
    next_evidence_needed: str
    source_profile_update_case_id: UUID
    patterns: tuple[CapabilityClaimPatternLineageContract, ...]


@dataclass(frozen=True)
class CurrentFlagProfileSnapshotContract:
    flag_profile_id: UUID
    flag_profile_version: int
    organization_context_id: UUID
    subject_person_id: UUID
    track_code: str
    profile_updated_at: datetime
    claims: tuple[CurrentCapabilityClaimContract, ...]


def _lineage_error(message: str, *, details: dict | None = None) -> AppError:
    return AppError(
        "FLAG_PROFILE_SNAPSHOT_LINEAGE_INCOMPLETE",
        message,
        status_code=409,
        details=details,
    )


def _source_case_matches_claim(
    source_case: ProfileUpdateCase,
    claim: CapabilityClaim,
) -> bool:
    return (
        source_case.state == ProfileUpdateCaseState.APPLIED.value
        and source_case.flag_profile_id == claim.flag_profile_id
        and source_case.organization_context_id == claim.organization_context_id
        and source_case.subject_person_id == claim.subject_person_id
        and source_case.track_code == claim.track_code
        and source_case.capability_id == claim.capability_id
        and source_case.reviewed_claim_state == claim.state
        and source_case.reviewed_level == claim.level
        and source_case.reviewed_proven_scope == claim.proven_scope
        and source_case.reviewed_evidence_recency == claim.evidence_recency
        and source_case.reviewed_confidence_in_claim == claim.confidence_in_claim
        and source_case.reviewed_next_evidence_needed == claim.next_evidence_needed
        and source_case.reviewed_at == claim.reviewed_at
        and source_case.reviewed_by == claim.reviewed_by
    )


async def _load_claim_pattern_lineage(
    db: AsyncSession,
    *,
    claim: CapabilityClaim,
    source_case: ProfileUpdateCase,
) -> tuple[CapabilityClaimPatternLineageContract, ...]:
    claim_pattern_rows = (
        await db.execute(
            select(CapabilityClaimPattern)
            .where(CapabilityClaimPattern.capability_claim_id == claim.id)
            .order_by(
                CapabilityClaimPattern.pattern_id,
                CapabilityClaimPattern.pattern_version,
            )
        )
    ).scalars().all()
    if not claim_pattern_rows:
        raise _lineage_error(
            "Current Capability Claim has no Reviewed Pattern lineage.",
            details={"claim_id": str(claim.id)},
        )

    source_pattern_rows = (
        await db.execute(
            select(ProfileUpdatePattern)
            .where(ProfileUpdatePattern.profile_update_case_id == source_case.id)
            .order_by(
                ProfileUpdatePattern.pattern_id,
                ProfileUpdatePattern.pattern_version,
            )
        )
    ).scalars().all()

    claim_keys = {
        (row.pattern_id, row.pattern_version, row.relationship)
        for row in claim_pattern_rows
    }
    source_by_key = {
        (row.pattern_id, row.pattern_version, row.relationship): row
        for row in source_pattern_rows
    }
    if claim_keys != set(source_by_key):
        raise _lineage_error(
            "Current Capability Claim Pattern lineage does not match its applied source.",
            details={"claim_id": str(claim.id)},
        )

    patterns: list[CapabilityClaimPatternLineageContract] = []
    for claim_pattern in claim_pattern_rows:
        key = (
            claim_pattern.pattern_id,
            claim_pattern.pattern_version,
            claim_pattern.relationship,
        )
        pattern = source_by_key[key]
        evidence_rows = (
            await db.execute(
                select(ProfileUpdatePatternEvidence)
                .where(
                    ProfileUpdatePatternEvidence.profile_update_pattern_id
                    == pattern.id,
                )
                .order_by(
                    ProfileUpdatePatternEvidence.accepted_at,
                    ProfileUpdatePatternEvidence.evidence_set_member_id,
                )
            )
        ).scalars().all()
        if not evidence_rows:
            raise _lineage_error(
                "Current Capability Claim Pattern has no Evidence lineage.",
                details={
                    "claim_id": str(claim.id),
                    "pattern_id": str(pattern.pattern_id),
                },
            )

        patterns.append(
            CapabilityClaimPatternLineageContract(
                pattern_id=pattern.pattern_id,
                pattern_version=pattern.pattern_version,
                relationship=pattern.relationship,
                pattern_status=pattern.pattern_status,
                behaviour_code=pattern.behaviour_code,
                scope=pattern.pattern_scope,
                reviewed_at=pattern.pattern_reviewed_at,
                evidence=tuple(
                    CapabilityClaimEvidenceLineageContract(
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
                ),
            )
        )

    return tuple(patterns)


async def load_current_flag_profile_snapshot(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    subject_person_id: UUID,
    track_code: str,
) -> CurrentFlagProfileSnapshotContract:
    normalized_track = track_code.strip()
    if not normalized_track:
        raise AppError(
            "PROFILE_TRACK_REQUIRED",
            "Track code is required.",
            status_code=422,
        )

    profile = (
        await db.execute(
            select(FlagProfile).where(
                FlagProfile.organization_context_id == organization_context_id,
                FlagProfile.subject_person_id == subject_person_id,
                FlagProfile.track_code == normalized_track,
            )
        )
    ).scalar_one_or_none()
    if profile is None:
        raise AppError(
            "FLAG_PROFILE_NOT_FOUND",
            "Flag Profile not found.",
            status_code=404,
        )

    claims = (
        await db.execute(
            select(CapabilityClaim)
            .where(
                CapabilityClaim.flag_profile_id == profile.id,
                CapabilityClaim.organization_context_id == organization_context_id,
                CapabilityClaim.subject_person_id == subject_person_id,
                CapabilityClaim.track_code == normalized_track,
            )
            .order_by(CapabilityClaim.capability_id, CapabilityClaim.id)
        )
    ).scalars().all()

    claim_contracts: list[CurrentCapabilityClaimContract] = []
    for claim in claims:
        source_case = (
            await db.execute(
                select(ProfileUpdateCase).where(
                    ProfileUpdateCase.id == claim.source_profile_update_case_id,
                    ProfileUpdateCase.flag_profile_id == profile.id,
                    ProfileUpdateCase.organization_context_id
                    == organization_context_id,
                    ProfileUpdateCase.subject_person_id == subject_person_id,
                    ProfileUpdateCase.track_code == normalized_track,
                    ProfileUpdateCase.capability_id == claim.capability_id,
                )
            )
        ).scalar_one_or_none()
        if source_case is None or not _source_case_matches_claim(source_case, claim):
            raise _lineage_error(
                "Current Capability Claim does not match its applied source.",
                details={"claim_id": str(claim.id)},
            )

        patterns = await _load_claim_pattern_lineage(
            db,
            claim=claim,
            source_case=source_case,
        )
        claim_contracts.append(
            CurrentCapabilityClaimContract(
                claim_id=claim.id,
                claim_version=claim.version,
                capability_id=claim.capability_id,
                state=claim.state,
                level=claim.level,
                proven_scope=claim.proven_scope,
                evidence_recency=claim.evidence_recency,
                confidence_in_claim=claim.confidence_in_claim,
                reviewed_at=claim.reviewed_at,
                next_evidence_needed=claim.next_evidence_needed,
                source_profile_update_case_id=claim.source_profile_update_case_id,
                patterns=patterns,
            )
        )

    current_version = (
        await db.execute(
            select(FlagProfile.version).where(
                FlagProfile.id == profile.id,
                FlagProfile.organization_context_id == organization_context_id,
                FlagProfile.subject_person_id == subject_person_id,
                FlagProfile.track_code == normalized_track,
            )
        )
    ).scalar_one_or_none()
    if current_version != profile.version:
        raise AppError(
            "FLAG_PROFILE_SNAPSHOT_STALE",
            "Flag Profile changed while its public snapshot was being built.",
            status_code=409,
            details={
                "expected_version": profile.version,
                "current_version": current_version,
            },
        )

    return CurrentFlagProfileSnapshotContract(
        flag_profile_id=profile.id,
        flag_profile_version=profile.version,
        organization_context_id=profile.organization_context_id,
        subject_person_id=profile.subject_person_id,
        track_code=profile.track_code,
        profile_updated_at=profile.updated_at,
        claims=tuple(claim_contracts),
    )
