from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EvidenceSet(Base):
    __tablename__ = "evidence_sets"
    __table_args__ = (
        UniqueConstraint(
            "evidence_set_key",
            "version_number",
            name="uq_pattern_evidence_set_key_version",
        ),
        UniqueConstraint(
            "organization_context_id",
            "created_by",
            "idempotency_key",
            name="uq_pattern_evidence_set_idempotency",
        ),
        {"schema": "patterns"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    evidence_set_key: Mapped[UUID] = mapped_column(default=uuid4)
    version_number: Mapped[int] = mapped_column(Integer)
    organization_context_id: Mapped[UUID]
    subject_person_id: Mapped[UUID]
    created_by: Mapped[UUID]
    idempotency_key: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EvidenceSetMember(Base):
    __tablename__ = "evidence_set_members"
    __table_args__ = (
        UniqueConstraint(
            "evidence_set_id",
            "evidence_case_id",
            name="uq_pattern_evidence_set_member_case",
        ),
        {"schema": "patterns"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    evidence_set_id: Mapped[UUID] = mapped_column(
        ForeignKey("patterns.evidence_sets.id")
    )

    # Opaque cross-context references. There is intentionally no database
    # foreign key into the Evidence bounded context.
    evidence_case_id: Mapped[UUID]
    interpretation_id: Mapped[UUID]
    interpretation_version: Mapped[int] = mapped_column(Integer)

    behaviour_code: Mapped[str] = mapped_column(String(120))
    signal: Mapped[str] = mapped_column(String(32))
    scope: Mapped[str] = mapped_column(String(255))
    confidence: Mapped[str] = mapped_column(String(32))
    context_difficulty: Mapped[str] = mapped_column(String(255))
    prompt_contamination: Mapped[str] = mapped_column(String(255))
    source_independence_group: Mapped[str] = mapped_column(String(255))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    target_links: Mapped[list[dict]] = mapped_column(JSONB)
    source_lineage: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PatternCandidate(Base):
    __tablename__ = "pattern_candidates"
    __table_args__ = (
        UniqueConstraint(
            "organization_context_id",
            "created_by",
            "idempotency_key",
            name="uq_pattern_candidate_idempotency",
        ),
        {"schema": "patterns"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    organization_context_id: Mapped[UUID]
    subject_person_id: Mapped[UUID]
    evidence_set_id: Mapped[UUID] = mapped_column(
        ForeignKey("patterns.evidence_sets.id")
    )
    behaviour_code: Mapped[str] = mapped_column(String(120))
    behaviour_description: Mapped[str] = mapped_column(Text)
    proposed_pattern_status: Mapped[str] = mapped_column(String(32))
    scope: Mapped[str] = mapped_column(String(255))
    rationale: Mapped[str] = mapped_column(Text)
    created_by: Mapped[UUID]
    idempotency_key: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PatternCandidateEvidence(Base):
    __tablename__ = "pattern_candidate_evidence"
    __table_args__ = (
        UniqueConstraint(
            "pattern_candidate_id",
            "evidence_set_member_id",
            name="uq_pattern_candidate_evidence_member",
        ),
        {"schema": "patterns"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    pattern_candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("patterns.pattern_candidates.id")
    )
    evidence_set_member_id: Mapped[UUID] = mapped_column(
        ForeignKey("patterns.evidence_set_members.id")
    )
    relationship: Mapped[str] = mapped_column(String(32))


class BehaviourPattern(Base):
    __tablename__ = "behaviour_patterns"
    __table_args__ = (
        UniqueConstraint(
            "source_pattern_candidate_id",
            name="uq_behaviour_pattern_source_candidate",
        ),
        {"schema": "patterns"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    organization_context_id: Mapped[UUID]
    subject_person_id: Mapped[UUID]
    source_pattern_candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("patterns.pattern_candidates.id")
    )
    evidence_set_id: Mapped[UUID] = mapped_column(
        ForeignKey("patterns.evidence_sets.id")
    )
    behaviour_code: Mapped[str] = mapped_column(String(120))
    behaviour_description: Mapped[str] = mapped_column(Text)
    pattern_status: Mapped[str] = mapped_column(String(32))
    scope: Mapped[str] = mapped_column(String(255))
    rationale: Mapped[str] = mapped_column(Text)
    reviewed_by: Mapped[UUID]
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PatternReview(Base):
    __tablename__ = "pattern_reviews"
    __table_args__ = {"schema": "patterns"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    pattern_candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("patterns.pattern_candidates.id")
    )
    reviewer_id: Mapped[UUID]
    decision: Mapped[str] = mapped_column(String(32))
    rationale: Mapped[str] = mapped_column(Text)
    resulting_pattern_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("patterns.behaviour_patterns.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
