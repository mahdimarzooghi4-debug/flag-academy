from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FlagProfile(Base):
    __tablename__ = "flag_profiles"
    __table_args__ = (
        UniqueConstraint(
            "organization_context_id",
            "subject_person_id",
            "track_code",
            name="uq_flag_profile_subject_track",
        ),
        {"schema": "flag_profile"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    organization_context_id: Mapped[UUID]
    subject_person_id: Mapped[UUID]
    track_code: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProfileUpdateCase(Base):
    __tablename__ = "profile_update_cases"
    __table_args__ = (
        UniqueConstraint(
            "organization_context_id",
            "created_by",
            "creation_idempotency_key",
            name="uq_profile_update_case_creation_idempotency",
        ),
        {"schema": "flag_profile"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    flag_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("flag_profile.flag_profiles.id")
    )
    organization_context_id: Mapped[UUID]
    subject_person_id: Mapped[UUID]
    track_code: Mapped[str] = mapped_column(String(128))

    # Opaque Curriculum reference: no cross-context database FK.
    capability_id: Mapped[UUID]

    state: Mapped[str] = mapped_column(String(32))

    # Snapshot of the current claim when the proposal was created.
    current_claim_id: Mapped[UUID | None] = mapped_column(nullable=True)
    current_claim_version: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_claim_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    current_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    current_proven_scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_evidence_recency: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    current_confidence_in_claim: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    current_next_evidence_needed: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    proposed_claim_state: Mapped[str] = mapped_column(String(32))
    proposed_level: Mapped[str] = mapped_column(String(16))
    proposed_proven_scope: Mapped[str] = mapped_column(String(255))
    proposed_evidence_recency: Mapped[str] = mapped_column(String(255))
    proposed_confidence_in_claim: Mapped[str] = mapped_column(String(64))
    proposed_next_evidence_needed: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)

    reviewed_claim_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reviewed_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reviewed_proven_scope: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    reviewed_evidence_recency: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    reviewed_confidence_in_claim: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    reviewed_next_evidence_needed: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    review_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[UUID]
    review_requested_by: Mapped[UUID | None] = mapped_column(nullable=True)
    review_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    applied_by: Mapped[UUID | None] = mapped_column(nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    creation_idempotency_key: Mapped[str] = mapped_column(String(160))
    review_request_idempotency_key: Mapped[str | None] = mapped_column(
        String(160), nullable=True
    )
    review_idempotency_key: Mapped[str | None] = mapped_column(
        String(160), nullable=True
    )
    apply_idempotency_key: Mapped[str | None] = mapped_column(
        String(160), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProfileUpdatePattern(Base):
    __tablename__ = "profile_update_patterns"
    __table_args__ = (
        UniqueConstraint(
            "profile_update_case_id",
            "pattern_id",
            name="uq_profile_update_case_pattern",
        ),
        {"schema": "flag_profile"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    profile_update_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("flag_profile.profile_update_cases.id")
    )

    # Opaque Pattern reference and reviewed snapshot: no cross-context FK.
    pattern_id: Mapped[UUID]
    pattern_version: Mapped[int] = mapped_column(BigInteger)
    relationship: Mapped[str] = mapped_column(String(32))
    pattern_status: Mapped[str] = mapped_column(String(32))
    behaviour_code: Mapped[str] = mapped_column(String(120))
    pattern_scope: Mapped[str] = mapped_column(String(255))
    pattern_reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProfileUpdatePatternEvidence(Base):
    __tablename__ = "profile_update_pattern_evidence"
    __table_args__ = (
        UniqueConstraint(
            "profile_update_pattern_id",
            "evidence_set_member_id",
            name="uq_profile_update_pattern_evidence_member",
        ),
        {"schema": "flag_profile"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    profile_update_pattern_id: Mapped[UUID] = mapped_column(
        ForeignKey("flag_profile.profile_update_patterns.id")
    )

    # Explicit immutable lineage snapshots. All source ids remain opaque.
    evidence_set_member_id: Mapped[UUID]
    evidence_case_id: Mapped[UUID]
    interpretation_id: Mapped[UUID]
    interpretation_version: Mapped[int] = mapped_column(Integer)
    evidence_relationship: Mapped[str] = mapped_column(String(32))
    signal: Mapped[str] = mapped_column(String(32))
    evidence_scope: Mapped[str] = mapped_column(String(255))
    confidence: Mapped[str] = mapped_column(String(32))
    context_difficulty: Mapped[str] = mapped_column(String(255))
    prompt_contamination: Mapped[str] = mapped_column(String(255))
    source_independence_group: Mapped[str] = mapped_column(String(255))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_observation_id: Mapped[UUID]
    source_context: Mapped[str] = mapped_column(String(64))
    source_reference: Mapped[str] = mapped_column(String(255))
    observation_type: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CapabilityClaim(Base):
    __tablename__ = "capability_claims"
    __table_args__ = (
        UniqueConstraint(
            "flag_profile_id",
            "capability_id",
            name="uq_capability_claim_profile_capability",
        ),
        {"schema": "flag_profile"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    flag_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("flag_profile.flag_profiles.id")
    )
    organization_context_id: Mapped[UUID]
    subject_person_id: Mapped[UUID]
    track_code: Mapped[str] = mapped_column(String(128))

    # Opaque Curriculum reference: no cross-context database FK.
    capability_id: Mapped[UUID]

    state: Mapped[str] = mapped_column(String(32))
    level: Mapped[str] = mapped_column(String(16))
    proven_scope: Mapped[str] = mapped_column(String(255))
    evidence_recency: Mapped[str] = mapped_column(String(255))
    confidence_in_claim: Mapped[str] = mapped_column(String(64))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[UUID]
    next_evidence_needed: Mapped[str] = mapped_column(Text)
    source_profile_update_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("flag_profile.profile_update_cases.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CapabilityClaimPattern(Base):
    __tablename__ = "capability_claim_patterns"
    __table_args__ = (
        UniqueConstraint(
            "capability_claim_id",
            "pattern_id",
            name="uq_capability_claim_pattern",
        ),
        {"schema": "flag_profile"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    capability_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("flag_profile.capability_claims.id")
    )

    # Opaque Pattern reference: no cross-context database FK.
    pattern_id: Mapped[UUID]
    pattern_version: Mapped[int] = mapped_column(BigInteger)
    relationship: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
