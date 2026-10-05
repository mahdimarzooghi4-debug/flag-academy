from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MissionInstance(Base):
    __tablename__ = "mission_instances"
    __table_args__ = (
        UniqueConstraint(
            "mission_version_id",
            "candidate_id",
            "start_idempotency_key",
            name="uq_mission_instance_start_idempotency",
        ),
        {"schema": "mission_runtime"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    organization_context_id: Mapped[UUID]
    mission_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("mission_design.mission_versions.id")
    )
    candidate_id: Mapped[UUID]
    status: Mapped[str] = mapped_column(String(32))
    world_state: Mapped[dict] = mapped_column(JSONB)
    world_state_version: Mapped[int] = mapped_column(BigInteger, default=1)
    simulation_seed: Mapped[int] = mapped_column(BigInteger)
    start_idempotency_key: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CandidateAction(Base):
    __tablename__ = "candidate_actions"
    __table_args__ = (
        UniqueConstraint(
            "mission_instance_id",
            "idempotency_key",
            name="uq_candidate_action_instance_idempotency",
        ),
        {"schema": "mission_runtime"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    mission_instance_id: Mapped[UUID] = mapped_column(
        ForeignKey("mission_runtime.mission_instances.id")
    )
    candidate_id: Mapped[UUID]
    action_type: Mapped[str] = mapped_column(String(48))
    target: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    reasoning: Mapped[str] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resource_cost: Mapped[dict] = mapped_column(JSONB)
    mode: Mapped[str] = mapped_column(String(32))
    provenance: Mapped[dict] = mapped_column(JSONB)
    idempotency_key: Mapped[str] = mapped_column(String(160))


class DecisionRecord(Base):
    __tablename__ = "decision_records"
    __table_args__ = (
        UniqueConstraint("action_id", name="uq_decision_record_action"),
        {"schema": "mission_runtime"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    mission_instance_id: Mapped[UUID] = mapped_column(
        ForeignKey("mission_runtime.mission_instances.id")
    )
    action_id: Mapped[UUID] = mapped_column(
        ForeignKey("mission_runtime.candidate_actions.id")
    )
    question: Mapped[str] = mapped_column(Text)
    options_considered: Mapped[list] = mapped_column(JSONB)
    available_evidence: Mapped[list] = mapped_column(JSONB)
    assumptions: Mapped[list] = mapped_column(JSONB)
    decision: Mapped[str] = mapped_column(Text)
    reasoning: Mapped[str] = mapped_column(Text)
    confidence: Mapped[int] = mapped_column(Integer)
    expected_outcome: Mapped[str] = mapped_column(Text)
    revisit_trigger: Mapped[str] = mapped_column(Text)
    decision_owner: Mapped[UUID]
    reversibility: Mapped[str] = mapped_column(String(64))
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RuntimeEvent(Base):
    __tablename__ = "runtime_events"
    __table_args__ = (
        UniqueConstraint(
            "mission_instance_id",
            "sequence_number",
            name="uq_runtime_event_instance_sequence",
        ),
        UniqueConstraint(
            "mission_instance_id",
            "idempotency_key",
            name="uq_runtime_event_instance_idempotency",
        ),
        {"schema": "mission_runtime"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    mission_instance_id: Mapped[UUID] = mapped_column(
        ForeignKey("mission_runtime.mission_instances.id")
    )
    sequence_number: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(160))
    source: Mapped[str] = mapped_column(String(64))
    trigger_type: Mapped[str] = mapped_column(String(64))
    trigger_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    visibility: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSONB)
    world_version_before: Mapped[int] = mapped_column(BigInteger)
    world_version_after: Mapped[int] = mapped_column(BigInteger)
    causal_parent_ids: Mapped[list] = mapped_column(JSONB)
    idempotency_key: Mapped[str] = mapped_column(String(200))


class Observation(Base):
    __tablename__ = "observations"
    __table_args__ = (
        UniqueConstraint("source_event_id", name="uq_observation_source_event"),
        {"schema": "mission_runtime"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    mission_instance_id: Mapped[UUID] = mapped_column(
        ForeignKey("mission_runtime.mission_instances.id")
    )
    source_event_id: Mapped[UUID] = mapped_column(
        ForeignKey("mission_runtime.runtime_events.id")
    )
    sequence_number: Mapped[int] = mapped_column(Integer)
    observation_type: Mapped[str] = mapped_column(String(80))
    factual_statement: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
