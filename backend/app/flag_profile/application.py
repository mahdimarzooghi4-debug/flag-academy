from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.flag_profile.domain import (
    ProfileUpdateCaseState,
    capability_level_valid,
    claim_pattern_relationship_valid,
    profile_claim_state_valid,
    profile_update_transition_allowed,
)
from app.flag_profile.models import (
    CapabilityClaim,
    CapabilityClaimPattern,
    FlagProfile,
    ProfileUpdateCase,
    ProfileUpdatePattern,
    ProfileUpdatePatternEvidence,
)
from app.patterns.contracts import ReviewedPatternSnapshotContract
from app.platform.events import EventEnvelope, new_event, record_event


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
        reviewed_claim_state=None,
        reviewed_level=None,
        reviewed_proven_scope=None,
        reviewed_evidence_recency=None,
        reviewed_confidence_in_claim=None,
        reviewed_next_evidence_needed=None,
        review_rationale=None,
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



@dataclass(frozen=True)
class RequestProfileUpdateReviewCommand:
    organization_context_id: UUID
    profile_update_case_id: UUID
    expected_version: int
    trace_id: str


def _require_profile_update_expected_version(
    *,
    current_version: int,
    expected_version: int,
) -> None:
    if expected_version != current_version:
        raise AppError(
            "VERSION_CONFLICT",
            "Profile update case changed. Refresh and retry.",
            status_code=409,
            details={
                "expected_version": expected_version,
                "current_version": current_version,
            },
        )


async def request_profile_update_review(
    db: AsyncSession,
    *,
    command: RequestProfileUpdateReviewCommand,
) -> ProfileUpdateCase:
    update_case = (
        await db.execute(
            select(ProfileUpdateCase)
            .where(
                ProfileUpdateCase.id == command.profile_update_case_id,
                ProfileUpdateCase.organization_context_id
                == command.organization_context_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if update_case is None:
        raise AppError(
            "PROFILE_UPDATE_CASE_NOT_FOUND",
            "Profile update case not found.",
            status_code=404,
        )

    _require_profile_update_expected_version(
        current_version=update_case.version,
        expected_version=command.expected_version,
    )

    if not profile_update_transition_allowed(
        update_case.state,
        ProfileUpdateCaseState.REVIEW_REQUIRED.value,
    ):
        raise AppError(
            "PROFILE_UPDATE_STATE_CONFLICT",
            "Profile update case cannot enter Human Review from its current state.",
            status_code=409,
            details={
                "current_state": update_case.state,
                "target_state": ProfileUpdateCaseState.REVIEW_REQUIRED.value,
            },
        )

    update_case.state = ProfileUpdateCaseState.REVIEW_REQUIRED.value
    update_case.version += 1
    update_case.updated_at = datetime.now(UTC)
    await db.commit()
    return update_case


@dataclass(frozen=True)
class ProfileUpdateEvidenceLineage:
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
class ProfileUpdatePatternLineage:
    pattern_id: UUID
    pattern_version: int
    relationship: str
    pattern_status: str
    behaviour_code: str
    scope: str
    reviewed_at: datetime
    evidence: tuple[ProfileUpdateEvidenceLineage, ...]


@dataclass(frozen=True)
class ProfileUpdateCasePreReview:
    id: UUID
    version: int
    organization_context_id: UUID
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
    patterns: tuple[ProfileUpdatePatternLineage, ...]


async def load_profile_update_case_pre_review(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    profile_update_case_id: UUID,
) -> ProfileUpdateCasePreReview:
    update_case = (
        await db.execute(
            select(ProfileUpdateCase).where(
                ProfileUpdateCase.id == profile_update_case_id,
                ProfileUpdateCase.organization_context_id
                == organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if update_case is None:
        raise AppError(
            "PROFILE_UPDATE_CASE_NOT_FOUND",
            "Profile update case not found.",
            status_code=404,
        )
    if update_case.state != ProfileUpdateCaseState.REVIEW_REQUIRED.value:
        raise AppError(
            "PROFILE_UPDATE_NOT_REVIEWABLE",
            "Profile update case must be in REVIEW_REQUIRED before Human Review.",
            status_code=409,
            details={"current_state": update_case.state},
        )

    pattern_rows = (
        await db.execute(
            select(ProfileUpdatePattern)
            .where(
                ProfileUpdatePattern.profile_update_case_id == update_case.id,
            )
            .order_by(
                ProfileUpdatePattern.pattern_reviewed_at,
                ProfileUpdatePattern.pattern_id,
            )
        )
    ).scalars().all()
    if not pattern_rows:
        raise AppError(
            "PROFILE_UPDATE_LINEAGE_INCOMPLETE",
            "Profile update case has no Reviewed Pattern lineage.",
            status_code=409,
        )

    patterns: list[ProfileUpdatePatternLineage] = []
    for pattern in pattern_rows:
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
            raise AppError(
                "PROFILE_UPDATE_LINEAGE_INCOMPLETE",
                "Profile update Pattern has no Evidence lineage.",
                status_code=409,
                details={"pattern_id": str(pattern.pattern_id)},
            )

        patterns.append(
            ProfileUpdatePatternLineage(
                pattern_id=pattern.pattern_id,
                pattern_version=pattern.pattern_version,
                relationship=pattern.relationship,
                pattern_status=pattern.pattern_status,
                behaviour_code=pattern.behaviour_code,
                scope=pattern.pattern_scope,
                reviewed_at=pattern.pattern_reviewed_at,
                evidence=tuple(
                    ProfileUpdateEvidenceLineage(
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

    return ProfileUpdateCasePreReview(
        id=update_case.id,
        version=update_case.version,
        organization_context_id=update_case.organization_context_id,
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
        patterns=tuple(patterns),
    )



@dataclass(frozen=True)
class ApproveProfileUpdateCaseCommand:
    organization_context_id: UUID
    profile_update_case_id: UUID
    reviewer_id: UUID
    reviewed_claim_state: str
    reviewed_level: str
    reviewed_proven_scope: str
    reviewed_evidence_recency: str
    reviewed_confidence_in_claim: str
    reviewed_next_evidence_needed: str
    rationale: str
    expected_version: int
    idempotency_key: str
    trace_id: str


def _require_profile_update_approval_contract(
    command: ApproveProfileUpdateCaseCommand,
) -> None:
    if not profile_claim_state_valid(command.reviewed_claim_state):
        raise AppError(
            "PROFILE_CLAIM_STATE_INVALID",
            "Reviewed Capability Claim state is invalid.",
            status_code=422,
        )
    if not capability_level_valid(command.reviewed_level):
        raise AppError(
            "PROFILE_CAPABILITY_LEVEL_INVALID",
            "Reviewed Capability level is invalid.",
            status_code=422,
        )

    required_text = (
        ("reviewed_proven_scope", command.reviewed_proven_scope),
        ("reviewed_evidence_recency", command.reviewed_evidence_recency),
        ("reviewed_confidence_in_claim", command.reviewed_confidence_in_claim),
        (
            "reviewed_next_evidence_needed",
            command.reviewed_next_evidence_needed,
        ),
        ("rationale", command.rationale),
    )
    missing = [name for name, value in required_text if not value.strip()]
    if missing:
        raise AppError(
            "PROFILE_UPDATE_REVIEW_INVALID",
            "Profile update Human Review has required fields missing.",
            status_code=422,
            details={"fields": missing},
        )


def _approval_retry_matches(
    update_case: ProfileUpdateCase,
    *,
    command: ApproveProfileUpdateCaseCommand,
    idempotency_key: str,
) -> bool:
    return (
        update_case.state == ProfileUpdateCaseState.APPROVED.value
        and update_case.review_idempotency_key == idempotency_key
        and update_case.reviewed_by == command.reviewer_id
        and update_case.reviewed_claim_state == command.reviewed_claim_state
        and update_case.reviewed_level == command.reviewed_level
        and update_case.reviewed_proven_scope
        == command.reviewed_proven_scope.strip()
        and update_case.reviewed_evidence_recency
        == command.reviewed_evidence_recency.strip()
        and update_case.reviewed_confidence_in_claim
        == command.reviewed_confidence_in_claim.strip()
        and update_case.reviewed_next_evidence_needed
        == command.reviewed_next_evidence_needed.strip()
        and update_case.review_rationale == command.rationale.strip()
    )


async def approve_profile_update_case(
    db: AsyncSession,
    *,
    command: ApproveProfileUpdateCaseCommand,
) -> ProfileUpdateCase:
    idempotency_key = command.idempotency_key.strip()
    if not idempotency_key:
        raise AppError(
            "PROFILE_IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency key is required.",
            status_code=422,
        )

    update_case = (
        await db.execute(
            select(ProfileUpdateCase)
            .where(
                ProfileUpdateCase.id == command.profile_update_case_id,
                ProfileUpdateCase.organization_context_id
                == command.organization_context_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if update_case is None:
        raise AppError(
            "PROFILE_UPDATE_CASE_NOT_FOUND",
            "Profile update case not found.",
            status_code=404,
        )

    if update_case.review_idempotency_key is not None:
        if _approval_retry_matches(
            update_case,
            command=command,
            idempotency_key=idempotency_key,
        ):
            return update_case
        if update_case.review_idempotency_key == idempotency_key:
            raise AppError(
                "PROFILE_IDEMPOTENCY_KEY_REUSED",
                "Idempotency key was already used for a different Profile review.",
                status_code=409,
            )

    _require_profile_update_expected_version(
        current_version=update_case.version,
        expected_version=command.expected_version,
    )
    if not profile_update_transition_allowed(
        update_case.state,
        ProfileUpdateCaseState.APPROVED.value,
    ):
        raise AppError(
            "PROFILE_UPDATE_STATE_CONFLICT",
            "Profile update case cannot be approved from its current state.",
            status_code=409,
            details={
                "current_state": update_case.state,
                "target_state": ProfileUpdateCaseState.APPROVED.value,
            },
        )

    _require_profile_update_approval_contract(command)

    # Approval is forbidden unless the complete snapshotted lineage is reviewable.
    await load_profile_update_case_pre_review(
        db,
        organization_context_id=command.organization_context_id,
        profile_update_case_id=update_case.id,
    )

    now = datetime.now(UTC)
    update_case.reviewed_claim_state = command.reviewed_claim_state
    update_case.reviewed_level = command.reviewed_level
    update_case.reviewed_proven_scope = command.reviewed_proven_scope.strip()
    update_case.reviewed_evidence_recency = (
        command.reviewed_evidence_recency.strip()
    )
    update_case.reviewed_confidence_in_claim = (
        command.reviewed_confidence_in_claim.strip()
    )
    update_case.reviewed_next_evidence_needed = (
        command.reviewed_next_evidence_needed.strip()
    )
    update_case.review_rationale = command.rationale.strip()
    update_case.reviewed_by = command.reviewer_id
    update_case.reviewed_at = now
    update_case.review_idempotency_key = idempotency_key
    update_case.state = ProfileUpdateCaseState.APPROVED.value
    update_case.version += 1
    update_case.updated_at = now

    await db.commit()
    return update_case



@dataclass(frozen=True)
class ApplyProfileUpdateCaseCommand:
    organization_context_id: UUID
    profile_update_case_id: UUID
    applied_by: UUID
    expected_version: int
    idempotency_key: str
    trace_id: str


def _claim_snapshot_matches_current(
    update_case: ProfileUpdateCase,
    current_claim: CapabilityClaim | None,
) -> bool:
    if update_case.current_claim_id is None:
        return current_claim is None
    return (
        current_claim is not None
        and current_claim.id == update_case.current_claim_id
        and current_claim.version == update_case.current_claim_version
        and current_claim.state == update_case.current_claim_state
        and current_claim.level == update_case.current_level
        and current_claim.proven_scope == update_case.current_proven_scope
        and current_claim.evidence_recency
        == update_case.current_evidence_recency
        and current_claim.confidence_in_claim
        == update_case.current_confidence_in_claim
        and current_claim.next_evidence_needed
        == update_case.current_next_evidence_needed
    )


def _new_profile_claim_changed_event(
    *,
    organization_context_id: UUID,
    subject_person_id: UUID,
    profile_update_case_id: UUID,
    claim_id: UUID,
    claim_version: int,
    capability_id: UUID,
    track_code: str,
    old_claim: dict | None,
    new_claim: dict,
    pattern_refs: list[dict],
    applied_by: UUID,
    trace_id: str,
) -> EventEnvelope:
    return new_event(
        event_type="profile.claim_changed.v1",
        aggregate_type="CapabilityClaim",
        aggregate_id=claim_id,
        aggregate_version=claim_version,
        actor={"type": "PERSON", "id": str(applied_by)},
        organization_context_id=organization_context_id,
        data_classification="CONFIDENTIAL",
        payload={
            "profile_update_case_id": str(profile_update_case_id),
            "subject_person_id": str(subject_person_id),
            "capability_id": str(capability_id),
            "track_code": track_code,
            "old_claim": old_claim,
            "new_claim": new_claim,
            "pattern_refs": pattern_refs,
        },
        trace_id=trace_id,
    )


def _applied_retry_matches(
    update_case: ProfileUpdateCase,
    *,
    command: ApplyProfileUpdateCaseCommand,
    idempotency_key: str,
) -> bool:
    return (
        update_case.state == ProfileUpdateCaseState.APPLIED.value
        and update_case.apply_idempotency_key == idempotency_key
        and update_case.applied_by == command.applied_by
    )


def _reviewed_values_complete(update_case: ProfileUpdateCase) -> bool:
    return (
        update_case.reviewed_claim_state is not None
        and update_case.reviewed_level is not None
        and update_case.reviewed_proven_scope is not None
        and update_case.reviewed_evidence_recency is not None
        and update_case.reviewed_confidence_in_claim is not None
        and update_case.reviewed_next_evidence_needed is not None
        and update_case.reviewed_by is not None
        and update_case.reviewed_at is not None
        and update_case.review_rationale is not None
    )


async def apply_profile_update_case(
    db: AsyncSession,
    *,
    command: ApplyProfileUpdateCaseCommand,
) -> CapabilityClaim:
    idempotency_key = command.idempotency_key.strip()
    if not idempotency_key:
        raise AppError(
            "PROFILE_IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency key is required.",
            status_code=422,
        )

    update_case = (
        await db.execute(
            select(ProfileUpdateCase)
            .where(
                ProfileUpdateCase.id == command.profile_update_case_id,
                ProfileUpdateCase.organization_context_id
                == command.organization_context_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if update_case is None:
        raise AppError(
            "PROFILE_UPDATE_CASE_NOT_FOUND",
            "Profile update case not found.",
            status_code=404,
        )

    if update_case.apply_idempotency_key is not None:
        if _applied_retry_matches(
            update_case,
            command=command,
            idempotency_key=idempotency_key,
        ):
            applied_claim = (
                await db.execute(
                    select(CapabilityClaim).where(
                        CapabilityClaim.flag_profile_id
                        == update_case.flag_profile_id,
                        CapabilityClaim.capability_id
                        == update_case.capability_id,
                        CapabilityClaim.source_profile_update_case_id
                        == update_case.id,
                    )
                )
            ).scalar_one_or_none()
            if applied_claim is None:
                raise AppError(
                    "PROFILE_APPLIED_CLAIM_NOT_FOUND",
                    "Applied Capability Claim could not be found.",
                    status_code=409,
                )
            return applied_claim
        if update_case.apply_idempotency_key == idempotency_key:
            raise AppError(
                "PROFILE_IDEMPOTENCY_KEY_REUSED",
                "Idempotency key was already used for a different Profile apply command.",
                status_code=409,
            )

    _require_profile_update_expected_version(
        current_version=update_case.version,
        expected_version=command.expected_version,
    )
    if not profile_update_transition_allowed(
        update_case.state,
        ProfileUpdateCaseState.APPLIED.value,
    ):
        raise AppError(
            "PROFILE_UPDATE_STATE_CONFLICT",
            "Profile update case cannot be applied from its current state.",
            status_code=409,
            details={
                "current_state": update_case.state,
                "target_state": ProfileUpdateCaseState.APPLIED.value,
            },
        )
    if not _reviewed_values_complete(update_case):
        raise AppError(
            "PROFILE_UPDATE_REVIEW_INCOMPLETE",
            "Approved Profile update is missing Human Review values.",
            status_code=409,
        )

    profile = (
        await db.execute(
            select(FlagProfile)
            .where(
                FlagProfile.id == update_case.flag_profile_id,
                FlagProfile.organization_context_id
                == command.organization_context_id,
                FlagProfile.subject_person_id == update_case.subject_person_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if profile is None:
        raise AppError(
            "FLAG_PROFILE_NOT_FOUND",
            "Flag Profile not found.",
            status_code=404,
        )

    current_claim = (
        await db.execute(
            select(CapabilityClaim)
            .where(
                CapabilityClaim.flag_profile_id == profile.id,
                CapabilityClaim.capability_id == update_case.capability_id,
                CapabilityClaim.organization_context_id
                == command.organization_context_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if not _claim_snapshot_matches_current(update_case, current_claim):
        raise AppError(
            "PROFILE_CURRENT_CLAIM_CHANGED",
            "Current Capability Claim changed after this Profile update was proposed.",
            status_code=409,
        )

    pattern_rows = (
        await db.execute(
            select(ProfileUpdatePattern)
            .where(
                ProfileUpdatePattern.profile_update_case_id == update_case.id,
            )
            .order_by(ProfileUpdatePattern.pattern_id)
        )
    ).scalars().all()
    if not pattern_rows:
        raise AppError(
            "PROFILE_UPDATE_LINEAGE_INCOMPLETE",
            "Approved Profile update has no Reviewed Pattern lineage.",
            status_code=409,
        )

    old_claim = (
        None
        if current_claim is None
        else {
            "claim_id": str(current_claim.id),
            "version": current_claim.version,
            "state": current_claim.state,
            "level": current_claim.level,
            "proven_scope": current_claim.proven_scope,
            "evidence_recency": current_claim.evidence_recency,
            "confidence_in_claim": current_claim.confidence_in_claim,
            "next_evidence_needed": current_claim.next_evidence_needed,
        }
    )

    reviewed_claim_state = update_case.reviewed_claim_state
    reviewed_level = update_case.reviewed_level
    reviewed_proven_scope = update_case.reviewed_proven_scope
    reviewed_evidence_recency = update_case.reviewed_evidence_recency
    reviewed_confidence_in_claim = update_case.reviewed_confidence_in_claim
    reviewed_next_evidence_needed = update_case.reviewed_next_evidence_needed
    reviewed_at = update_case.reviewed_at
    reviewed_by = update_case.reviewed_by
    if (
        reviewed_claim_state is None
        or reviewed_level is None
        or reviewed_proven_scope is None
        or reviewed_evidence_recency is None
        or reviewed_confidence_in_claim is None
        or reviewed_next_evidence_needed is None
        or reviewed_at is None
        or reviewed_by is None
    ):
        raise AppError(
            "PROFILE_UPDATE_REVIEW_INCOMPLETE",
            "Approved Profile update is missing Human Review values.",
            status_code=409,
        )

    now = datetime.now(UTC)
    if current_claim is None:
        claim = CapabilityClaim(
            id=uuid4(),
            version=1,
            flag_profile_id=profile.id,
            organization_context_id=update_case.organization_context_id,
            subject_person_id=update_case.subject_person_id,
            track_code=update_case.track_code,
            capability_id=update_case.capability_id,
            state=reviewed_claim_state,
            level=reviewed_level,
            proven_scope=reviewed_proven_scope,
            evidence_recency=reviewed_evidence_recency,
            confidence_in_claim=reviewed_confidence_in_claim,
            reviewed_at=reviewed_at,
            reviewed_by=reviewed_by,
            next_evidence_needed=reviewed_next_evidence_needed,
            source_profile_update_case_id=update_case.id,
            created_at=now,
            updated_at=now,
        )
        db.add(claim)
        await db.flush()
    else:
        claim = current_claim
        claim.version += 1
        claim.state = reviewed_claim_state
        claim.level = reviewed_level
        claim.proven_scope = reviewed_proven_scope
        claim.evidence_recency = reviewed_evidence_recency
        claim.confidence_in_claim = reviewed_confidence_in_claim
        claim.reviewed_at = reviewed_at
        claim.reviewed_by = reviewed_by
        claim.next_evidence_needed = reviewed_next_evidence_needed
        claim.source_profile_update_case_id = update_case.id
        claim.updated_at = now

        await db.execute(
            delete(CapabilityClaimPattern).where(
                CapabilityClaimPattern.capability_claim_id == claim.id
            )
        )

    pattern_refs = [
        {
            "pattern_id": str(pattern.pattern_id),
            "pattern_version": pattern.pattern_version,
            "relationship": pattern.relationship,
        }
        for pattern in pattern_rows
    ]
    for pattern in pattern_rows:
        db.add(
            CapabilityClaimPattern(
                id=uuid4(),
                capability_claim_id=claim.id,
                pattern_id=pattern.pattern_id,
                pattern_version=pattern.pattern_version,
                relationship=pattern.relationship,
                created_at=now,
            )
        )

    profile.version += 1
    profile.updated_at = now
    update_case.state = ProfileUpdateCaseState.APPLIED.value
    update_case.version += 1
    update_case.applied_by = command.applied_by
    update_case.applied_at = now
    update_case.apply_idempotency_key = idempotency_key
    update_case.updated_at = now

    new_claim = {
        "claim_id": str(claim.id),
        "version": claim.version,
        "state": claim.state,
        "level": claim.level,
        "proven_scope": claim.proven_scope,
        "evidence_recency": claim.evidence_recency,
        "confidence_in_claim": claim.confidence_in_claim,
        "next_evidence_needed": claim.next_evidence_needed,
    }
    record_event(
        db,
        _new_profile_claim_changed_event(
            organization_context_id=update_case.organization_context_id,
            subject_person_id=update_case.subject_person_id,
            profile_update_case_id=update_case.id,
            claim_id=claim.id,
            claim_version=claim.version,
            capability_id=update_case.capability_id,
            track_code=update_case.track_code,
            old_claim=old_claim,
            new_claim=new_claim,
            pattern_refs=pattern_refs,
            applied_by=command.applied_by,
            trace_id=command.trace_id,
        ),
    )

    await db.commit()
    return claim
