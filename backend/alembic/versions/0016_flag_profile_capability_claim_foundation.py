"""flag profile capability claim foundation

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-06
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS "flag_profile"'))

    op.create_table(
        "flag_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("track_code", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "organization_context_id",
            "subject_person_id",
            "track_code",
            name="uq_flag_profile_subject_track",
        ),
        schema="flag_profile",
    )
    op.create_index(
        "ix_flag_profile_subject",
        "flag_profiles",
        ["organization_context_id", "subject_person_id", "track_code"],
        schema="flag_profile",
    )

    op.create_table(
        "profile_update_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("flag_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("track_code", sa.String(128), nullable=False),
        sa.Column("capability_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("current_claim_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_claim_version", sa.BigInteger(), nullable=True),
        sa.Column("current_claim_state", sa.String(32), nullable=True),
        sa.Column("current_level", sa.String(16), nullable=True),
        sa.Column("current_proven_scope", sa.String(255), nullable=True),
        sa.Column("current_evidence_recency", sa.String(255), nullable=True),
        sa.Column("current_confidence_in_claim", sa.String(64), nullable=True),
        sa.Column("current_next_evidence_needed", sa.Text(), nullable=True),
        sa.Column("proposed_claim_state", sa.String(32), nullable=False),
        sa.Column("proposed_level", sa.String(16), nullable=False),
        sa.Column("proposed_proven_scope", sa.String(255), nullable=False),
        sa.Column("proposed_evidence_recency", sa.String(255), nullable=False),
        sa.Column("proposed_confidence_in_claim", sa.String(64), nullable=False),
        sa.Column("proposed_next_evidence_needed", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creation_idempotency_key", sa.String(160), nullable=False),
        sa.Column("review_idempotency_key", sa.String(160), nullable=True),
        sa.Column("apply_idempotency_key", sa.String(160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["flag_profile_id"],
            ["flag_profile.flag_profiles.id"],
        ),
        sa.UniqueConstraint(
            "organization_context_id",
            "created_by",
            "creation_idempotency_key",
            name="uq_profile_update_case_creation_idempotency",
        ),
        schema="flag_profile",
    )
    op.create_index(
        "ix_profile_update_case_subject",
        "profile_update_cases",
        ["organization_context_id", "subject_person_id", "created_at"],
        schema="flag_profile",
    )
    op.create_index(
        "ix_profile_update_case_capability",
        "profile_update_cases",
        ["organization_context_id", "capability_id", "created_at"],
        schema="flag_profile",
    )

    op.create_table(
        "profile_update_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_update_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pattern_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pattern_version", sa.BigInteger(), nullable=False),
        sa.Column("relationship", sa.String(32), nullable=False),
        sa.Column("pattern_status", sa.String(32), nullable=False),
        sa.Column("behaviour_code", sa.String(120), nullable=False),
        sa.Column("pattern_scope", sa.String(255), nullable=False),
        sa.Column("pattern_reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_update_case_id"],
            ["flag_profile.profile_update_cases.id"],
        ),
        sa.UniqueConstraint(
            "profile_update_case_id",
            "pattern_id",
            name="uq_profile_update_case_pattern",
        ),
        schema="flag_profile",
    )

    op.create_table(
        "profile_update_pattern_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_update_pattern_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_set_member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interpretation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interpretation_version", sa.Integer(), nullable=False),
        sa.Column("evidence_relationship", sa.String(32), nullable=False),
        sa.Column("signal", sa.String(32), nullable=False),
        sa.Column("evidence_scope", sa.String(255), nullable=False),
        sa.Column("confidence", sa.String(32), nullable=False),
        sa.Column("context_difficulty", sa.String(255), nullable=False),
        sa.Column("prompt_contamination", sa.String(255), nullable=False),
        sa.Column("source_independence_group", sa.String(255), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_context", sa.String(64), nullable=False),
        sa.Column("source_reference", sa.String(255), nullable=False),
        sa.Column("observation_type", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["profile_update_pattern_id"],
            ["flag_profile.profile_update_patterns.id"],
        ),
        sa.UniqueConstraint(
            "profile_update_pattern_id",
            "evidence_set_member_id",
            name="uq_profile_update_pattern_evidence_member",
        ),
        schema="flag_profile",
    )

    op.create_table(
        "capability_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("flag_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("track_code", sa.String(128), nullable=False),
        sa.Column("capability_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("proven_scope", sa.String(255), nullable=False),
        sa.Column("evidence_recency", sa.String(255), nullable=False),
        sa.Column("confidence_in_claim", sa.String(64), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("next_evidence_needed", sa.Text(), nullable=False),
        sa.Column("source_profile_update_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["flag_profile_id"],
            ["flag_profile.flag_profiles.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_profile_update_case_id"],
            ["flag_profile.profile_update_cases.id"],
        ),
        sa.UniqueConstraint(
            "flag_profile_id",
            "capability_id",
            name="uq_capability_claim_profile_capability",
        ),
        schema="flag_profile",
    )
    op.create_index(
        "ix_capability_claim_subject",
        "capability_claims",
        ["organization_context_id", "subject_person_id", "capability_id"],
        schema="flag_profile",
    )

    op.create_table(
        "capability_claim_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("capability_claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pattern_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pattern_version", sa.BigInteger(), nullable=False),
        sa.Column("relationship", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["capability_claim_id"],
            ["flag_profile.capability_claims.id"],
        ),
        sa.UniqueConstraint(
            "capability_claim_id",
            "pattern_id",
            name="uq_capability_claim_pattern",
        ),
        schema="flag_profile",
    )


def downgrade() -> None:
    op.drop_table("capability_claim_patterns", schema="flag_profile")
    op.drop_index(
        "ix_capability_claim_subject",
        table_name="capability_claims",
        schema="flag_profile",
    )
    op.drop_table("capability_claims", schema="flag_profile")
    op.drop_table("profile_update_pattern_evidence", schema="flag_profile")
    op.drop_table("profile_update_patterns", schema="flag_profile")
    op.drop_index(
        "ix_profile_update_case_capability",
        table_name="profile_update_cases",
        schema="flag_profile",
    )
    op.drop_index(
        "ix_profile_update_case_subject",
        table_name="profile_update_cases",
        schema="flag_profile",
    )
    op.drop_table("profile_update_cases", schema="flag_profile")
    op.drop_index(
        "ix_flag_profile_subject",
        table_name="flag_profiles",
        schema="flag_profile",
    )
    op.drop_table("flag_profiles", schema="flag_profile")
    op.execute(sa.text('DROP SCHEMA IF EXISTS "flag_profile"'))
