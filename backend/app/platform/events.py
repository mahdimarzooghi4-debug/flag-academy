from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.models import DomainEvent, OutboxEvent


class EventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    event_version: int = 1
    aggregate_type: str
    aggregate_id: UUID
    aggregate_version: int
    occurred_at: datetime
    actor: dict[str, Any]
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    organization_context_id: UUID | None = None
    data_classification: str
    payload: dict[str, Any]
    trace_id: str


def new_event(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    aggregate_version: int,
    actor: dict[str, Any],
    data_classification: str,
    payload: dict[str, Any],
    trace_id: str,
    organization_context_id: UUID | None = None,
    correlation_id: UUID | None = None,
    causation_id: UUID | None = None,
    occurred_at: datetime | None = None,
) -> EventEnvelope:
    return EventEnvelope(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        aggregate_version=aggregate_version,
        occurred_at=occurred_at or datetime.now(UTC),
        actor=actor,
        correlation_id=correlation_id,
        causation_id=causation_id,
        organization_context_id=organization_context_id,
        data_classification=data_classification,
        payload=payload,
        trace_id=trace_id,
    )


def record_event(session: AsyncSession, envelope: EventEnvelope) -> None:
    """Persist audit event and transactional outbox record in the caller's transaction."""
    session.add(
        DomainEvent(
            event_id=envelope.event_id,
            event_type=envelope.event_type,
            event_version=envelope.event_version,
            aggregate_type=envelope.aggregate_type,
            aggregate_id=envelope.aggregate_id,
            aggregate_version=envelope.aggregate_version,
            occurred_at=envelope.occurred_at,
            actor=envelope.actor,
            correlation_id=envelope.correlation_id,
            causation_id=envelope.causation_id,
            organization_context_id=envelope.organization_context_id,
            data_classification=envelope.data_classification,
            payload=envelope.payload,
            trace_id=envelope.trace_id,
        )
    )
    session.add(
        OutboxEvent(
            event_id=envelope.event_id,
            event_type=envelope.event_type,
            event_version=envelope.event_version,
            payload=envelope.model_dump(mode="json"),
            created_at=envelope.occurred_at,
        )
    )
