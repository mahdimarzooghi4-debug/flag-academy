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


class AIDataset(Base):
    __tablename__ = "datasets"
    __table_args__ = {"schema": "ai_control_plane"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255))
    purpose: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIDatasetVersion(Base):
    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "version_number",
            name="uq_ai_dataset_version_number",
        ),
        UniqueConstraint(
            "dataset_id",
            "dataset_digest",
            name="uq_ai_dataset_version_digest",
        ),
        CheckConstraint(
            "dataset_digest ~ '^[0-9a-f]{64}$'",
            name="ck_ai_dataset_version_digest_sha256",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dataset_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.datasets.id")
    )
    version_number: Mapped[int] = mapped_column(BigInteger)
    source_policy_key: Mapped[str] = mapped_column(String(160))
    source_policy_version: Mapped[str] = mapped_column(String(160))
    dataset_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIDatasetItem(Base):
    __tablename__ = "dataset_items"
    __table_args__ = (
        UniqueConstraint(
            "dataset_version_id",
            "position",
            name="uq_ai_dataset_item_position",
        ),
        UniqueConstraint(
            "dataset_version_id",
            "provenance_digest",
            name="uq_ai_dataset_item_provenance",
        ),
        CheckConstraint(
            "provenance_digest ~ '^[0-9a-f]{64}$'",
            name="ck_ai_dataset_item_provenance_sha256",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dataset_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.dataset_versions.id")
    )
    position: Mapped[int] = mapped_column(Integer)
    source_type: Mapped[str] = mapped_column(String(160))
    source_reference: Mapped[str] = mapped_column(String(255))
    source_version: Mapped[str | None] = mapped_column(String(160), nullable=True)
    approval_reference: Mapped[str] = mapped_column(String(255))
    data_classification: Mapped[str] = mapped_column(String(64))
    provenance_digest: Mapped[str] = mapped_column(String(64))


class AITrainingRun(Base):
    __tablename__ = "training_runs"
    __table_args__ = (
        CheckConstraint(
            "requested_by_type IN ('PERSON', 'SYSTEM')",
            name="ck_ai_training_requested_by_type",
        ),
        CheckConstraint(
            "training_recipe_digest ~ '^[0-9a-f]{64}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dataset_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.dataset_versions.id")
    )
    model_family: Mapped[str] = mapped_column(String(255))
    training_recipe_digest: Mapped[str] = mapped_column(String(64))
    requested_by_type: Mapped[str] = mapped_column(String(16))
    requested_by_reference: Mapped[str] = mapped_column(String(255))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AITrainingRunState(Base):
    __tablename__ = "training_run_states"
    __table_args__ = (
        UniqueConstraint(
            "training_run_id",
            "sequence",
            name="uq_ai_training_run_state_sequence",
        ),
        CheckConstraint(
            "state IN ('REQUESTED', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_ai_training_run_state",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    training_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.training_runs.id")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(32))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(160), nullable=True)


class AIModelArtifact(Base):
    __tablename__ = "model_artifacts"
    __table_args__ = (
        CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    training_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.training_runs.id"),
        unique=True,
    )
    artifact_format: Mapped[str] = mapped_column(String(160))
    artifact_reference: Mapped[str] = mapped_column(String(512))
    content_sha256: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint(
            "model_family",
            "semantic_version",
            name="uq_ai_model_family_semantic_version",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_artifact_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.model_artifacts.id"),
        unique=True,
    )
    training_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.training_runs.id"),
        unique=True,
    )
    dataset_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.dataset_versions.id")
    )
    model_family: Mapped[str] = mapped_column(String(255))
    semantic_version: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIEvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        CheckConstraint(
            "requested_by_type IN ('PERSON', 'SYSTEM')",
            name="ck_ai_evaluation_requested_by_type",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.model_versions.id")
    )
    evaluation_dataset_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.dataset_versions.id")
    )
    evaluation_policy_key: Mapped[str] = mapped_column(String(160))
    evaluation_policy_version: Mapped[str] = mapped_column(String(160))
    requested_by_type: Mapped[str] = mapped_column(String(16))
    requested_by_reference: Mapped[str] = mapped_column(String(255))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIEvaluationRunState(Base):
    __tablename__ = "evaluation_run_states"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_run_id",
            "sequence",
            name="uq_ai_evaluation_run_state_sequence",
        ),
        CheckConstraint(
            "state IN ('REQUESTED', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_ai_evaluation_run_state",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    evaluation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.evaluation_runs.id")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(32))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(160), nullable=True)


class AIEvaluationResult(Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (
        CheckConstraint(
            "metrics_digest ~ '^[0-9a-f]{64}$'",
            name="ck_ai_evaluation_metrics_sha256",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    evaluation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.evaluation_runs.id"),
        unique=True,
    )
    metrics_artifact_reference: Mapped[str] = mapped_column(String(512))
    metrics_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIModelPromotionDecision(Base):
    __tablename__ = "model_promotion_decisions"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_run_id",
            "target_environment",
            name="uq_ai_model_promotion_eval_target",
        ),
        CheckConstraint(
            "decision IN ('APPROVED', 'REJECTED')",
            name="ck_ai_model_promotion_decision",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.model_versions.id")
    )
    evaluation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.evaluation_runs.id")
    )
    reviewer_id: Mapped[UUID]
    rationale: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(32))
    target_environment: Mapped[str] = mapped_column(String(64))
    prior_active_model_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ai_control_plane.model_versions.id"),
        nullable=True,
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
",
            name="ck_ai_training_recipe_sha256",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dataset_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.dataset_versions.id")
    )
    model_family: Mapped[str] = mapped_column(String(255))
    training_recipe_digest: Mapped[str] = mapped_column(String(64))
    requested_by_type: Mapped[str] = mapped_column(String(16))
    requested_by_reference: Mapped[str] = mapped_column(String(255))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AITrainingRunState(Base):
    __tablename__ = "training_run_states"
    __table_args__ = (
        UniqueConstraint(
            "training_run_id",
            "sequence",
            name="uq_ai_training_run_state_sequence",
        ),
        CheckConstraint(
            "state IN ('REQUESTED', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_ai_training_run_state",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    training_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.training_runs.id")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(32))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(160), nullable=True)


class AIModelArtifact(Base):
    __tablename__ = "model_artifacts"
    __table_args__ = (
        CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_ai_model_artifact_sha256",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    training_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.training_runs.id"),
        unique=True,
    )
    artifact_format: Mapped[str] = mapped_column(String(160))
    artifact_reference: Mapped[str] = mapped_column(String(512))
    content_sha256: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint(
            "model_family",
            "semantic_version",
            name="uq_ai_model_family_semantic_version",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_artifact_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.model_artifacts.id"),
        unique=True,
    )
    training_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.training_runs.id"),
        unique=True,
    )
    dataset_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.dataset_versions.id")
    )
    model_family: Mapped[str] = mapped_column(String(255))
    semantic_version: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIEvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = {"schema": "ai_control_plane"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.model_versions.id")
    )
    evaluation_dataset_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.dataset_versions.id")
    )
    evaluation_policy_key: Mapped[str] = mapped_column(String(160))
    evaluation_policy_version: Mapped[str] = mapped_column(String(160))
    requested_by_type: Mapped[str] = mapped_column(String(16))
    requested_by_reference: Mapped[str] = mapped_column(String(255))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIEvaluationRunState(Base):
    __tablename__ = "evaluation_run_states"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_run_id",
            "sequence",
            name="uq_ai_evaluation_run_state_sequence",
        ),
        CheckConstraint(
            "state IN ('REQUESTED', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_ai_evaluation_run_state",
        ),
        CheckConstraint(
            "requested_by_type IS NULL OR requested_by_type IN ('PERSON', 'SYSTEM')",
            name="ck_ai_evaluation_state_requested_by_type",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    evaluation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.evaluation_runs.id")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(32))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(160), nullable=True)
    requested_by_type: Mapped[str | None] = mapped_column(String(16), nullable=True)


class AIEvaluationResult(Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (
        CheckConstraint(
            "metrics_digest ~ '^[0-9a-f]{64}$'",
            name="ck_ai_evaluation_metrics_sha256",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    evaluation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.evaluation_runs.id"),
        unique=True,
    )
    metrics_artifact_reference: Mapped[str] = mapped_column(String(512))
    metrics_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIModelPromotionDecision(Base):
    __tablename__ = "model_promotion_decisions"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_run_id",
            "target_environment",
            name="uq_ai_model_promotion_eval_target",
        ),
        CheckConstraint(
            "decision IN ('APPROVED', 'REJECTED')",
            name="ck_ai_model_promotion_decision",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.model_versions.id")
    )
    evaluation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.evaluation_runs.id")
    )
    reviewer_id: Mapped[UUID]
    rationale: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(32))
    target_environment: Mapped[str] = mapped_column(String(64))
    prior_active_model_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ai_control_plane.model_versions.id"),
        nullable=True,
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
",
            name="ck_ai_model_artifact_sha256",
        ),
        CheckConstraint(
            "byte_size >= 0",
            name="ck_ai_model_artifact_byte_size",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    training_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.training_runs.id"),
        unique=True,
    )
    artifact_format: Mapped[str] = mapped_column(String(160))
    artifact_reference: Mapped[str] = mapped_column(String(512))
    content_sha256: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint(
            "model_family",
            "semantic_version",
            name="uq_ai_model_family_semantic_version",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_artifact_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.model_artifacts.id"),
        unique=True,
    )
    training_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.training_runs.id"),
        unique=True,
    )
    dataset_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.dataset_versions.id")
    )
    model_family: Mapped[str] = mapped_column(String(255))
    semantic_version: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIEvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        CheckConstraint(
            "requested_by_type IN ('PERSON', 'SYSTEM')",
            name="ck_ai_evaluation_requested_by_type",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.model_versions.id")
    )
    evaluation_dataset_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.dataset_versions.id")
    )
    evaluation_policy_key: Mapped[str] = mapped_column(String(160))
    evaluation_policy_version: Mapped[str] = mapped_column(String(160))
    requested_by_type: Mapped[str] = mapped_column(String(16))
    requested_by_reference: Mapped[str] = mapped_column(String(255))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIEvaluationRunState(Base):
    __tablename__ = "evaluation_run_states"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_run_id",
            "sequence",
            name="uq_ai_evaluation_run_state_sequence",
        ),
        CheckConstraint(
            "state IN ('REQUESTED', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_ai_evaluation_run_state",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    evaluation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.evaluation_runs.id")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(32))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(160), nullable=True)


class AIEvaluationResult(Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (
        CheckConstraint(
            "metrics_digest ~ '^[0-9a-f]{64}$'",
            name="ck_ai_evaluation_metrics_sha256",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    evaluation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.evaluation_runs.id"),
        unique=True,
    )
    metrics_artifact_reference: Mapped[str] = mapped_column(String(512))
    metrics_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIModelPromotionDecision(Base):
    __tablename__ = "model_promotion_decisions"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_run_id",
            "target_environment",
            name="uq_ai_model_promotion_eval_target",
        ),
        CheckConstraint(
            "decision IN ('APPROVED', 'REJECTED')",
            name="ck_ai_model_promotion_decision",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.model_versions.id")
    )
    evaluation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.evaluation_runs.id")
    )
    reviewer_id: Mapped[UUID]
    rationale: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(32))
    target_environment: Mapped[str] = mapped_column(String(64))
    prior_active_model_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ai_control_plane.model_versions.id"),
        nullable=True,
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
",
            name="ck_ai_training_recipe_sha256",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dataset_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.dataset_versions.id")
    )
    model_family: Mapped[str] = mapped_column(String(255))
    training_recipe_digest: Mapped[str] = mapped_column(String(64))
    requested_by_type: Mapped[str] = mapped_column(String(16))
    requested_by_reference: Mapped[str] = mapped_column(String(255))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AITrainingRunState(Base):
    __tablename__ = "training_run_states"
    __table_args__ = (
        UniqueConstraint(
            "training_run_id",
            "sequence",
            name="uq_ai_training_run_state_sequence",
        ),
        CheckConstraint(
            "state IN ('REQUESTED', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_ai_training_run_state",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    training_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.training_runs.id")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(32))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(160), nullable=True)


class AIModelArtifact(Base):
    __tablename__ = "model_artifacts"
    __table_args__ = (
        CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_ai_model_artifact_sha256",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    training_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.training_runs.id"),
        unique=True,
    )
    artifact_format: Mapped[str] = mapped_column(String(160))
    artifact_reference: Mapped[str] = mapped_column(String(512))
    content_sha256: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint(
            "model_family",
            "semantic_version",
            name="uq_ai_model_family_semantic_version",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_artifact_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.model_artifacts.id"),
        unique=True,
    )
    training_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.training_runs.id"),
        unique=True,
    )
    dataset_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.dataset_versions.id")
    )
    model_family: Mapped[str] = mapped_column(String(255))
    semantic_version: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIEvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = {"schema": "ai_control_plane"}

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.model_versions.id")
    )
    evaluation_dataset_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.dataset_versions.id")
    )
    evaluation_policy_key: Mapped[str] = mapped_column(String(160))
    evaluation_policy_version: Mapped[str] = mapped_column(String(160))
    requested_by_type: Mapped[str] = mapped_column(String(16))
    requested_by_reference: Mapped[str] = mapped_column(String(255))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIEvaluationRunState(Base):
    __tablename__ = "evaluation_run_states"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_run_id",
            "sequence",
            name="uq_ai_evaluation_run_state_sequence",
        ),
        CheckConstraint(
            "state IN ('REQUESTED', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_ai_evaluation_run_state",
        ),
        CheckConstraint(
            "requested_by_type IS NULL OR requested_by_type IN ('PERSON', 'SYSTEM')",
            name="ck_ai_evaluation_state_requested_by_type",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    evaluation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.evaluation_runs.id")
    )
    sequence: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(32))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(160), nullable=True)
    requested_by_type: Mapped[str | None] = mapped_column(String(16), nullable=True)


class AIEvaluationResult(Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (
        CheckConstraint(
            "metrics_digest ~ '^[0-9a-f]{64}$'",
            name="ck_ai_evaluation_metrics_sha256",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    evaluation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.evaluation_runs.id"),
        unique=True,
    )
    metrics_artifact_reference: Mapped[str] = mapped_column(String(512))
    metrics_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AIModelPromotionDecision(Base):
    __tablename__ = "model_promotion_decisions"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_run_id",
            "target_environment",
            name="uq_ai_model_promotion_eval_target",
        ),
        CheckConstraint(
            "decision IN ('APPROVED', 'REJECTED')",
            name="ck_ai_model_promotion_decision",
        ),
        {"schema": "ai_control_plane"},
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    model_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.model_versions.id")
    )
    evaluation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_control_plane.evaluation_runs.id")
    )
    reviewer_id: Mapped[UUID]
    rationale: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(32))
    target_environment: Mapped[str] = mapped_column(String(64))
    prior_active_model_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ai_control_plane.model_versions.id"),
        nullable=True,
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
