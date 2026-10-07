"""Parcham AI control-plane registry foundation

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-07
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS ai_control_plane"))

    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("purpose", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="ai_control_plane",
    )

    op.create_table(
        "dataset_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.BigInteger(), nullable=False),
        sa.Column("source_policy_key", sa.String(160), nullable=False),
        sa.Column("source_policy_version", sa.String(160), nullable=False),
        sa.Column("dataset_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["ai_control_plane.datasets.id"],
        ),
        sa.UniqueConstraint(
            "dataset_id",
            "version_number",
            name="uq_ai_dataset_version_number",
        ),
        sa.UniqueConstraint(
            "dataset_id",
            "dataset_digest",
            name="uq_ai_dataset_version_digest",
        ),
        sa.CheckConstraint(
            "dataset_digest ~ '^[0-9a-f]{64}$'",
            name="ck_ai_dataset_version_digest_sha256",
        ),
        schema="ai_control_plane",
    )

    op.create_table(
        "dataset_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(160), nullable=False),
        sa.Column("source_reference", sa.String(255), nullable=False),
        sa.Column("source_version", sa.String(160), nullable=True),
        sa.Column("approval_reference", sa.String(255), nullable=False),
        sa.Column("data_classification", sa.String(64), nullable=False),
        sa.Column("provenance_digest", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["ai_control_plane.dataset_versions.id"],
        ),
        sa.UniqueConstraint(
            "dataset_version_id",
            "position",
            name="uq_ai_dataset_item_position",
        ),
        sa.UniqueConstraint(
            "dataset_version_id",
            "provenance_digest",
            name="uq_ai_dataset_item_provenance",
        ),
        sa.CheckConstraint(
            "provenance_digest ~ '^[0-9a-f]{64}$'",
            name="ck_ai_dataset_item_provenance_sha256",
        ),
        schema="ai_control_plane",
    )

    op.create_table(
        "training_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("model_family", sa.String(255), nullable=False),
        sa.Column("training_recipe_digest", sa.String(64), nullable=False),
        sa.Column("requested_by_type", sa.String(16), nullable=False),
        sa.Column("requested_by_reference", sa.String(255), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["ai_control_plane.dataset_versions.id"],
        ),
        sa.CheckConstraint(
            "requested_by_type IN ('PERSON', 'SYSTEM')",
            name="ck_ai_training_requested_by_type",
        ),
        sa.CheckConstraint(
            "training_recipe_digest ~ '^[0-9a-f]{64}$'",
            name="ck_ai_training_recipe_sha256",
        ),
        schema="ai_control_plane",
    )

    op.create_table(
        "training_run_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "training_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_code", sa.String(160), nullable=True),
        sa.ForeignKeyConstraint(
            ["training_run_id"],
            ["ai_control_plane.training_runs.id"],
        ),
        sa.UniqueConstraint(
            "training_run_id",
            "sequence",
            name="uq_ai_training_run_state_sequence",
        ),
        sa.CheckConstraint(
            "state IN ('REQUESTED', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_ai_training_run_state",
        ),
        schema="ai_control_plane",
    )

    op.create_table(
        "model_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "training_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("artifact_format", sa.String(160), nullable=False),
        sa.Column("artifact_reference", sa.String(512), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["training_run_id"],
            ["ai_control_plane.training_runs.id"],
        ),
        sa.CheckConstraint(
            "content_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_ai_model_artifact_sha256",
        ),
        sa.CheckConstraint(
            "byte_size >= 0",
            name="ck_ai_model_artifact_byte_size",
        ),
        schema="ai_control_plane",
    )

    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_artifact_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "training_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "dataset_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("model_family", sa.String(255), nullable=False),
        sa.Column("semantic_version", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["model_artifact_id"],
            ["ai_control_plane.model_artifacts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["training_run_id"],
            ["ai_control_plane.training_runs.id"],
        ),
        sa.ForeignKeyConstraint(
            ["dataset_version_id"],
            ["ai_control_plane.dataset_versions.id"],
        ),
        sa.UniqueConstraint(
            "model_family",
            "semantic_version",
            name="uq_ai_model_family_semantic_version",
        ),
        schema="ai_control_plane",
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "evaluation_dataset_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("evaluation_policy_key", sa.String(160), nullable=False),
        sa.Column("evaluation_policy_version", sa.String(160), nullable=False),
        sa.Column("requested_by_type", sa.String(16), nullable=False),
        sa.Column("requested_by_reference", sa.String(255), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["ai_control_plane.model_versions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_dataset_version_id"],
            ["ai_control_plane.dataset_versions.id"],
        ),
        sa.CheckConstraint(
            "requested_by_type IN ('PERSON', 'SYSTEM')",
            name="ck_ai_evaluation_requested_by_type",
        ),
        schema="ai_control_plane",
    )

    op.create_table(
        "evaluation_run_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "evaluation_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_code", sa.String(160), nullable=True),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"],
            ["ai_control_plane.evaluation_runs.id"],
        ),
        sa.UniqueConstraint(
            "evaluation_run_id",
            "sequence",
            name="uq_ai_evaluation_run_state_sequence",
        ),
        sa.CheckConstraint(
            "state IN ('REQUESTED', 'RUNNING', 'SUCCEEDED', 'FAILED')",
            name="ck_ai_evaluation_run_state",
        ),
        schema="ai_control_plane",
    )

    op.create_table(
        "evaluation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "evaluation_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("metrics_artifact_reference", sa.String(512), nullable=False),
        sa.Column("metrics_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"],
            ["ai_control_plane.evaluation_runs.id"],
        ),
        sa.CheckConstraint(
            "metrics_digest ~ '^[0-9a-f]{64}$'",
            name="ck_ai_evaluation_metrics_sha256",
        ),
        schema="ai_control_plane",
    )

    op.create_table(
        "model_promotion_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "evaluation_run_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("target_environment", sa.String(64), nullable=False),
        sa.Column(
            "prior_active_model_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["ai_control_plane.model_versions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["evaluation_run_id"],
            ["ai_control_plane.evaluation_runs.id"],
        ),
        sa.ForeignKeyConstraint(
            ["prior_active_model_version_id"],
            ["ai_control_plane.model_versions.id"],
        ),
        sa.UniqueConstraint(
            "evaluation_run_id",
            "target_environment",
            name="uq_ai_model_promotion_eval_target",
        ),
        sa.CheckConstraint(
            "decision IN ('APPROVED', 'REJECTED')",
            name="ck_ai_model_promotion_decision",
        ),
        schema="ai_control_plane",
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION ai_control_plane.reject_history_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS 'BEGIN
                RAISE EXCEPTION
                    ''AI control-plane records are immutable'';
            END;';
            """
        )
    )

    for table_name in (
        "datasets",
        "dataset_versions",
        "dataset_items",
        "training_runs",
        "training_run_states",
        "model_artifacts",
        "model_versions",
        "evaluation_runs",
        "evaluation_run_states",
        "evaluation_results",
        "model_promotion_decisions",
    ):
        op.execute(
            sa.text(
                f"""
                CREATE TRIGGER trg_{table_name}_immutable
                BEFORE UPDATE OR DELETE ON ai_control_plane.{table_name}
                FOR EACH ROW
                EXECUTE FUNCTION ai_control_plane.reject_history_mutation()
                """
            )
        )


def downgrade() -> None:
    for table_name in (
        "model_promotion_decisions",
        "evaluation_results",
        "evaluation_run_states",
        "evaluation_runs",
        "model_versions",
        "model_artifacts",
        "training_run_states",
        "training_runs",
        "dataset_items",
        "dataset_versions",
        "datasets",
    ):
        op.drop_table(table_name, schema="ai_control_plane")

    op.execute(
        sa.text(
            "DROP FUNCTION IF EXISTS ai_control_plane.reject_history_mutation()"
        )
    )
    op.execute(sa.text("DROP SCHEMA IF EXISTS ai_control_plane"))
