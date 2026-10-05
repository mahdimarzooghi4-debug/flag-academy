from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EvidenceCase(Base):
    __tablename__ = "evidence_cases"
    __table_args__ = (
        UniqueConstraint("source_observation_id", name="uq_evidence_case_source_observation"),
        {"schema": "evidence"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    organization_context_id: Mapped[UUID]
    subject_person_id: Mapped[UUID]
    source_observation_id: Mapped[UUID]
    source_context: Mapped[str] = mapped_column(String(64))
    source_reference: Mapped[str] = mapped_column(String(255))
    source_runtime_event_id: Mapped[UUID | None] = mapped_column(nullable=True)
    observation_type: Mapped[str] = mapped_column(String(80))
    observed_fact: Mapped[str] = mapped_column(Text)
    observed_payload: Mapped[dict] = mapped_column(JSONB)
    candidate_visible: Mapped[bool] = mapped_column(default=False)
    candidate_visible_payload: Mapped[dict] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_independence_group: Mapped[str] = mapped_column(String(255))
    provenance: Mapped[dict] = mapped_column(JSONB)
    integrity_state: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    context_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvidenceInterpretation(Base):
    __tablename__ = "evidence_interpretations"
    __table_args__ = (
        UniqueConstraint(
            "evidence_case_id",
            "version_number",
            name="uq_evidence_interpretation_case_version",
        ),
        {"schema": "evidence"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    evidence_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.evidence_cases.id")
    )
    version_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
    behaviour_code: Mapped[str] = mapped_column(String(120))
    behaviour_description: Mapped[str] = mapped_column(Text)
    signal: Mapped[str] = mapped_column(String(32))
    scope: Mapped[str] = mapped_column(String(255))
    confidence: Mapped[str] = mapped_column(String(32))
    context_difficulty: Mapped[str] = mapped_column(String(255))
    prompt_contamination: Mapped[str] = mapped_column(String(255))
    ai_contribution: Mapped[str] = mapped_column(String(255))
    mode: Mapped[str] = mapped_column(String(32))
    rationale: Mapped[str] = mapped_column(Text)
    created_by: Mapped[UUID]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EvidenceLink(Base):
    __tablename__ = "evidence_links"
    __table_args__ = {"schema": "evidence"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    interpretation_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.evidence_interpretations.id")
    )
    target_type: Mapped[str] = mapped_column(String(32))
    target_ref: Mapped[str] = mapped_column(String(255))
    signal: Mapped[str] = mapped_column(String(32))
    scope: Mapped[str] = mapped_column(String(255))
    relevance: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[str] = mapped_column(String(32))


class EvidenceReview(Base):
    __tablename__ = "evidence_reviews"
    __table_args__ = {"schema": "evidence"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    evidence_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.evidence_cases.id")
    )
    reviewer_id: Mapped[UUID]
    decision: Mapped[str] = mapped_column(String(32))
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CandidateResponse(Base):
    __tablename__ = "candidate_responses"
    __table_args__ = (
        UniqueConstraint(
            "evidence_case_id",
            "idempotency_key",
            name="uq_candidate_response_case_idempotency",
        ),
        {"schema": "evidence"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    evidence_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence.evidence_cases.id")
    )
    candidate_id: Mapped[UUID]
    response_text: Mapped[str] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
