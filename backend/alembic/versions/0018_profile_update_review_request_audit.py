"""profile update review request audit

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-06
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "profile_update_cases",
        sa.Column(
            "review_requested_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        schema="flag_profile",
    )
    op.add_column(
        "profile_update_cases",
        sa.Column(
            "review_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        schema="flag_profile",
    )
    op.add_column(
        "profile_update_cases",
        sa.Column(
            "review_request_idempotency_key",
            sa.String(160),
            nullable=True,
        ),
        schema="flag_profile",
    )


def downgrade() -> None:
    op.drop_column(
        "profile_update_cases",
        "review_request_idempotency_key",
        schema="flag_profile",
    )
    op.drop_column(
        "profile_update_cases",
        "review_requested_at",
        schema="flag_profile",
    )
    op.drop_column(
        "profile_update_cases",
        "review_requested_by",
        schema="flag_profile",
    )
