from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.flag_profile.contracts import CurrentFlagProfileSnapshotContract
from app.gate_assessment.domain import GateAssessmentState, gate_transition_allowed
from app.gate_assessment.models import (
    GateAssessment,
    GateProfileSnapshot,
    GateProfileSnapshotClaim,
    GateReview,
    GateSnapshotEvidenceRef,
    GateSnapshotPatternRef,
)


class CurrentFlagProfileReader(Protocol):
    async def load(
        self,
        *,
        organization_context_id: UUID,
        subject_person_id: UUID,
        track_code: str,
    ) -> CurrentFlagProfileSnapshotContract: ...


@dataclass(frozen=True)
class OpenGateReviewCommand:
    organization_context_id: UUID
    gate_assessment_id: UUID
    track_code: str
    opened_by: UUID
    expected_version: int
    idempotency_key: str
    trace_id: str


@dataclass(frozen=True)
class OpenGateReviewResult:
    gate_assessment: GateAssessment
    review: GateReview
    profile_snapshot: GateProfileSnapshot


def _require_open_review_command(command: OpenGateReviewCommand) -> tuple[str, str, str]:
    track_code = command.track_code.strip()
    idempotency_key = command.idempotency_key.strip()
    trace_id = command.trace_id.strip()

    if not track_code:
        raise AppError(
            "GATE_PROFILE_TRACK_REQUIRED",
            "Track code is required to snapshot the Current Flag Profile.",
            status_code=422,
        )
    if not idempotency_key:
        raise AppError(
            "GATE_IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency key is required.",
            status_code=422,
        )
    if not trace_id:
        raise AppError(
            "GATE_TRACE_ID_REQUIRED",
            "Trace id is required.",
            status_code=422,
        )
    return track_code, idempotency_key, trace_id


async def _existing_open_review(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    opened_by: UUID,
    idempotency_key: str,
) -> GateReview | None:
    return (
        await db.execute(
            select(GateReview).where(
                GateReview.organization_context_id == organization_context_id,
                GateReview.opened_by == opened_by,
                GateReview.open_idempotency_key == idempotency_key,
            )
        )
    ).scalar_one_or_none()


def _open_review_retry_matches(
    review: GateReview,
    snapshot: GateProfileSnapshot,
    *,
    command: OpenGateReviewCommand,
    track_code: str,
) -> bool:
    return (
        review.gate_assessment_id == command.gate_assessment_id
        and review.opened_by == command.opened_by
        and snapshot.gate_assessment_id == command.gate_assessment_id
        and snapshot.source_track_code == track_code
    )


async def _load_open_review_retry(
    db: AsyncSession,
    *,
    review: GateReview,
    command: OpenGateReviewCommand,
    track_code: str,
) -> OpenGateReviewResult:
    assessment = (
        await db.execute(
            select(GateAssessment).where(
                GateAssessment.id == review.gate_assessment_id,
                GateAssessment.organization_context_id
                == command.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    snapshot = (
        await db.execute(
            select(GateProfileSnapshot).where(
                GateProfileSnapshot.id == review.gate_profile_snapshot_id,
                GateProfileSnapshot.gate_assessment_id
                == review.gate_assessment_id,
                GateProfileSnapshot.organization_context_id
                == command.organization_context_id,
            )
        )
    ).scalar_one_or_none()

    if assessment is None or snapshot is None:
        raise AppError(
            "GATE_REVIEW_LINEAGE_INCOMPLETE",
            "Existing Gate Review is missing its assessment or pinned Profile Snapshot.",
            status_code=409,
        )
    if not _open_review_retry_matches(
        review,
        snapshot,
        command=command,
        track_code=track_code,
    ):
        raise AppError(
            "GATE_IDEMPOTENCY_KEY_REUSED",
            "Idempotency key was already used for a different Gate Review request.",
            status_code=409,
        )

    return OpenGateReviewResult(
        gate_assessment=assessment,
        review=review,
        profile_snapshot=snapshot,
    )


def _require_expected_version(
    *,
    current_version: int,
    expected_version: int,
) -> None:
    if current_version != expected_version:
        raise AppError(
            "GATE_VERSION_CONFLICT",
            "Gate Assessment changed. Refresh and retry.",
            status_code=409,
            details={
                "expected_version": expected_version,
                "current_version": current_version,
            },
        )


def _require_profile_scope(
    snapshot: CurrentFlagProfileSnapshotContract,
    *,
    organization_context_id: UUID,
    subject_person_id: UUID,
    track_code: str,
) -> None:
    if (
        snapshot.organization_context_id != organization_context_id
        or snapshot.subject_person_id != subject_person_id
        or snapshot.track_code != track_code
    ):
        raise AppError(
            "GATE_PROFILE_SNAPSHOT_SCOPE_MISMATCH",
            "Current Flag Profile snapshot does not match the Gate Assessment scope.",
            status_code=409,
        )


async def _next_snapshot_version(
    db: AsyncSession,
    *,
    gate_assessment_id: UUID,
) -> int:
    current = (
        await db.execute(
            select(func.max(GateProfileSnapshot.snapshot_version)).where(
                GateProfileSnapshot.gate_assessment_id == gate_assessment_id
            )
        )
    ).scalar_one()
    return int(current or 0) + 1


def _persist_profile_snapshot(
    db: AsyncSession,
    *,
    gate_assessment: GateAssessment,
    source: CurrentFlagProfileSnapshotContract,
    snapshot_version: int,
    captured_at: datetime,
) -> GateProfileSnapshot:
    snapshot = GateProfileSnapshot(
        id=uuid4(),
        gate_assessment_id=gate_assessment.id,
        snapshot_version=snapshot_version,
        organization_context_id=gate_assessment.organization_context_id,
        subject_person_id=gate_assessment.subject_person_id,
        source_flag_profile_id=source.flag_profile_id,
        source_flag_profile_version=source.flag_profile_version,
        source_track_code=source.track_code,
        source_profile_updated_at=source.profile_updated_at,
        captured_at=captured_at,
    )
    db.add(snapshot)

    for claim in source.claims:
        claim_row = GateProfileSnapshotClaim(
            id=uuid4(),
            gate_profile_snapshot_id=snapshot.id,
            source_claim_id=claim.claim_id,
            source_claim_version=claim.claim_version,
            capability_id=claim.capability_id,
            state=claim.state,
            level=claim.level,
            proven_scope=claim.proven_scope,
            evidence_recency=claim.evidence_recency,
            confidence_in_claim=claim.confidence_in_claim,
            reviewed_at=claim.reviewed_at,
            next_evidence_needed=claim.next_evidence_needed,
            source_profile_update_case_id=claim.source_profile_update_case_id,
        )
        db.add(claim_row)

        for pattern in claim.patterns:
            pattern_row = GateSnapshotPatternRef(
                id=uuid4(),
                gate_profile_snapshot_claim_id=claim_row.id,
                source_pattern_id=pattern.pattern_id,
                source_pattern_version=pattern.pattern_version,
                relationship=pattern.relationship,
                pattern_status=pattern.pattern_status,
                behaviour_code=pattern.behaviour_code,
                scope=pattern.scope,
                reviewed_at=pattern.reviewed_at,
            )
            db.add(pattern_row)

            for evidence in pattern.evidence:
                db.add(
                    GateSnapshotEvidenceRef(
                        id=uuid4(),
                        gate_snapshot_pattern_ref_id=pattern_row.id,
                        evidence_set_member_id=evidence.evidence_set_member_id,
                        evidence_case_id=evidence.evidence_case_id,
                        interpretation_id=evidence.interpretation_id,
                        interpretation_version=evidence.interpretation_version,
                        evidence_relationship=evidence.evidence_relationship,
                        signal=evidence.signal,
                        scope=evidence.scope,
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
                )

    return snapshot


async def open_gate_review(
    db: AsyncSession,
    *,
    reader: CurrentFlagProfileReader,
    command: OpenGateReviewCommand,
) -> OpenGateReviewResult:
    track_code, idempotency_key, trace_id = _require_open_review_command(command)

    existing = await _existing_open_review(
        db,
        organization_context_id=command.organization_context_id,
        opened_by=command.opened_by,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        return await _load_open_review_retry(
            db,
            review=existing,
            command=command,
            track_code=track_code,
        )

    assessment = (
        await db.execute(
            select(GateAssessment)
            .where(
                GateAssessment.id == command.gate_assessment_id,
                GateAssessment.organization_context_id
                == command.organization_context_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if assessment is None:
        raise AppError(
            "GATE_ASSESSMENT_NOT_FOUND",
            "Gate Assessment not found.",
            status_code=404,
        )

    _require_expected_version(
        current_version=assessment.version,
        expected_version=command.expected_version,
    )
    if not gate_transition_allowed(
        assessment.state,
        GateAssessmentState.REVIEW_REQUIRED.value,
    ):
        raise AppError(
            "GATE_STATE_CONFLICT",
            "Gate Assessment cannot open Human Review from its current state.",
            status_code=409,
            details={
                "current_state": assessment.state,
                "target_state": GateAssessmentState.REVIEW_REQUIRED.value,
            },
        )

    current_profile = await reader.load(
        organization_context_id=command.organization_context_id,
        subject_person_id=assessment.subject_person_id,
        track_code=track_code,
    )
    _require_profile_scope(
        current_profile,
        organization_context_id=command.organization_context_id,
        subject_person_id=assessment.subject_person_id,
        track_code=track_code,
    )

    snapshot_version = await _next_snapshot_version(
        db,
        gate_assessment_id=assessment.id,
    )
    now = datetime.now(UTC)
    profile_snapshot = _persist_profile_snapshot(
        db,
        gate_assessment=assessment,
        source=current_profile,
        snapshot_version=snapshot_version,
        captured_at=now,
    )

    assessment.state = GateAssessmentState.REVIEW_REQUIRED.value
    assessment.version += 1
    assessment.updated_at = now

    review = GateReview(
        id=uuid4(),
        gate_assessment_id=assessment.id,
        gate_profile_snapshot_id=profile_snapshot.id,
        gate_definition_version_id=assessment.gate_definition_version_id,
        organization_context_id=assessment.organization_context_id,
        subject_person_id=assessment.subject_person_id,
        gate_assessment_version=assessment.version,
        opened_by=command.opened_by,
        opened_at=now,
        open_idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    db.add(review)

    await db.commit()
    return OpenGateReviewResult(
        gate_assessment=assessment,
        review=review,
        profile_snapshot=profile_snapshot,
    )
