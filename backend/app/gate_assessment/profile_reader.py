from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.flag_profile.contracts import (
    CurrentFlagProfileSnapshotContract,
    load_current_flag_profile_snapshot,
)


class FlagProfileSnapshotReader:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def load(
        self,
        *,
        organization_context_id: UUID,
        subject_person_id: UUID,
        track_code: str,
    ) -> CurrentFlagProfileSnapshotContract:
        return await load_current_flag_profile_snapshot(
            self._db,
            organization_context_id=organization_context_id,
            subject_person_id=subject_person_id,
            track_code=track_code,
        )
