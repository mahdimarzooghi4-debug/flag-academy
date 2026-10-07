"""governed AI dataset builder foundation

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-07
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "datasets",
        sa.Column(
            "organization_context_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        schema="ai_control_plane",
    )
    op.create_unique_constraint(
        "uq_ai_dataset_scope_name_purpose",
        "datasets",
        ["organization_context_id", "name", "purpose"],
        schema="ai_control_plane",
    )

    op.add_column(
        "dataset_versions",
        sa.Column(
            "parent_dataset_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        schema="ai_control_plane",
    )
    op.create_foreign_key(
        "fk_ai_dataset_version_parent",
        "dataset_versions",
        "dataset_versions",
        ["parent_dataset_version_id"],
        ["id"],
        source_schema="ai_control_plane",
        referent_schema="ai_control_plane",
    )

    op.create_table(
        "learning_source_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("source_policy_key", sa.String(160), nullable=False),
        sa.Column("source_policy_version", sa.String(160), nullable=False),
        sa.Column("source_type", sa.String(160), nullable=False),
        sa.Column("source_reference", sa.String(255), nullable=False),
        sa.Column("source_version", sa.String(160), nullable=True),
        sa.Column("source_payload_digest", sa.String(64), nullable=False),
        sa.Column("approval_reference", sa.String(255), nullable=False),
        sa.Column("data_classification", sa.String(64), nullable=False),
        sa.Column("provenance_digest", sa.String(64), nullable=False),
        sa.Column("approved_by_type", sa.String(16), nullable=False),
        sa.Column("approved_by_reference", sa.String(255), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["ai_control_plane.datasets.id"],
        ),
        sa.UniqueConstraint(
            "dataset_id",
            "approval_reference",
            name="uq_ai_learning_approval_reference",
        ),
        sa.UniqueConstraint(
            "dataset_id",
            "provenance_digest",
            name="uq_ai_learning_approval_provenance",
        ),
        sa.CheckConstraint(
            "source_payload_digest ~ '^[0-9a-f]{64}$'",
            name="ck_ai_learning_approval_payload_sha256",
        ),
        sa.CheckConstraint(
            "provenance_digest ~ '^[0-9a-f]{64}$'",
            name="ck_ai_learning_approval_provenance_sha256",
        ),
        sa.CheckConstraint(
            "approved_by_type IN ('PERSON', 'SYSTEM')",
            name="ck_ai_learning_approval_actor_type",
        ),
        schema="ai_control_plane",
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_learning_source_approvals_immutable
            BEFORE UPDATE OR DELETE
            ON ai_control_plane.learning_source_approvals
            FOR EACH ROW
            EXECUTE FUNCTION ai_control_plane.reject_history_mutation()
            """
        )
    )

    op.add_column(
        "dataset_items",
        sa.Column(
            "learning_source_approval_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        schema="ai_control_plane",
    )
    op.add_column(
        "dataset_items",
        sa.Column(
            "source_payload_digest",
            sa.String(64),
            nullable=False,
        ),
        schema="ai_control_plane",
    )
    op.create_foreign_key(
        "fk_ai_dataset_item_learning_approval",
        "dataset_items",
        "learning_source_approvals",
        ["learning_source_approval_id"],
        ["id"],
        source_schema="ai_control_plane",
        referent_schema="ai_control_plane",
    )
    op.create_unique_constraint(
        "uq_ai_dataset_item_learning_approval",
        "dataset_items",
        ["learning_source_approval_id"],
        schema="ai_control_plane",
    )
    op.create_check_constraint(
        "ck_ai_dataset_item_payload_sha256",
        "dataset_items",
        "source_payload_digest ~ '^[0-9a-f]{64}$'",
        schema="ai_control_plane",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_ai_dataset_item_payload_sha256",
        "dataset_items",
        schema="ai_control_plane",
        type_="check",
    )
    op.drop_constraint(
        "uq_ai_dataset_item_learning_approval",
        "dataset_items",
        schema="ai_control_plane",
        type_="unique",
    )
    op.drop_constraint(
        "fk_ai_dataset_item_learning_approval",
        "dataset_items",
        schema="ai_control_plane",
        type_="foreignkey",
    )
    op.drop_column(
        "dataset_items",
        "source_payload_digest",
        schema="ai_control_plane",
    )
    op.drop_column(
        "dataset_items",
        "learning_source_approval_id",
        schema="ai_control_plane",
    )

    op.execute(
        sa.text(
            """
            DROP TRIGGER IF EXISTS trg_learning_source_approvals_immutable
            ON ai_control_plane.learning_source_approvals
            """
        )
    )
    op.drop_table(
        "learning_source_approvals",
        schema="ai_control_plane",
    )

    op.drop_constraint(
        "fk_ai_dataset_version_parent",
        "dataset_versions",
        schema="ai_control_plane",
        type_="foreignkey",
    )
    op.drop_column(
        "dataset_versions",
        "parent_dataset_version_id",
        schema="ai_control_plane",
    )

    op.drop_constraint(
        "uq_ai_dataset_scope_name_purpose",
        "datasets",
        schema="ai_control_plane",
        type_="unique",
    )
    op.drop_column(
        "datasets",
        "organization_context_id",
        schema="ai_control_plane",
    )
