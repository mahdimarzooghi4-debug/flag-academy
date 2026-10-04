"""practice attempt foundation

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-04
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "practice_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("learning_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["learning_unit_id"],
            ["learning.learning_units.id"],
        ),
        sa.UniqueConstraint("learning_unit_id", "candidate_id"),
        schema="learning",
    )
    op.create_index(
        "ix_practice_attempts_candidate_status",
        "practice_attempts",
        ["candidate_id", "status"],
        schema="learning",
    )

    op.create_table(
        "practice_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_attempt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instructor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["practice_attempt_id"],
            ["learning.practice_attempts.id"],
        ),
        schema="learning",
    )
    op.create_index(
        "ix_practice_feedback_attempt_created",
        "practice_feedback",
        ["practice_attempt_id", "created_at"],
        schema="learning",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_practice_feedback_attempt_created",
        table_name="practice_feedback",
        schema="learning",
    )
    op.drop_table("practice_feedback", schema="learning")
    op.drop_index(
        "ix_practice_attempts_candidate_status",
        table_name="practice_attempts",
        schema="learning",
    )
    op.drop_table("practice_attempts", schema="learning")
