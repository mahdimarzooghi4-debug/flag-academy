"""gate review opening audit foundation

Revision ID: 0021
Revises: 0020
Create Date: 2026-10-07
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gate_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "gate_assessment_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "gate_profile_snapshot_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "gate_definition_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "organization_context_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "subject_person_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("gate_assessment_version", sa.BigInteger(), nullable=False),
        sa.Column(
            "opened_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open_idempotency_key", sa.String(160), nullable=False),
        sa.Column("trace_id", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(
            ["gate_assessment_id"],
            ["gate_assessment.gate_assessments.id"],
        ),
        sa.ForeignKeyConstraint(
            ["gate_profile_snapshot_id"],
            ["gate_assessment.gate_profile_snapshots.id"],
        ),
        sa.ForeignKeyConstraint(
            ["gate_definition_version_id"],
            ["gate_assessment.gate_definition_versions.id"],
        ),
        sa.UniqueConstraint(
            "organization_context_id",
            "opened_by",
            "open_idempotency_key",
            name="uq_gate_review_open_idempotency",
        ),
        sa.UniqueConstraint(
            "gate_assessment_id",
            "gate_assessment_version",
            name="uq_gate_review_assessment_version",
        ),
        schema="gate_assessment",
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION gate_assessment.reject_gate_review_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS 'BEGIN
                RAISE EXCEPTION
                    ''gate review opening rows are immutable'';
            END;';
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_gate_reviews_immutable
            BEFORE UPDATE OR DELETE ON gate_assessment.gate_reviews
            FOR EACH ROW
            EXECUTE FUNCTION gate_assessment.reject_gate_review_mutation()
            """
        )
    )


def downgrade() -> None:
    op.drop_table("gate_reviews", schema="gate_assessment")
    op.execute(
        sa.text(
            "DROP FUNCTION IF EXISTS "
            "gate_assessment.reject_gate_review_mutation()"
        )
    )
