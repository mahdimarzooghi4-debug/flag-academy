from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.patterns.contracts import (
    ReviewedPatternSnapshotContract,
    load_reviewed_pattern_snapshots,
)


class ReviewedPatternReader:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def load(
        self,
        *,
        organization_context_id: UUID,
        subject_person_id: UUID,
        pattern_ids: tuple[UUID, ...],
    ) -> list[ReviewedPatternSnapshotContract]:
        return await load_reviewed_pattern_snapshots(
            self._db,
            organization_context_id=organization_context_id,
            subject_person_id=subject_person_id,
            pattern_ids=pattern_ids,
        )
