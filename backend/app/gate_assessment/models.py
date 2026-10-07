from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class GateDefinition(Base):
    __tablename__ = "gate_definitions"
    __table_args__ = {"schema": "gate_assessment"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(8), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GateDefinitionVersion(Base):
    __tablename__ = "gate_definition_versions"
    __table_args__ = (
        UniqueConstraint(
            "gate_definition_id",
            "version_number",
            name="uq_gate_definition_version",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_definitions.id")
    )
    version_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255))
    decision_question: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GateDefinitionRequirement(Base):
    __tablename__ = "gate_definition_requirements"
    __table_args__ = (
        UniqueConstraint(
            "gate_definition_version_id",
            "position",
            name="uq_gate_definition_requirement_position",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_definition_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_definition_versions.id")
    )
    position: Mapped[int] = mapped_column(Integer)
    requirement_text: Mapped[str] = mapped_column(Text)


class GateDefinitionOutcome(Base):
    __tablename__ = "gate_definition_outcomes"
    __table_args__ = (
        UniqueConstraint(
            "gate_definition_version_id",
            "position",
            name="uq_gate_definition_outcome_position",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_definition_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_definition_versions.id")
    )
    position: Mapped[int] = mapped_column(Integer)
    outcome_text: Mapped[str] = mapped_column(Text)



class GateAssessment(Base):
    __tablename__ = "gate_assessments"
    __table_args__ = (
        UniqueConstraint(
            "organization_context_id",
            "subject_person_id",
            "gate_definition_version_id",
            name="uq_gate_assessment_identity",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    version: Mapped[int] = mapped_column(BigInteger, default=1)
    gate_definition_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_definition_versions.id")
    )
    organization_context_id: Mapped[UUID]
    subject_person_id: Mapped[UUID]
    state: Mapped[str] = mapped_column(String(32), default="UNPROVEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GateProfileSnapshot(Base):
    __tablename__ = "gate_profile_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "gate_assessment_id",
            "snapshot_version",
            name="uq_gate_profile_snapshot_version",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_assessments.id")
    )
    snapshot_version: Mapped[int] = mapped_column(BigInteger)
    organization_context_id: Mapped[UUID]
    subject_person_id: Mapped[UUID]
    source_flag_profile_id: Mapped[UUID]
    source_flag_profile_version: Mapped[int] = mapped_column(BigInteger)
    source_track_code: Mapped[str] = mapped_column(String(128))
    source_profile_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GateProfileSnapshotClaim(Base):
    __tablename__ = "gate_profile_snapshot_claims"
    __table_args__ = (
        UniqueConstraint(
            "gate_profile_snapshot_id",
            "source_claim_id",
            "source_claim_version",
            name="uq_gate_snapshot_claim_version",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_profile_snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_profile_snapshots.id")
    )
    source_claim_id: Mapped[UUID]
    source_claim_version: Mapped[int] = mapped_column(BigInteger)
    capability_id: Mapped[UUID]
    state: Mapped[str] = mapped_column(String(32))
    level: Mapped[str] = mapped_column(String(16))
    proven_scope: Mapped[str] = mapped_column(String(255))
    evidence_recency: Mapped[str] = mapped_column(String(255))
    confidence_in_claim: Mapped[str] = mapped_column(String(64))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    next_evidence_needed: Mapped[str] = mapped_column(Text)
    source_profile_update_case_id: Mapped[UUID]


class GateSnapshotPatternRef(Base):
    __tablename__ = "gate_snapshot_pattern_refs"
    __table_args__ = (
        UniqueConstraint(
            "gate_profile_snapshot_claim_id",
            "source_pattern_id",
            "source_pattern_version",
            "relationship",
            name="uq_gate_snapshot_pattern_ref",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_profile_snapshot_claim_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_profile_snapshot_claims.id")
    )
    source_pattern_id: Mapped[UUID]
    source_pattern_version: Mapped[int] = mapped_column(BigInteger)
    relationship: Mapped[str] = mapped_column(String(32))
    pattern_status: Mapped[str] = mapped_column(String(32))
    behaviour_code: Mapped[str] = mapped_column(String(120))
    scope: Mapped[str] = mapped_column(String(255))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GateSnapshotEvidenceRef(Base):
    __tablename__ = "gate_snapshot_evidence_refs"
    __table_args__ = (
        UniqueConstraint(
            "gate_snapshot_pattern_ref_id",
            "evidence_set_member_id",
            name="uq_gate_snapshot_evidence_ref",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_snapshot_pattern_ref_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_snapshot_pattern_refs.id")
    )
    evidence_set_member_id: Mapped[UUID]
    evidence_case_id: Mapped[UUID]
    interpretation_id: Mapped[UUID]
    interpretation_version: Mapped[int] = mapped_column(Integer)
    evidence_relationship: Mapped[str] = mapped_column(String(32))
    signal: Mapped[str] = mapped_column(String(32))
    scope: Mapped[str] = mapped_column(String(255))
    confidence: Mapped[str] = mapped_column(String(32))
    context_difficulty: Mapped[str] = mapped_column(String(255))
    prompt_contamination: Mapped[str] = mapped_column(String(255))
    source_independence_group: Mapped[str] = mapped_column(String(255))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_observation_id: Mapped[UUID]
    source_context: Mapped[str] = mapped_column(String(64))
    source_reference: Mapped[str] = mapped_column(String(255))
    observation_type: Mapped[str] = mapped_column(String(80))



class GateReview(Base):
    __tablename__ = "gate_reviews"
    __table_args__ = (
        UniqueConstraint(
            "organization_context_id",
            "opened_by",
            "open_idempotency_key",
            name="uq_gate_review_open_idempotency",
        ),
        UniqueConstraint(
            "gate_assessment_id",
            "gate_assessment_version",
            name="uq_gate_review_assessment_version",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_assessments.id")
    )
    gate_profile_snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_profile_snapshots.id"),
        unique=True,
    )
    gate_definition_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_definition_versions.id")
    )
    organization_context_id: Mapped[UUID]
    subject_person_id: Mapped[UUID]
    gate_assessment_version: Mapped[int] = mapped_column(BigInteger)
    opened_by: Mapped[UUID]
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    open_idempotency_key: Mapped[str] = mapped_column(String(160))
    trace_id: Mapped[str] = mapped_column(String(255))



class GateReviewDecision(Base):
    __tablename__ = "gate_review_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision_state IN ('PASS_CONFIRMED', 'FAIL')",
            name="ck_gate_review_decision_state",
        ),
        UniqueConstraint(
            "organization_context_id",
            "reviewer_id",
            "decision_idempotency_key",
            name="uq_gate_review_decision_idempotency",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_review_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_reviews.id"),
        unique=True,
    )
    gate_assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_assessments.id")
    )
    gate_profile_snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_profile_snapshots.id")
    )
    gate_profile_snapshot_version: Mapped[int] = mapped_column(BigInteger)
    gate_definition_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_definition_versions.id")
    )
    organization_context_id: Mapped[UUID]
    subject_person_id: Mapped[UUID]
    prior_assessment_version: Mapped[int] = mapped_column(BigInteger)
    resulting_assessment_version: Mapped[int] = mapped_column(BigInteger)
    decision_state: Mapped[str] = mapped_column(String(32))
    reviewer_id: Mapped[UUID]
    rationale: Mapped[str] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decision_idempotency_key: Mapped[str] = mapped_column(String(160))
    trace_id: Mapped[str] = mapped_column(String(255))



class GateRemediation(Base):
    __tablename__ = "gate_remediations"
    __table_args__ = (
        UniqueConstraint(
            "gate_assessment_id",
            "failure_assessment_version",
            name="uq_gate_remediation_failure_version",
        ),
        UniqueConstraint(
            "organization_context_id",
            "started_by",
            "start_idempotency_key",
            name="uq_gate_remediation_start_idempotency",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_assessments.id")
    )
    organization_context_id: Mapped[UUID]
    subject_person_id: Mapped[UUID]
    failure_assessment_version: Mapped[int] = mapped_column(BigInteger)
    remediation_assessment_version: Mapped[int] = mapped_column(BigInteger)
    started_by: Mapped[UUID]
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    start_idempotency_key: Mapped[str] = mapped_column(String(160))
    trace_id: Mapped[str] = mapped_column(String(255))


class GateReassessment(Base):
    __tablename__ = "gate_reassessments"
    __table_args__ = (
        UniqueConstraint(
            "organization_context_id",
            "opened_by",
            "open_idempotency_key",
            name="uq_gate_reassessment_open_idempotency",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_assessments.id")
    )
    gate_remediation_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_remediations.id"),
        unique=True,
    )
    gate_profile_snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_profile_snapshots.id"),
        unique=True,
    )
    gate_definition_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_definition_versions.id")
    )
    organization_context_id: Mapped[UUID]
    subject_person_id: Mapped[UUID]
    prior_assessment_version: Mapped[int] = mapped_column(BigInteger)
    reassessment_assessment_version: Mapped[int] = mapped_column(BigInteger)
    opened_by: Mapped[UUID]
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    open_idempotency_key: Mapped[str] = mapped_column(String(160))
    trace_id: Mapped[str] = mapped_column(String(255))


class GateReassessmentDecision(Base):
    __tablename__ = "gate_reassessment_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision_state IN ('PASS', 'FAIL')",
            name="ck_gate_reassessment_decision_state",
        ),
        UniqueConstraint(
            "organization_context_id",
            "reviewer_id",
            "decision_idempotency_key",
            name="uq_gate_reassessment_decision_idempotency",
        ),
        {"schema": "gate_assessment"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    gate_reassessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_reassessments.id"),
        unique=True,
    )
    gate_assessment_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_assessments.id")
    )
    gate_profile_snapshot_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_profile_snapshots.id")
    )
    gate_profile_snapshot_version: Mapped[int] = mapped_column(BigInteger)
    gate_definition_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("gate_assessment.gate_definition_versions.id")
    )
    organization_context_id: Mapped[UUID]
    subject_person_id: Mapped[UUID]
    prior_assessment_version: Mapped[int] = mapped_column(BigInteger)
    resulting_assessment_version: Mapped[int] = mapped_column(BigInteger)
    decision_state: Mapped[str] = mapped_column(String(32))
    reviewer_id: Mapped[UUID]
    rationale: Mapped[str] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decision_idempotency_key: Mapped[str] = mapped_column(String(160))
    trace_id: Mapped[str] = mapped_column(String(255))
