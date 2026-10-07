"""gate remediation and reassessment foundation

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-07
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gate_remediations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "gate_assessment_id",
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
        sa.Column("failure_assessment_version", sa.BigInteger(), nullable=False),
        sa.Column(
            "remediation_assessment_version",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column("started_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("start_idempotency_key", sa.String(160), nullable=False),
        sa.Column("trace_id", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(
            ["gate_assessment_id"],
            ["gate_assessment.gate_assessments.id"],
        ),
        sa.UniqueConstraint(
            "gate_assessment_id",
            "failure_assessment_version",
            name="uq_gate_remediation_failure_version",
        ),
        sa.UniqueConstraint(
            "organization_context_id",
            "started_by",
            "start_idempotency_key",
            name="uq_gate_remediation_start_idempotency",
        ),
        schema="gate_assessment",
    )

    op.create_table(
        "gate_reassessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "gate_assessment_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "gate_remediation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
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
        sa.Column("prior_assessment_version", sa.BigInteger(), nullable=False),
        sa.Column(
            "reassessment_assessment_version",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column("opened_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open_idempotency_key", sa.String(160), nullable=False),
        sa.Column("trace_id", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(
            ["gate_assessment_id"],
            ["gate_assessment.gate_assessments.id"],
        ),
        sa.ForeignKeyConstraint(
            ["gate_remediation_id"],
            ["gate_assessment.gate_remediations.id"],
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
            name="uq_gate_reassessment_open_idempotency",
        ),
        schema="gate_assessment",
    )

    op.create_table(
        "gate_reassessment_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "gate_reassessment_id",
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
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision_idempotency_key", sa.String(160), nullable=False),
        sa.Column("trace_id", sa.String(255), nullable=False),
        sa.CheckConstraint(
            "decision_state IN ('PASS', 'FAIL')",
            name="ck_gate_reassessment_decision_state",
        ),
        sa.ForeignKeyConstraint(
            ["gate_reassessment_id"],
            ["gate_assessment.gate_reassessments.id"],
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
            name="uq_gate_reassessment_decision_idempotency",
        ),
        schema="gate_assessment",
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION gate_assessment.reject_recovery_history_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS 'BEGIN
                RAISE EXCEPTION
                    ''gate remediation/reassessment history is immutable'';
            END;';
            """
        )
    )
    for table_name in (
        "gate_remediations",
        "gate_reassessments",
        "gate_reassessment_decisions",
    ):
        op.execute(
            sa.text(
                f"""
                CREATE TRIGGER trg_{table_name}_immutable
                BEFORE UPDATE OR DELETE ON gate_assessment.{table_name}
                FOR EACH ROW
                EXECUTE FUNCTION gate_assessment.reject_recovery_history_mutation()
                """
            )
        )


def downgrade() -> None:
    op.drop_table("gate_reassessment_decisions", schema="gate_assessment")
    op.drop_table("gate_reassessments", schema="gate_assessment")
    op.drop_table("gate_remediations", schema="gate_assessment")
    op.execute(
        sa.text(
            "DROP FUNCTION IF EXISTS "
            "gate_assessment.reject_recovery_history_mutation()"
        )
    )
