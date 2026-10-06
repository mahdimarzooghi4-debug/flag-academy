"""profile update human review fields

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-06
"""

import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "profile_update_cases",
        sa.Column("reviewed_claim_state", sa.String(32), nullable=True),
        schema="flag_profile",
    )
    op.add_column(
        "profile_update_cases",
        sa.Column("reviewed_level", sa.String(16), nullable=True),
        schema="flag_profile",
    )
    op.add_column(
        "profile_update_cases",
        sa.Column("reviewed_proven_scope", sa.String(255), nullable=True),
        schema="flag_profile",
    )
    op.add_column(
        "profile_update_cases",
        sa.Column("reviewed_evidence_recency", sa.String(255), nullable=True),
        schema="flag_profile",
    )
    op.add_column(
        "profile_update_cases",
        sa.Column("reviewed_confidence_in_claim", sa.String(64), nullable=True),
        schema="flag_profile",
    )
    op.add_column(
        "profile_update_cases",
        sa.Column("reviewed_next_evidence_needed", sa.Text(), nullable=True),
        schema="flag_profile",
    )
    op.add_column(
        "profile_update_cases",
        sa.Column("review_rationale", sa.Text(), nullable=True),
        schema="flag_profile",
    )


def downgrade() -> None:
    op.drop_column(
        "profile_update_cases",
        "review_rationale",
        schema="flag_profile",
    )
    op.drop_column(
        "profile_update_cases",
        "reviewed_next_evidence_needed",
        schema="flag_profile",
    )
    op.drop_column(
        "profile_update_cases",
        "reviewed_confidence_in_claim",
        schema="flag_profile",
    )
    op.drop_column(
        "profile_update_cases",
        "reviewed_evidence_recency",
        schema="flag_profile",
    )
    op.drop_column(
        "profile_update_cases",
        "reviewed_proven_scope",
        schema="flag_profile",
    )
    op.drop_column(
        "profile_update_cases",
        "reviewed_level",
        schema="flag_profile",
    )
    op.drop_column(
        "profile_update_cases",
        "reviewed_claim_state",
        schema="flag_profile",
    )
