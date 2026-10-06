from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.models import EvidenceCase, EvidenceInterpretation, EvidenceLink
from app.patterns.application import AcceptedEvidenceSnapshot


class SqlAcceptedEvidenceReader:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def load(
        self,
        *,
        organization_context_id: UUID,
        subject_person_id: UUID,
        evidence_case_ids: tuple[UUID, ...],
    ) -> list[AcceptedEvidenceSnapshot]:
        cases = (
            await self._db.execute(
                select(EvidenceCase)
                .where(
                    EvidenceCase.id.in_(evidence_case_ids),
                    EvidenceCase.organization_context_id == organization_context_id,
                    EvidenceCase.subject_person_id == subject_person_id,
                    EvidenceCase.status == "ACCEPTED",
                )
                .order_by(EvidenceCase.created_at, EvidenceCase.id)
            )
        ).scalars().all()

        snapshots: list[AcceptedEvidenceSnapshot] = []
        for case in cases:
            if case.accepted_at is None:
                continue
            interpretation = (
                await self._db.execute(
                    select(EvidenceInterpretation)
                    .where(
                        EvidenceInterpretation.evidence_case_id == case.id,
                        EvidenceInterpretation.status == "ACTIVE",
                    )
                    .order_by(EvidenceInterpretation.version_number.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if interpretation is None:
                continue

            links = (
                await self._db.execute(
                    select(EvidenceLink)
                    .where(EvidenceLink.interpretation_id == interpretation.id)
                    .order_by(
                        EvidenceLink.target_type,
                        EvidenceLink.target_ref,
                        EvidenceLink.id,
                    )
                )
            ).scalars().all()

            snapshots.append(
                AcceptedEvidenceSnapshot(
                    evidence_case_id=case.id,
                    interpretation_id=interpretation.id,
                    interpretation_version=interpretation.version_number,
                    organization_context_id=case.organization_context_id,
                    subject_person_id=case.subject_person_id,
                    status=case.status,
                    interpretation_status=interpretation.status,
                    behaviour_code=interpretation.behaviour_code,
                    signal=interpretation.signal,
                    scope=interpretation.scope,
                    confidence=interpretation.confidence,
                    context_difficulty=interpretation.context_difficulty,
                    prompt_contamination=interpretation.prompt_contamination,
                    source_independence_group=case.source_independence_group,
                    accepted_at=case.accepted_at,
                    target_links=[
                        {
                            "target_type": link.target_type,
                            "target_ref": link.target_ref,
                            "signal": link.signal,
                            "scope": link.scope,
                            "relevance": link.relevance,
                            "confidence": link.confidence,
                        }
                        for link in links
                    ],
                    source_lineage={
                        "source_observation_id": str(case.source_observation_id),
                        "source_context": case.source_context,
                        "source_reference": case.source_reference,
                        "observation_type": case.observation_type,
                    },
                )
            )
        return snapshots
