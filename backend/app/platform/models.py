from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DomainEvent(Base):
    __tablename__ = "domain_events"
    __table_args__ = {"schema": "platform"}

    event_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(160))
    event_version: Mapped[int] = mapped_column(Integer)
    aggregate_type: Mapped[str] = mapped_column(String(128))
    aggregate_id: Mapped[UUID]
    aggregate_version: Mapped[int] = mapped_column(BigInteger)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor: Mapped[dict] = mapped_column(JSONB)
    correlation_id: Mapped[UUID | None]
    causation_id: Mapped[UUID | None]
    organization_context_id: Mapped[UUID | None]
    data_classification: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSONB)
    trace_id: Mapped[str] = mapped_column(String(128))


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = {"schema": "platform"}

    event_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(160))
    event_version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSONB)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class InboxEvent(Base):
    __tablename__ = "inbox_events"
    __table_args__ = (
        UniqueConstraint("consumer_name", "event_id"),
        {"schema": "platform"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    consumer_name: Mapped[str] = mapped_column(String(128))
    event_id: Mapped[UUID]
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
