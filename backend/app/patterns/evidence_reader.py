from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.contracts import load_accepted_evidence_snapshots
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
        snapshots = await load_accepted_evidence_snapshots(
            self._db,
            organization_context_id=organization_context_id,
            subject_person_id=subject_person_id,
            evidence_case_ids=evidence_case_ids,
        )
        return [
            AcceptedEvidenceSnapshot(
                evidence_case_id=item.evidence_case_id,
                interpretation_id=item.interpretation_id,
                interpretation_version=item.interpretation_version,
                organization_context_id=item.organization_context_id,
                subject_person_id=item.subject_person_id,
                status=item.status,
                interpretation_status=item.interpretation_status,
                behaviour_code=item.behaviour_code,
                signal=item.signal,
                scope=item.scope,
                confidence=item.confidence,
                context_difficulty=item.context_difficulty,
                prompt_contamination=item.prompt_contamination,
                source_independence_group=item.source_independence_group,
                accepted_at=item.accepted_at,
                target_links=item.target_links,
                source_lineage=item.source_lineage,
            )
            for item in snapshots
        ]
