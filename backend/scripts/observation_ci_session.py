"""CI-ONLY: add a short synthetic Session for genuine OIDC Observation testing.

No production bootstrap, sample approval, or operational Session state is changed.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.academy.models import Session
from app.db import SessionFactory

CLASS_ID = UUID("00000000-0000-0000-0000-000000000220")
CI_SESSION_ID = UUID("00000000-0000-0000-0000-000000000243")


async def main() -> None:
    now = datetime.now(UTC)
    async with SessionFactory() as db:
        db.add(
            Session(
                id=CI_SESSION_ID,
                class_offering_id=CLASS_ID,
                title="CI-only current session, not a real Academy class",
                starts_at=now - timedelta(minutes=30),
                ends_at=now + timedelta(minutes=30),
                delivery_mode="ONLINE",
                status="ACTIVE",
            )
        )
        await db.commit()


if __name__ == "__main__":
    asyncio.run(main())
