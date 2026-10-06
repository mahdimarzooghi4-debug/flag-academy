"""pattern engine foundation

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-06
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS "patterns"'))

    op.create_table(
        "evidence_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evidence_set_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "evidence_set_key",
            "version_number",
            name="uq_pattern_evidence_set_key_version",
        ),
        sa.UniqueConstraint(
            "organization_context_id",
            "created_by",
            "idempotency_key",
            name="uq_pattern_evidence_set_idempotency",
        ),
        schema="patterns",
    )
    op.create_index(
        "ix_pattern_evidence_set_subject",
        "evidence_sets",
        ["organization_context_id", "subject_person_id", "created_at"],
        schema="patterns",
    )

    op.create_table(
        "evidence_set_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evidence_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interpretation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interpretation_version", sa.Integer(), nullable=False),
        sa.Column("behaviour_code", sa.String(120), nullable=False),
        sa.Column("signal", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(255), nullable=False),
        sa.Column("confidence", sa.String(32), nullable=False),
        sa.Column("context_difficulty", sa.String(255), nullable=False),
        sa.Column("prompt_contamination", sa.String(255), nullable=False),
        sa.Column("source_independence_group", sa.String(255), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_links", postgresql.JSONB(), nullable=False),
        sa.Column("source_lineage", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_set_id"],
            ["patterns.evidence_sets.id"],
        ),
        sa.UniqueConstraint(
            "evidence_set_id",
            "evidence_case_id",
            name="uq_pattern_evidence_set_member_case",
        ),
        schema="patterns",
    )
    op.create_index(
        "ix_pattern_evidence_member_case",
        "evidence_set_members",
        ["evidence_case_id"],
        schema="patterns",
    )

    op.create_table(
        "pattern_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("behaviour_code", sa.String(120), nullable=False),
        sa.Column("behaviour_description", sa.Text(), nullable=False),
        sa.Column("proposed_pattern_status", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(255), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_set_id"],
            ["patterns.evidence_sets.id"],
        ),
        sa.UniqueConstraint(
            "organization_context_id",
            "created_by",
            "idempotency_key",
            name="uq_pattern_candidate_idempotency",
        ),
        schema="patterns",
    )
    op.create_index(
        "ix_pattern_candidate_subject",
        "pattern_candidates",
        ["organization_context_id", "subject_person_id", "created_at"],
        schema="patterns",
    )
    op.create_index(
        "ix_pattern_candidate_behaviour",
        "pattern_candidates",
        ["organization_context_id", "behaviour_code", "created_at"],
        schema="patterns",
    )

    op.create_table(
        "pattern_candidate_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pattern_candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_set_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(
            ["pattern_candidate_id"],
            ["patterns.pattern_candidates.id"],
        ),
        sa.ForeignKeyConstraint(
            ["evidence_set_member_id"],
            ["patterns.evidence_set_members.id"],
        ),
        sa.UniqueConstraint(
            "pattern_candidate_id",
            "evidence_set_member_id",
            name="uq_pattern_candidate_evidence_member",
        ),
        schema="patterns",
    )

    op.create_table(
        "behaviour_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_pattern_candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("behaviour_code", sa.String(120), nullable=False),
        sa.Column("behaviour_description", sa.Text(), nullable=False),
        sa.Column("pattern_status", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(255), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_pattern_candidate_id"],
            ["patterns.pattern_candidates.id"],
        ),
        sa.ForeignKeyConstraint(
            ["evidence_set_id"],
            ["patterns.evidence_sets.id"],
        ),
        sa.UniqueConstraint(
            "source_pattern_candidate_id",
            name="uq_behaviour_pattern_source_candidate",
        ),
        schema="patterns",
    )
    op.create_index(
        "ix_behaviour_pattern_subject",
        "behaviour_patterns",
        ["organization_context_id", "subject_person_id", "updated_at"],
        schema="patterns",
    )
    op.create_index(
        "ix_behaviour_pattern_behaviour",
        "behaviour_patterns",
        ["organization_context_id", "behaviour_code", "updated_at"],
        schema="patterns",
    )

    op.create_table(
        "pattern_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("pattern_candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("resulting_pattern_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["pattern_candidate_id"],
            ["patterns.pattern_candidates.id"],
        ),
        sa.ForeignKeyConstraint(
            ["resulting_pattern_id"],
            ["patterns.behaviour_patterns.id"],
        ),
        schema="patterns",
    )


def downgrade() -> None:
    op.drop_table("pattern_reviews", schema="patterns")
    op.drop_index(
        "ix_behaviour_pattern_behaviour",
        table_name="behaviour_patterns",
        schema="patterns",
    )
    op.drop_index(
        "ix_behaviour_pattern_subject",
        table_name="behaviour_patterns",
        schema="patterns",
    )
    op.drop_table("behaviour_patterns", schema="patterns")
    op.drop_table("pattern_candidate_evidence", schema="patterns")
    op.drop_index(
        "ix_pattern_candidate_behaviour",
        table_name="pattern_candidates",
        schema="patterns",
    )
    op.drop_index(
        "ix_pattern_candidate_subject",
        table_name="pattern_candidates",
        schema="patterns",
    )
    op.drop_table("pattern_candidates", schema="patterns")
    op.drop_index(
        "ix_pattern_evidence_member_case",
        table_name="evidence_set_members",
        schema="patterns",
    )
    op.drop_table("evidence_set_members", schema="patterns")
    op.drop_index(
        "ix_pattern_evidence_set_subject",
        table_name="evidence_sets",
        schema="patterns",
    )
    op.drop_table("evidence_sets", schema="patterns")
    op.execute(sa.text('DROP SCHEMA IF EXISTS "patterns"'))
