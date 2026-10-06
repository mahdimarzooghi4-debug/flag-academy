from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.flag_profile.domain import (
    CapabilityLevel,
    ClaimPatternRelationship,
    ProfileUpdateCaseState,
    capability_level_valid,
    claim_pattern_relationship_valid,
    profile_claim_state_valid,
)
from app.flag_profile.models import (
    CapabilityClaim,
    FlagProfile,
    ProfileUpdateCase,
    ProfileUpdatePattern,
    ProfileUpdatePatternEvidence,
)
from app.patterns.contracts import ReviewedPatternSnapshotContract


class ReviewedPatternReader(Protocol):
    async def load(
        self,
        *,
        organization_context_id: UUID,
        subject_person_id: UUID,
        pattern_ids: tuple[UUID, ...],
    ) -> list[ReviewedPatternSnapshotContract]: ...


@dataclass(frozen=True)
class ProfileUpdatePatternInput:
    pattern_id: UUID
    relationship: str


@dataclass(frozen=True)
class CreateProfileUpdateCaseCommand:
    organization_context_id: UUID
    subject_person_id: UUID
    track_code: str
    capability_id: UUID
    patterns: tuple[ProfileUpdatePatternInput, ...]
    proposed_claim_state: str
    proposed_level: str
    proposed_proven_scope: str
    proposed_evidence_recency: str
    proposed_confidence_in_claim: str
    proposed_next_evidence_needed: str
    rationale: str
    created_by: UUID
    expected_version: int
    idempotency_key: str
    trace_id: str


def _require_profile_update_create_expected_version(expected_version: int) -> None:
    if expected_version != 0:
        raise AppError(
            "VERSION_CONFLICT",
            "Profile update proposal changed. Refresh and retry.",
            status_code=409,
            details={
                "expected_version": expected_version,
                "current_version": 0,
            },
        )


def _require_create_contract(command: CreateProfileUpdateCaseCommand) -> None:
    if not command.track_code.strip():
        raise AppError(
            "PROFILE_TRACK_REQUIRED",
            "Track code is required.",
            status_code=422,
        )
    if not profile_claim_state_valid(command.proposed_claim_state):
        raise AppError(
            "PROFILE_CLAIM_STATE_INVALID",
            "Capability Claim state is invalid.",
            status_code=422,
        )
    if not capability_level_valid(command.proposed_level):
        raise AppError(
            "PROFILE_CAPABILITY_LEVEL_INVALID",
            "Capability level is invalid.",
            status_code=422,
        )

    required_text = (
        ("proven_scope", command.proposed_proven_scope),
        ("evidence_recency", command.proposed_evidence_recency),
        ("confidence_in_claim", command.proposed_confidence_in_claim),
        ("next_evidence_needed", command.proposed_next_evidence_needed),
        ("rationale", command.rationale),
    )
    missing = [name for name, value in required_text if not value.strip()]
    if missing:
        raise AppError(
            "PROFILE_UPDATE_CASE_INVALID",
            "Profile update proposal has required fields missing.",
            status_code=422,
            details={"fields": missing},
        )

    if not command.patterns:
        raise AppError(
            "PROFILE_PATTERN_REQUIRED",
            "At least one Reviewed Pattern is required.",
            status_code=422,
        )

    pattern_ids = [item.pattern_id for item in command.patterns]
    if len(pattern_ids) != len(set(pattern_ids)):
        raise AppError(
            "PROFILE_PATTERN_DUPLICATE",
            "A Reviewed Pattern may appear only once in a Profile update proposal.",
            status_code=422,
        )
    if any(
        not claim_pattern_relationship_valid(item.relationship)
        for item in command.patterns
    ):
        raise AppError(
            "PROFILE_PATTERN_RELATIONSHIP_INVALID",
            "Pattern relationship must be SUPPORTING or CONTRADICTORY.",
            status_code=422,
        )


async def _load_or_create_flag_profile(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    subject_person_id: UUID,
    track_code: str,
    now: datetime,
) -> FlagProfile:
    profile = (
        await db.execute(
            select(FlagProfile)
            .where(
                FlagProfile.organization_context_id == organization_context_id,
                FlagProfile.subject_person_id == subject_person_id,
                FlagProfile.track_code == track_code,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if profile is not None:
        return profile

    profile = FlagProfile(
        id=uuid4(),
        version=1,
        organization_context_id=organization_context_id,
        subject_person_id=subject_person_id,
        track_code=track_code,
        created_at=now,
        updated_at=now,
    )
    db.add(profile)
    await db.flush()
    return profile


async def _current_claim(
    db: AsyncSession,
    *,
    flag_profile_id: UUID,
    capability_id: UUID,
) -> CapabilityClaim | None:
    return (
        await db.execute(
            select(CapabilityClaim).where(
                CapabilityClaim.flag_profile_id == flag_profile_id,
                CapabilityClaim.capability_id == capability_id,
            )
        )
    ).scalar_one_or_none()


async def _existing_profile_update_case(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    created_by: UUID,
    idempotency_key: str,
) -> ProfileUpdateCase | None:
    return (
        await db.execute(
            select(ProfileUpdateCase).where(
                ProfileUpdateCase.organization_context_id
                == organization_context_id,
                ProfileUpdateCase.created_by == created_by,
                ProfileUpdateCase.creation_idempotency_key == idempotency_key,
            )
        )
    ).scalar_one_or_none()


async def _existing_pattern_relationships(
    db: AsyncSession,
    *,
    profile_update_case_id: UUID,
) -> set[tuple[UUID, str]]:
    rows = (
        await db.execute(
            select(
                ProfileUpdatePattern.pattern_id,
                ProfileUpdatePattern.relationship,
            ).where(
                ProfileUpdatePattern.profile_update_case_id
                == profile_update_case_id
            )
        )
    ).all()
    return {(row.pattern_id, row.relationship) for row in rows}


async def create_profile_update_case(
    db: AsyncSession,
    *,
    reader: ReviewedPatternReader,
    command: CreateProfileUpdateCaseCommand,
) -> ProfileUpdateCase:
    idempotency_key = command.idempotency_key.strip()
    if not idempotency_key:
        raise AppError(
            "PROFILE_IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency key is required.",
            status_code=422,
        )

    existing = await _existing_profile_update_case(
        db,
        organization_context_id=command.organization_context_id,
        created_by=command.created_by,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        existing_relationships = await _existing_pattern_relationships(
            db,
            profile_update_case_id=existing.id,
        )
        requested_relationships = {
            (item.pattern_id, item.relationship) for item in command.patterns
        }
        if (
            existing.subject_person_id != command.subject_person_id
            or existing.track_code != command.track_code.strip()
            or existing.capability_id != command.capability_id
            or existing.proposed_claim_state != command.proposed_claim_state
            or existing.proposed_level != command.proposed_level
            or existing.proposed_proven_scope
            != command.proposed_proven_scope.strip()
            or existing.proposed_evidence_recency
            != command.proposed_evidence_recency.strip()
            or existing.proposed_confidence_in_claim
            != command.proposed_confidence_in_claim.strip()
            or existing.proposed_next_evidence_needed
            != command.proposed_next_evidence_needed.strip()
            or existing.rationale != command.rationale.strip()
            or existing_relationships != requested_relationships
            or len(existing_relationships) != len(command.patterns)
        ):
            raise AppError(
                "PROFILE_IDEMPOTENCY_KEY_REUSED",
                "Idempotency key was already used for a different Profile update proposal.",
                status_code=409,
            )
        return existing

    _require_profile_update_create_expected_version(command.expected_version)
    _require_create_contract(command)

    requested_pattern_ids = tuple(item.pattern_id for item in command.patterns)
    snapshots = await reader.load(
        organization_context_id=command.organization_context_id,
        subject_person_id=command.subject_person_id,
        pattern_ids=requested_pattern_ids,
    )
    snapshot_by_id = {item.pattern_id: item for item in snapshots}
    missing_pattern_ids = [
        str(pattern_id)
        for pattern_id in requested_pattern_ids
        if pattern_id not in snapshot_by_id
    ]
    if missing_pattern_ids:
        raise AppError(
            "PROFILE_PATTERN_NOT_FOUND",
            "Reviewed Pattern not found.",
            status_code=404,
            details={"pattern_ids": missing_pattern_ids},
        )

    now = datetime.now(UTC)
    track_code = command.track_code.strip()
    profile = await _load_or_create_flag_profile(
        db,
        organization_context_id=command.organization_context_id,
        subject_person_id=command.subject_person_id,
        track_code=track_code,
        now=now,
    )
    current_claim = await _current_claim(
        db,
        flag_profile_id=profile.id,
        capability_id=command.capability_id,
    )

    update_case = ProfileUpdateCase(
        id=uuid4(),
        version=1,
        flag_profile_id=profile.id,
        organization_context_id=command.organization_context_id,
        subject_person_id=command.subject_person_id,
        track_code=track_code,
        capability_id=command.capability_id,
        state=ProfileUpdateCaseState.PROPOSED.value,
        current_claim_id=current_claim.id if current_claim is not None else None,
        current_claim_version=(
            current_claim.version if current_claim is not None else None
        ),
        current_claim_state=current_claim.state if current_claim is not None else None,
        current_level=current_claim.level if current_claim is not None else None,
        current_proven_scope=(
            current_claim.proven_scope if current_claim is not None else None
        ),
        current_evidence_recency=(
            current_claim.evidence_recency if current_claim is not None else None
        ),
        current_confidence_in_claim=(
            current_claim.confidence_in_claim if current_claim is not None else None
        ),
        current_next_evidence_needed=(
            current_claim.next_evidence_needed if current_claim is not None else None
        ),
        proposed_claim_state=command.proposed_claim_state,
        proposed_level=command.proposed_level,
        proposed_proven_scope=command.proposed_proven_scope.strip(),
        proposed_evidence_recency=command.proposed_evidence_recency.strip(),
        proposed_confidence_in_claim=(
            command.proposed_confidence_in_claim.strip()
        ),
        proposed_next_evidence_needed=(
            command.proposed_next_evidence_needed.strip()
        ),
        rationale=command.rationale.strip(),
        created_by=command.created_by,
        reviewed_by=None,
        reviewed_at=None,
        applied_by=None,
        applied_at=None,
        creation_idempotency_key=idempotency_key,
        review_idempotency_key=None,
        apply_idempotency_key=None,
        created_at=now,
        updated_at=now,
    )
    db.add(update_case)
    await db.flush()

    relationship_by_pattern = {
        item.pattern_id: item.relationship for item in command.patterns
    }
    for pattern_id in requested_pattern_ids:
        snapshot = snapshot_by_id[pattern_id]
        pattern_ref = ProfileUpdatePattern(
            id=uuid4(),
            profile_update_case_id=update_case.id,
            pattern_id=snapshot.pattern_id,
            pattern_version=snapshot.pattern_version,
            relationship=relationship_by_pattern[pattern_id],
            pattern_status=snapshot.pattern_status,
            behaviour_code=snapshot.behaviour_code,
            pattern_scope=snapshot.scope,
            pattern_reviewed_at=snapshot.reviewed_at,
            created_at=now,
        )
        db.add(pattern_ref)
        await db.flush()

        for evidence in snapshot.evidence:
            db.add(
                ProfileUpdatePatternEvidence(
                    id=uuid4(),
                    profile_update_pattern_id=pattern_ref.id,
                    evidence_set_member_id=evidence.evidence_set_member_id,
                    evidence_case_id=evidence.evidence_case_id,
                    interpretation_id=evidence.interpretation_id,
                    interpretation_version=evidence.interpretation_version,
                    evidence_relationship=evidence.relationship,
                    signal=evidence.signal,
                    evidence_scope=evidence.scope,
                    confidence=evidence.confidence,
                    context_difficulty=evidence.context_difficulty,
                    prompt_contamination=evidence.prompt_contamination,
                    source_independence_group=evidence.source_independence_group,
                    accepted_at=evidence.accepted_at,
                    source_observation_id=evidence.source.source_observation_id,
                    source_context=evidence.source.source_context,
                    source_reference=evidence.source.source_reference,
                    observation_type=evidence.source.observation_type,
                    created_at=now,
                )
            )

    await db.commit()
    return update_case
