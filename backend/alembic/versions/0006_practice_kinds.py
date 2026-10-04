"""practice kinds

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-04
"""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learning_units",
        sa.Column("practice_kind", sa.String(32), nullable=True),
        schema="learning",
    )
    op.execute(
        sa.text(
            "UPDATE learning.learning_units "
            "SET practice_kind = 'GUIDED_EXERCISE' "
            "WHERE phase = 'PRACTICE' AND practice_kind IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("learning_units", "practice_kind", schema="learning")
