"""scheduled effect terminal status

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-05
"""

import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scheduled_effects",
        sa.Column("terminal_status", sa.String(32), nullable=True),
        schema="mission_runtime",
    )


def downgrade() -> None:
    op.drop_column(
        "scheduled_effects",
        "terminal_status",
        schema="mission_runtime",
    )
