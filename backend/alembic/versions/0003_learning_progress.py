"""learning progress v1

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-04
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learning_unit_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("learning_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["learning_unit_id"],
            ["learning.learning_units.id"],
        ),
        sa.UniqueConstraint("learning_unit_id", "candidate_id"),
        schema="learning",
    )
    op.create_index(
        "ix_learning_unit_progress_candidate_state",
        "learning_unit_progress",
        ["candidate_id", "state"],
        schema="learning",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_learning_unit_progress_candidate_state",
        table_name="learning_unit_progress",
        schema="learning",
    )
    op.drop_table("learning_unit_progress", schema="learning")
