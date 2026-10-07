"""gate human decision audit

Revision ID: 0022
Revises: 0021
Create Date: 2026-10-07
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gate_review_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "gate_review_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "gate_assessment_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "gate_profile_snapshot_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "gate_profile_snapshot_version",
            sa.BigInteger(),
            nullable=False,
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
        sa.Column("prior_assessment_version", sa.BigInteger(), nullable=False),
        sa.Column("resulting_assessment_version", sa.BigInteger(), nullable=False),
        sa.Column("decision_state", sa.String(32), nullable=False),
        sa.Column(
            "reviewer_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision_idempotency_key", sa.String(160), nullable=False),
        sa.Column("trace_id", sa.String(255), nullable=False),
        sa.CheckConstraint(
            "decision_state IN ('PASS_CONFIRMED', 'FAIL')",
            name="ck_gate_review_decision_state",
        ),
        sa.ForeignKeyConstraint(
            ["gate_review_id"],
            ["gate_assessment.gate_reviews.id"],
        ),
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
            "reviewer_id",
            "decision_idempotency_key",
            name="uq_gate_review_decision_idempotency",
        ),
        schema="gate_assessment",
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION gate_assessment.reject_gate_decision_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS 'BEGIN
                RAISE EXCEPTION
                    ''gate review decision rows are immutable'';
            END;';
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_gate_review_decisions_immutable
            BEFORE UPDATE OR DELETE ON gate_assessment.gate_review_decisions
            FOR EACH ROW
            EXECUTE FUNCTION gate_assessment.reject_gate_decision_mutation()
            """
        )
    )


def downgrade() -> None:
    op.drop_table("gate_review_decisions", schema="gate_assessment")
    op.execute(
        sa.text(
            "DROP FUNCTION IF EXISTS "
            "gate_assessment.reject_gate_decision_mutation()"
        )
    )
