"""gate assessment persistence foundation

Revision ID: 0020
Revises: 0019
Create Date: 2026-10-07
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gate_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False),
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
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["gate_definition_version_id"],
            ["gate_assessment.gate_definition_versions.id"],
        ),
        sa.UniqueConstraint(
            "organization_context_id",
            "subject_person_id",
            "gate_definition_version_id",
            name="uq_gate_assessment_identity",
        ),
        schema="gate_assessment",
    )

    op.create_table(
        "gate_profile_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "gate_assessment_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("snapshot_version", sa.BigInteger(), nullable=False),
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
        sa.Column(
            "source_flag_profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("source_flag_profile_version", sa.BigInteger(), nullable=False),
        sa.Column("source_track_code", sa.String(128), nullable=False),
        sa.Column(
            "source_profile_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["gate_assessment_id"],
            ["gate_assessment.gate_assessments.id"],
        ),
        sa.UniqueConstraint(
            "gate_assessment_id",
            "snapshot_version",
            name="uq_gate_profile_snapshot_version",
        ),
        schema="gate_assessment",
    )

    op.create_table(
        "gate_profile_snapshot_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "gate_profile_snapshot_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "source_claim_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("source_claim_version", sa.BigInteger(), nullable=False),
        sa.Column(
            "capability_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("proven_scope", sa.String(255), nullable=False),
        sa.Column("evidence_recency", sa.String(255), nullable=False),
        sa.Column("confidence_in_claim", sa.String(64), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_evidence_needed", sa.Text(), nullable=False),
        sa.Column(
            "source_profile_update_case_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["gate_profile_snapshot_id"],
            ["gate_assessment.gate_profile_snapshots.id"],
        ),
        sa.UniqueConstraint(
            "gate_profile_snapshot_id",
            "source_claim_id",
            "source_claim_version",
            name="uq_gate_snapshot_claim_version",
        ),
        schema="gate_assessment",
    )

    op.create_table(
        "gate_snapshot_pattern_refs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "gate_profile_snapshot_claim_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "source_pattern_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("source_pattern_version", sa.BigInteger(), nullable=False),
        sa.Column("relationship", sa.String(32), nullable=False),
        sa.Column("pattern_status", sa.String(32), nullable=False),
        sa.Column("behaviour_code", sa.String(120), nullable=False),
        sa.Column("scope", sa.String(255), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["gate_profile_snapshot_claim_id"],
            ["gate_assessment.gate_profile_snapshot_claims.id"],
        ),
        sa.UniqueConstraint(
            "gate_profile_snapshot_claim_id",
            "source_pattern_id",
            "source_pattern_version",
            "relationship",
            name="uq_gate_snapshot_pattern_ref",
        ),
        schema="gate_assessment",
    )

    op.create_table(
        "gate_snapshot_evidence_refs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "gate_snapshot_pattern_ref_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "evidence_set_member_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "evidence_case_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "interpretation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("interpretation_version", sa.Integer(), nullable=False),
        sa.Column("evidence_relationship", sa.String(32), nullable=False),
        sa.Column("signal", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(255), nullable=False),
        sa.Column("confidence", sa.String(32), nullable=False),
        sa.Column("context_difficulty", sa.String(255), nullable=False),
        sa.Column("prompt_contamination", sa.String(255), nullable=False),
        sa.Column("source_independence_group", sa.String(255), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source_observation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("source_context", sa.String(64), nullable=False),
        sa.Column("source_reference", sa.String(255), nullable=False),
        sa.Column("observation_type", sa.String(80), nullable=False),
        sa.ForeignKeyConstraint(
            ["gate_snapshot_pattern_ref_id"],
            ["gate_assessment.gate_snapshot_pattern_refs.id"],
        ),
        sa.UniqueConstraint(
            "gate_snapshot_pattern_ref_id",
            "evidence_set_member_id",
            name="uq_gate_snapshot_evidence_ref",
        ),
        schema="gate_assessment",
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION gate_assessment.reject_profile_snapshot_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS 'BEGIN
                RAISE EXCEPTION
                    ''gate profile snapshot rows are immutable; create a new snapshot instead'';
            END;';
            """
        )
    )
    for table_name in (
        "gate_profile_snapshots",
        "gate_profile_snapshot_claims",
        "gate_snapshot_pattern_refs",
        "gate_snapshot_evidence_refs",
    ):
        op.execute(
            sa.text(
                f"""
                CREATE TRIGGER trg_{table_name}_immutable
                BEFORE UPDATE OR DELETE ON gate_assessment.{table_name}
                FOR EACH ROW
                EXECUTE FUNCTION gate_assessment.reject_profile_snapshot_mutation()
                """
            )
        )


def downgrade() -> None:
    op.drop_table("gate_snapshot_evidence_refs", schema="gate_assessment")
    op.drop_table("gate_snapshot_pattern_refs", schema="gate_assessment")
    op.drop_table("gate_profile_snapshot_claims", schema="gate_assessment")
    op.drop_table("gate_profile_snapshots", schema="gate_assessment")
    op.drop_table("gate_assessments", schema="gate_assessment")
    op.execute(
        sa.text(
            "DROP FUNCTION IF EXISTS "
            "gate_assessment.reject_profile_snapshot_mutation()"
        )
    )
