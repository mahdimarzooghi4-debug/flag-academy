"""state triggered scheduled effects

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-05
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "scheduled_effects",
        "due_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        schema="mission_runtime",
    )
    op.add_column(
        "scheduled_effects",
        sa.Column("trigger_condition", postgresql.JSONB(), nullable=True),
        schema="mission_runtime",
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM mission_runtime.scheduled_effects WHERE due_at IS NULL"
    )
    op.drop_column(
        "scheduled_effects",
        "trigger_condition",
        schema="mission_runtime",
    )
    op.alter_column(
        "scheduled_effects",
        "due_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        schema="mission_runtime",
    )
