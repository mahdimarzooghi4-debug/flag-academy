from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.gate_assessment.application import (
    CurrentFlagProfileReader,
    _next_snapshot_version,
    _persist_profile_snapshot,
    _require_expected_version,
    _require_profile_scope,
)
from app.gate_assessment.domain import GateAssessmentState, gate_transition_allowed
from app.gate_assessment.models import (
    GateAssessment,
    GateProfileSnapshot,
    GateProfileSnapshotClaim,
    GateReassessment,
    GateReassessmentDecision,
    GateRemediation,
    GateReviewDecision,
    GateSnapshotEvidenceRef,
    GateSnapshotPatternRef,
)
from app.platform.events import EventEnvelope, new_event, record_event


@dataclass(frozen=True)
class StartGateRemediationCommand:
    organization_context_id: UUID
    gate_assessment_id: UUID
    started_by: UUID
    expected_version: int
    idempotency_key: str
    trace_id: str


@dataclass(frozen=True)
class StartGateRemediationResult:
    gate_assessment: GateAssessment
    remediation: GateRemediation


@dataclass(frozen=True)
class OpenGateReassessmentCommand:
    organization_context_id: UUID
    gate_assessment_id: UUID
    gate_remediation_id: UUID
    track_code: str
    opened_by: UUID
    expected_version: int
    idempotency_key: str
    trace_id: str


@dataclass(frozen=True)
class OpenGateReassessmentResult:
    gate_assessment: GateAssessment
    remediation: GateRemediation
    reassessment: GateReassessment
    profile_snapshot: GateProfileSnapshot


@dataclass(frozen=True)
class CompleteGateReassessmentCommand:
    organization_context_id: UUID
    gate_reassessment_id: UUID
    reviewer_id: UUID
    decision_state: str
    rationale: str
    expected_version: int
    expected_gate_definition_version_id: UUID
    expected_profile_snapshot_id: UUID
    expected_profile_snapshot_version: int
    idempotency_key: str
    trace_id: str


@dataclass(frozen=True)
class CompleteGateReassessmentResult:
    gate_assessment: GateAssessment
    reassessment: GateReassessment
    decision: GateReassessmentDecision
    profile_snapshot: GateProfileSnapshot


def _require_key_and_trace(
    *,
    idempotency_key: str,
    trace_id: str,
) -> tuple[str, str]:
    normalized_key = idempotency_key.strip()
    normalized_trace = trace_id.strip()
    if not normalized_key:
        raise AppError(
            "GATE_IDEMPOTENCY_KEY_REQUIRED",
            "Idempotency key is required.",
            status_code=422,
        )
    if not normalized_trace:
        raise AppError(
            "GATE_TRACE_ID_REQUIRED",
            "Trace id is required.",
            status_code=422,
        )
    return normalized_key, normalized_trace


async def _failure_is_human_decision(
    db: AsyncSession,
    *,
    gate_assessment_id: UUID,
    resulting_assessment_version: int,
) -> bool:
    review_failure = (
        await db.execute(
            select(GateReviewDecision.id).where(
                GateReviewDecision.gate_assessment_id == gate_assessment_id,
                GateReviewDecision.resulting_assessment_version
                == resulting_assessment_version,
                GateReviewDecision.decision_state
                == GateAssessmentState.FAIL.value,
            )
        )
    ).scalar_one_or_none()
    if review_failure is not None:
        return True

    reassessment_failure = (
        await db.execute(
            select(GateReassessmentDecision.id).where(
                GateReassessmentDecision.gate_assessment_id
                == gate_assessment_id,
                GateReassessmentDecision.resulting_assessment_version
                == resulting_assessment_version,
                GateReassessmentDecision.decision_state
                == GateAssessmentState.FAIL.value,
            )
        )
    ).scalar_one_or_none()
    return reassessment_failure is not None


async def _remediation_by_key(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    started_by: UUID,
    idempotency_key: str,
) -> GateRemediation | None:
    return (
        await db.execute(
            select(GateRemediation).where(
                GateRemediation.organization_context_id
                == organization_context_id,
                GateRemediation.started_by == started_by,
                GateRemediation.start_idempotency_key == idempotency_key,
            )
        )
    ).scalar_one_or_none()


def _remediation_retry_matches(
    remediation: GateRemediation,
    *,
    command: StartGateRemediationCommand,
    idempotency_key: str,
) -> bool:
    return (
        remediation.gate_assessment_id == command.gate_assessment_id
        and remediation.started_by == command.started_by
        and remediation.failure_assessment_version == command.expected_version
        and remediation.start_idempotency_key == idempotency_key
    )


async def _load_remediation_retry(
    db: AsyncSession,
    *,
    remediation: GateRemediation,
    command: StartGateRemediationCommand,
    idempotency_key: str,
) -> StartGateRemediationResult:
    if not _remediation_retry_matches(
        remediation,
        command=command,
        idempotency_key=idempotency_key,
    ):
        raise AppError(
            "GATE_IDEMPOTENCY_KEY_REUSED",
            "Idempotency key was already used for a different remediation command.",
            status_code=409,
        )
    assessment = (
        await db.execute(
            select(GateAssessment).where(
                GateAssessment.id == remediation.gate_assessment_id,
                GateAssessment.organization_context_id
                == command.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if assessment is None:
        raise AppError(
            "GATE_REMEDIATION_LINEAGE_INCOMPLETE",
            "Gate remediation is missing its assessment.",
            status_code=409,
        )
    return StartGateRemediationResult(
        gate_assessment=assessment,
        remediation=remediation,
    )


async def start_gate_remediation(
    db: AsyncSession,
    *,
    command: StartGateRemediationCommand,
) -> StartGateRemediationResult:
    idempotency_key, trace_id = _require_key_and_trace(
        idempotency_key=command.idempotency_key,
        trace_id=command.trace_id,
    )
    existing = await _remediation_by_key(
        db,
        organization_context_id=command.organization_context_id,
        started_by=command.started_by,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        return await _load_remediation_retry(
            db,
            remediation=existing,
            command=command,
            idempotency_key=idempotency_key,
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

    raced = await _remediation_by_key(
        db,
        organization_context_id=command.organization_context_id,
        started_by=command.started_by,
        idempotency_key=idempotency_key,
    )
    if raced is not None:
        return await _load_remediation_retry(
            db,
            remediation=raced,
            command=command,
            idempotency_key=idempotency_key,
        )

    _require_expected_version(
        current_version=assessment.version,
        expected_version=command.expected_version,
    )
    if not gate_transition_allowed(
        assessment.state,
        GateAssessmentState.REMEDIATION.value,
    ):
        raise AppError(
            "GATE_STATE_CONFLICT",
            "Gate Assessment cannot start remediation from its current state.",
            status_code=409,
            details={
                "current_state": assessment.state,
                "target_state": GateAssessmentState.REMEDIATION.value,
            },
        )
    if not await _failure_is_human_decision(
        db,
        gate_assessment_id=assessment.id,
        resulting_assessment_version=assessment.version,
    ):
        raise AppError(
            "GATE_FAILURE_DECISION_NOT_FOUND",
            "FAIL state is not backed by an accountable Human decision.",
            status_code=409,
        )

    now = datetime.now(UTC)
    failure_version = assessment.version
    assessment.state = GateAssessmentState.REMEDIATION.value
    assessment.version += 1
    assessment.updated_at = now

    remediation = GateRemediation(
        id=uuid4(),
        gate_assessment_id=assessment.id,
        organization_context_id=assessment.organization_context_id,
        subject_person_id=assessment.subject_person_id,
        failure_assessment_version=failure_version,
        remediation_assessment_version=assessment.version,
        started_by=command.started_by,
        started_at=now,
        start_idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    db.add(remediation)
    await db.commit()
    return StartGateRemediationResult(
        gate_assessment=assessment,
        remediation=remediation,
    )


async def _reassessment_by_key(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    opened_by: UUID,
    idempotency_key: str,
) -> GateReassessment | None:
    return (
        await db.execute(
            select(GateReassessment).where(
                GateReassessment.organization_context_id
                == organization_context_id,
                GateReassessment.opened_by == opened_by,
                GateReassessment.open_idempotency_key == idempotency_key,
            )
        )
    ).scalar_one_or_none()


def _reassessment_retry_matches(
    reassessment: GateReassessment,
    snapshot: GateProfileSnapshot,
    *,
    command: OpenGateReassessmentCommand,
    track_code: str,
    idempotency_key: str,
) -> bool:
    return (
        reassessment.gate_assessment_id == command.gate_assessment_id
        and reassessment.gate_remediation_id == command.gate_remediation_id
        and reassessment.opened_by == command.opened_by
        and reassessment.prior_assessment_version == command.expected_version
        and reassessment.open_idempotency_key == idempotency_key
        and snapshot.id == reassessment.gate_profile_snapshot_id
        and snapshot.source_track_code == track_code
    )


async def _load_reassessment_retry(
    db: AsyncSession,
    *,
    reassessment: GateReassessment,
    command: OpenGateReassessmentCommand,
    track_code: str,
    idempotency_key: str,
) -> OpenGateReassessmentResult:
    assessment = (
        await db.execute(
            select(GateAssessment).where(
                GateAssessment.id == reassessment.gate_assessment_id,
                GateAssessment.organization_context_id
                == command.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    remediation = (
        await db.execute(
            select(GateRemediation).where(
                GateRemediation.id == reassessment.gate_remediation_id,
                GateRemediation.organization_context_id
                == command.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    snapshot = (
        await db.execute(
            select(GateProfileSnapshot).where(
                GateProfileSnapshot.id == reassessment.gate_profile_snapshot_id,
                GateProfileSnapshot.organization_context_id
                == command.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if assessment is None or remediation is None or snapshot is None:
        raise AppError(
            "GATE_REASSESSMENT_LINEAGE_INCOMPLETE",
            "Gate reassessment is missing assessment, remediation, or snapshot lineage.",
            status_code=409,
        )
    if not _reassessment_retry_matches(
        reassessment,
        snapshot,
        command=command,
        track_code=track_code,
        idempotency_key=idempotency_key,
    ):
        raise AppError(
            "GATE_IDEMPOTENCY_KEY_REUSED",
            "Idempotency key was already used for a different reassessment command.",
            status_code=409,
        )
    return OpenGateReassessmentResult(
        gate_assessment=assessment,
        remediation=remediation,
        reassessment=reassessment,
        profile_snapshot=snapshot,
    )


async def open_gate_reassessment(
    db: AsyncSession,
    *,
    reader: CurrentFlagProfileReader,
    command: OpenGateReassessmentCommand,
) -> OpenGateReassessmentResult:
    track_code = command.track_code.strip()
    if not track_code:
        raise AppError(
            "GATE_PROFILE_TRACK_REQUIRED",
            "Track code is required to snapshot the Current Flag Profile.",
            status_code=422,
        )
    idempotency_key, trace_id = _require_key_and_trace(
        idempotency_key=command.idempotency_key,
        trace_id=command.trace_id,
    )

    existing = await _reassessment_by_key(
        db,
        organization_context_id=command.organization_context_id,
        opened_by=command.opened_by,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        return await _load_reassessment_retry(
            db,
            reassessment=existing,
            command=command,
            track_code=track_code,
            idempotency_key=idempotency_key,
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

    raced = await _reassessment_by_key(
        db,
        organization_context_id=command.organization_context_id,
        opened_by=command.opened_by,
        idempotency_key=idempotency_key,
    )
    if raced is not None:
        return await _load_reassessment_retry(
            db,
            reassessment=raced,
            command=command,
            track_code=track_code,
            idempotency_key=idempotency_key,
        )

    _require_expected_version(
        current_version=assessment.version,
        expected_version=command.expected_version,
    )
    if not gate_transition_allowed(
        assessment.state,
        GateAssessmentState.REASSESSMENT.value,
    ):
        raise AppError(
            "GATE_STATE_CONFLICT",
            "Gate Assessment cannot enter reassessment from its current state.",
            status_code=409,
            details={
                "current_state": assessment.state,
                "target_state": GateAssessmentState.REASSESSMENT.value,
            },
        )

    remediation = (
        await db.execute(
            select(GateRemediation).where(
                GateRemediation.id == command.gate_remediation_id,
                GateRemediation.gate_assessment_id == assessment.id,
                GateRemediation.organization_context_id
                == command.organization_context_id,
                GateRemediation.subject_person_id == assessment.subject_person_id,
                GateRemediation.remediation_assessment_version
                == assessment.version,
            )
        )
    ).scalar_one_or_none()
    if remediation is None:
        raise AppError(
            "GATE_REMEDIATION_NOT_CURRENT",
            "Reassessment must use the current remediation cycle.",
            status_code=409,
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
    snapshot = _persist_profile_snapshot(
        db,
        gate_assessment=assessment,
        source=current_profile,
        snapshot_version=snapshot_version,
        captured_at=now,
    )

    prior_version = assessment.version
    assessment.state = GateAssessmentState.REASSESSMENT.value
    assessment.version += 1
    assessment.updated_at = now

    reassessment = GateReassessment(
        id=uuid4(),
        gate_assessment_id=assessment.id,
        gate_remediation_id=remediation.id,
        gate_profile_snapshot_id=snapshot.id,
        gate_definition_version_id=assessment.gate_definition_version_id,
        organization_context_id=assessment.organization_context_id,
        subject_person_id=assessment.subject_person_id,
        prior_assessment_version=prior_version,
        reassessment_assessment_version=assessment.version,
        opened_by=command.opened_by,
        opened_at=now,
        open_idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    db.add(reassessment)
    await db.commit()
    return OpenGateReassessmentResult(
        gate_assessment=assessment,
        remediation=remediation,
        reassessment=reassessment,
        profile_snapshot=snapshot,
    )


async def _require_snapshot_lineage_complete(
    db: AsyncSession,
    *,
    profile_snapshot_id: UUID,
) -> None:
    claim_rows = (
        await db.execute(
            select(GateProfileSnapshotClaim.id).where(
                GateProfileSnapshotClaim.gate_profile_snapshot_id
                == profile_snapshot_id
            )
        )
    ).scalars().all()

    for claim_id in claim_rows:
        pattern_rows = (
            await db.execute(
                select(GateSnapshotPatternRef.id).where(
                    GateSnapshotPatternRef.gate_profile_snapshot_claim_id
                    == claim_id
                )
            )
        ).scalars().all()
        if not pattern_rows:
            raise AppError(
                "GATE_REASSESSMENT_LINEAGE_INCOMPLETE",
                "Pinned reassessment Claim has no Pattern lineage.",
                status_code=409,
            )
        for pattern_id in pattern_rows:
            evidence_exists = (
                await db.execute(
                    select(GateSnapshotEvidenceRef.id)
                    .where(
                        GateSnapshotEvidenceRef.gate_snapshot_pattern_ref_id
                        == pattern_id
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()
            if evidence_exists is None:
                raise AppError(
                    "GATE_REASSESSMENT_LINEAGE_INCOMPLETE",
                    "Pinned reassessment Pattern has no Evidence lineage.",
                    status_code=409,
                )


async def _reassessment_decision_by_key(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    reviewer_id: UUID,
    idempotency_key: str,
) -> GateReassessmentDecision | None:
    return (
        await db.execute(
            select(GateReassessmentDecision).where(
                GateReassessmentDecision.organization_context_id
                == organization_context_id,
                GateReassessmentDecision.reviewer_id == reviewer_id,
                GateReassessmentDecision.decision_idempotency_key
                == idempotency_key,
            )
        )
    ).scalar_one_or_none()


async def _reassessment_decision_for_cycle(
    db: AsyncSession,
    *,
    gate_reassessment_id: UUID,
) -> GateReassessmentDecision | None:
    return (
        await db.execute(
            select(GateReassessmentDecision).where(
                GateReassessmentDecision.gate_reassessment_id
                == gate_reassessment_id
            )
        )
    ).scalar_one_or_none()


def _require_reassessment_decision_contract(
    command: CompleteGateReassessmentCommand,
) -> tuple[str, str, str, str]:
    decision_state = command.decision_state.strip()
    rationale = command.rationale.strip()
    idempotency_key, trace_id = _require_key_and_trace(
        idempotency_key=command.idempotency_key,
        trace_id=command.trace_id,
    )
    if decision_state not in {
        GateAssessmentState.PASS.value,
        GateAssessmentState.FAIL.value,
    }:
        raise AppError(
            "GATE_REASSESSMENT_DECISION_INVALID",
            "Human reassessment decision must be PASS or FAIL.",
            status_code=422,
        )
    if not rationale:
        raise AppError(
            "GATE_DECISION_RATIONALE_REQUIRED",
            "Human reassessment decision rationale is required.",
            status_code=422,
        )
    return decision_state, rationale, idempotency_key, trace_id


def _reassessment_decision_retry_matches(
    decision: GateReassessmentDecision,
    *,
    command: CompleteGateReassessmentCommand,
    decision_state: str,
    rationale: str,
    idempotency_key: str,
) -> bool:
    return (
        decision.gate_reassessment_id == command.gate_reassessment_id
        and decision.reviewer_id == command.reviewer_id
        and decision.decision_state == decision_state
        and decision.rationale == rationale
        and decision.prior_assessment_version == command.expected_version
        and decision.gate_definition_version_id
        == command.expected_gate_definition_version_id
        and decision.gate_profile_snapshot_id
        == command.expected_profile_snapshot_id
        and decision.gate_profile_snapshot_version
        == command.expected_profile_snapshot_version
        and decision.decision_idempotency_key == idempotency_key
    )


async def _load_reassessment_decision_retry(
    db: AsyncSession,
    *,
    decision: GateReassessmentDecision,
    command: CompleteGateReassessmentCommand,
    decision_state: str,
    rationale: str,
    idempotency_key: str,
) -> CompleteGateReassessmentResult:
    if not _reassessment_decision_retry_matches(
        decision,
        command=command,
        decision_state=decision_state,
        rationale=rationale,
        idempotency_key=idempotency_key,
    ):
        raise AppError(
            "GATE_IDEMPOTENCY_KEY_REUSED",
            "Idempotency key was already used for a different reassessment decision.",
            status_code=409,
        )

    reassessment = (
        await db.execute(
            select(GateReassessment).where(
                GateReassessment.id == decision.gate_reassessment_id,
                GateReassessment.organization_context_id
                == command.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    assessment = (
        await db.execute(
            select(GateAssessment).where(
                GateAssessment.id == decision.gate_assessment_id,
                GateAssessment.organization_context_id
                == command.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    snapshot = (
        await db.execute(
            select(GateProfileSnapshot).where(
                GateProfileSnapshot.id == decision.gate_profile_snapshot_id,
                GateProfileSnapshot.organization_context_id
                == command.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if reassessment is None or assessment is None or snapshot is None:
        raise AppError(
            "GATE_REASSESSMENT_LINEAGE_INCOMPLETE",
            "Completed reassessment decision is missing persisted lineage.",
            status_code=409,
        )
    return CompleteGateReassessmentResult(
        gate_assessment=assessment,
        reassessment=reassessment,
        decision=decision,
        profile_snapshot=snapshot,
    )


def _new_reassessment_completed_event(
    *,
    reassessment: GateReassessment,
    decision: GateReassessmentDecision,
    trace_id: str,
) -> EventEnvelope:
    return new_event(
        event_type="gate.review_completed.v1",
        aggregate_type="GateAssessment",
        aggregate_id=decision.gate_assessment_id,
        aggregate_version=decision.resulting_assessment_version,
        actor={"type": "PERSON", "id": str(decision.reviewer_id)},
        organization_context_id=decision.organization_context_id,
        data_classification="CONFIDENTIAL",
        payload={
            "review_kind": "REASSESSMENT",
            "gate_reassessment_id": str(reassessment.id),
            "gate_remediation_id": str(reassessment.gate_remediation_id),
            "gate_reassessment_decision_id": str(decision.id),
            "subject_person_id": str(decision.subject_person_id),
            "gate_definition_version_id": str(
                decision.gate_definition_version_id
            ),
            "profile_snapshot_id": str(decision.gate_profile_snapshot_id),
            "profile_snapshot_version": decision.gate_profile_snapshot_version,
            "decision_state": decision.decision_state,
            "prior_assessment_version": decision.prior_assessment_version,
            "resulting_assessment_version": (
                decision.resulting_assessment_version
            ),
        },
        trace_id=trace_id,
    )


async def complete_gate_reassessment(
    db: AsyncSession,
    *,
    command: CompleteGateReassessmentCommand,
) -> CompleteGateReassessmentResult:
    decision_state, rationale, idempotency_key, trace_id = (
        _require_reassessment_decision_contract(command)
    )
    existing = await _reassessment_decision_by_key(
        db,
        organization_context_id=command.organization_context_id,
        reviewer_id=command.reviewer_id,
        idempotency_key=idempotency_key,
    )
    if existing is not None:
        return await _load_reassessment_decision_retry(
            db,
            decision=existing,
            command=command,
            decision_state=decision_state,
            rationale=rationale,
            idempotency_key=idempotency_key,
        )

    reassessment = (
        await db.execute(
            select(GateReassessment).where(
                GateReassessment.id == command.gate_reassessment_id,
                GateReassessment.organization_context_id
                == command.organization_context_id,
            )
        )
    ).scalar_one_or_none()
    if reassessment is None:
        raise AppError(
            "GATE_REASSESSMENT_NOT_FOUND",
            "Gate reassessment not found.",
            status_code=404,
        )

    assessment = (
        await db.execute(
            select(GateAssessment)
            .where(
                GateAssessment.id == reassessment.gate_assessment_id,
                GateAssessment.organization_context_id
                == command.organization_context_id,
                GateAssessment.subject_person_id == reassessment.subject_person_id,
                GateAssessment.gate_definition_version_id
                == reassessment.gate_definition_version_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if assessment is None:
        raise AppError(
            "GATE_REASSESSMENT_LINEAGE_INCOMPLETE",
            "Gate reassessment is missing its Gate Assessment.",
            status_code=409,
        )

    raced = await _reassessment_decision_for_cycle(
        db,
        gate_reassessment_id=reassessment.id,
    )
    if raced is not None:
        if _reassessment_decision_retry_matches(
            raced,
            command=command,
            decision_state=decision_state,
            rationale=rationale,
            idempotency_key=idempotency_key,
        ):
            return await _load_reassessment_decision_retry(
                db,
                decision=raced,
                command=command,
                decision_state=decision_state,
                rationale=rationale,
                idempotency_key=idempotency_key,
            )
        raise AppError(
            "GATE_REASSESSMENT_ALREADY_DECIDED",
            "Gate reassessment already has an accountable Human decision.",
            status_code=409,
        )

    _require_expected_version(
        current_version=assessment.version,
        expected_version=command.expected_version,
    )
    if reassessment.reassessment_assessment_version != command.expected_version:
        raise AppError(
            "GATE_REASSESSMENT_VERSION_CONFLICT",
            "Reassessment is pinned to a different Gate Assessment version.",
            status_code=409,
        )
    if (
        reassessment.gate_definition_version_id
        != command.expected_gate_definition_version_id
    ):
        raise AppError(
            "GATE_DEFINITION_VERSION_CONFLICT",
            "Reassessment is pinned to a different Gate Definition version.",
            status_code=409,
        )
    if not gate_transition_allowed(assessment.state, decision_state):
        raise AppError(
            "GATE_STATE_CONFLICT",
            "Requested Human reassessment decision is not allowed.",
            status_code=409,
            details={
                "current_state": assessment.state,
                "target_state": decision_state,
            },
        )

    snapshot = (
        await db.execute(
            select(GateProfileSnapshot).where(
                GateProfileSnapshot.id
                == reassessment.gate_profile_snapshot_id,
                GateProfileSnapshot.gate_assessment_id == assessment.id,
                GateProfileSnapshot.organization_context_id
                == command.organization_context_id,
                GateProfileSnapshot.subject_person_id
                == assessment.subject_person_id,
            )
        )
    ).scalar_one_or_none()
    if snapshot is None:
        raise AppError(
            "GATE_REASSESSMENT_LINEAGE_INCOMPLETE",
            "Reassessment is missing its pinned Profile Snapshot.",
            status_code=409,
        )
    if (
        snapshot.id != command.expected_profile_snapshot_id
        or snapshot.snapshot_version
        != command.expected_profile_snapshot_version
    ):
        raise AppError(
            "GATE_PROFILE_SNAPSHOT_VERSION_CONFLICT",
            "Reassessment is pinned to a different Profile Snapshot.",
            status_code=409,
        )

    await _require_snapshot_lineage_complete(
        db,
        profile_snapshot_id=snapshot.id,
    )

    now = datetime.now(UTC)
    prior_version = assessment.version
    assessment.state = decision_state
    assessment.version += 1
    assessment.updated_at = now

    decision = GateReassessmentDecision(
        id=uuid4(),
        gate_reassessment_id=reassessment.id,
        gate_assessment_id=assessment.id,
        gate_profile_snapshot_id=snapshot.id,
        gate_profile_snapshot_version=snapshot.snapshot_version,
        gate_definition_version_id=reassessment.gate_definition_version_id,
        organization_context_id=assessment.organization_context_id,
        subject_person_id=assessment.subject_person_id,
        prior_assessment_version=prior_version,
        resulting_assessment_version=assessment.version,
        decision_state=decision_state,
        reviewer_id=command.reviewer_id,
        rationale=rationale,
        decided_at=now,
        decision_idempotency_key=idempotency_key,
        trace_id=trace_id,
    )
    db.add(decision)
    record_event(
        db,
        _new_reassessment_completed_event(
            reassessment=reassessment,
            decision=decision,
            trace_id=trace_id,
        ),
    )
    await db.commit()
    return CompleteGateReassessmentResult(
        gate_assessment=assessment,
        reassessment=reassessment,
        decision=decision,
        profile_snapshot=snapshot,
    )
