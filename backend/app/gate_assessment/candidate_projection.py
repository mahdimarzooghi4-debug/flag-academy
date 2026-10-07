from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gate_assessment.domain import GateAssessmentState
from app.gate_assessment.models import (
    GateAssessment,
    GateDefinition,
    GateDefinitionVersion,
    GateProfileSnapshot,
    GateProfileSnapshotClaim,
)


@dataclass(frozen=True)
class CandidateGateItem:
    gate_code: str
    gate_name: str
    status: str
    evidence_gaps: tuple[str, ...]
    remediation_status: str | None


@dataclass(frozen=True)
class CandidateGateProjection:
    gates: tuple[CandidateGateItem, ...]


def _candidate_remediation_status(state: str) -> str | None:
    if state in {
        GateAssessmentState.REMEDIATION.value,
        GateAssessmentState.REASSESSMENT.value,
    }:
        return state
    return None


async def _latest_snapshot_gaps(
    db: AsyncSession,
    *,
    gate_assessment_id: UUID,
    organization_context_id: UUID,
    subject_person_id: UUID,
) -> tuple[str, ...]:
    snapshot = (
        await db.execute(
            select(GateProfileSnapshot)
            .where(
                GateProfileSnapshot.gate_assessment_id == gate_assessment_id,
                GateProfileSnapshot.organization_context_id
                == organization_context_id,
                GateProfileSnapshot.subject_person_id == subject_person_id,
            )
            .order_by(
                GateProfileSnapshot.snapshot_version.desc(),
                GateProfileSnapshot.id.desc(),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if snapshot is None:
        return ()

    claims = (
        await db.execute(
            select(GateProfileSnapshotClaim)
            .where(
                GateProfileSnapshotClaim.gate_profile_snapshot_id == snapshot.id
            )
            .order_by(
                GateProfileSnapshotClaim.capability_id,
                GateProfileSnapshotClaim.source_claim_id,
            )
        )
    ).scalars().all()

    gaps: list[str] = []
    seen: set[str] = set()
    for claim in claims:
        gap = claim.next_evidence_needed.strip()
        if gap and gap not in seen:
            gaps.append(gap)
            seen.add(gap)
    return tuple(gaps)


async def load_candidate_gate_projection(
    db: AsyncSession,
    *,
    organization_context_id: UUID,
    subject_person_id: UUID,
) -> CandidateGateProjection:
    rows = (
        await db.execute(
            select(GateAssessment, GateDefinitionVersion, GateDefinition)
            .join(
                GateDefinitionVersion,
                GateDefinitionVersion.id
                == GateAssessment.gate_definition_version_id,
            )
            .join(
                GateDefinition,
                GateDefinition.id
                == GateDefinitionVersion.gate_definition_id,
            )
            .where(
                GateAssessment.organization_context_id
                == organization_context_id,
                GateAssessment.subject_person_id == subject_person_id,
            )
            .order_by(
                GateDefinition.code,
                GateDefinitionVersion.version_number,
                GateAssessment.id,
            )
        )
    ).all()

    items: list[CandidateGateItem] = []
    for assessment, definition_version, definition in rows:
        items.append(
            CandidateGateItem(
                gate_code=definition.code,
                gate_name=definition_version.name,
                status=assessment.state,
                evidence_gaps=await _latest_snapshot_gaps(
                    db,
                    gate_assessment_id=assessment.id,
                    organization_context_id=organization_context_id,
                    subject_person_id=subject_person_id,
                ),
                remediation_status=_candidate_remediation_status(
                    assessment.state
                ),
            )
        )

    return CandidateGateProjection(gates=tuple(items))
