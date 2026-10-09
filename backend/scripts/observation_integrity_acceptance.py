"""CI-only real PostgreSQL invariants for Classroom Observation.

Runs after the live OIDC browser test: verifies one Observation and one event,
immutability at the DB engine, and that private note text is absent from Outbox.
"""
from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from app.academy.models import ClassAssessorObservation
from app.db import SessionFactory, engine
from app.platform.models import DomainEvent, OutboxEvent

ORG_ID = UUID("00000000-0000-0000-0000-000000000001")
CLASS_ID = UUID("00000000-0000-0000-0000-000000000220")
SESSION_ID = UUID("00000000-0000-0000-0000-000000000243")
ASSESSOR_ID = UUID("00000000-0000-0000-0000-000000000104")


async def main() -> None:
    async with SessionFactory() as db:
        items = (
            await db.execute(
                select(ClassAssessorObservation).where(
                    ClassAssessorObservation.organization_context_id == ORG_ID,
                    ClassAssessorObservation.class_offering_id == CLASS_ID,
                    ClassAssessorObservation.session_id == SESSION_ID,
                    ClassAssessorObservation.observer_person_id == ASSESSOR_ID,
                )
            )
        ).scalars().all()
        assert len(items) == 1, "Concurrent requests must produce exactly one source row"
        item = items[0]
        assert item.recorded_at >= item.observed_at
        events = (
            await db.execute(
                select(DomainEvent).where(
                    DomainEvent.aggregate_id == item.id,
                    DomainEvent.event_type == "academy.class_observation_recorded.v1",
                    DomainEvent.organization_context_id == ORG_ID,
                )
            )
        ).scalars().all()
        assert len(events) == 1, "Replay must not create another audit event"
        event = events[0]
        assert event.actor == {"type": "PERSON", "id": str(ASSESSOR_ID)}
        assert item.observed_fact not in str(event.payload), "Private note exposed in DomainEvent"
        outbox = (
            await db.execute(
                select(OutboxEvent).where(OutboxEvent.event_id == event.event_id)
            )
        ).scalar_one()
        assert item.observed_fact not in str(outbox.payload), "Private note exposed in Outbox"

    # Even privileged SQL connections must not be able to edit or delete history.
    async with engine.connect() as conn:
        trans = await conn.begin()
        for command in (
            update(ClassAssessorObservation)
            .where(ClassAssessorObservation.id == item.id)
            .values(observed_fact="Tampered after review"),
            delete(ClassAssessorObservation).where(
                ClassAssessorObservation.id == item.id
            ),
        ):
            savepoint = await conn.begin_nested()
            try:
                await conn.execute(command)
            except DBAPIError:
                await savepoint.rollback()
            else:
                await savepoint.rollback()
                raise AssertionError("PostgreSQL must reject observation mutation")
        await trans.rollback()

    async with SessionFactory() as db:
        restored = (
            await db.execute(
                select(ClassAssessorObservation).where(
                    ClassAssessorObservation.id == item.id
                )
            )
        ).scalar_one()
        assert restored.observed_fact == item.observed_fact


if __name__ == "__main__":
    asyncio.run(main())
