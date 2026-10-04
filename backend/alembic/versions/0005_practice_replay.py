"""practice replay lineage

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-04
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "practice_attempts_learning_unit_id_candidate_id_key",
        "practice_attempts",
        schema="learning",
        type_="unique",
    )
    op.add_column(
        "practice_attempts",
        sa.Column(
            "attempt_number",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        schema="learning",
    )
    op.add_column(
        "practice_attempts",
        sa.Column(
            "replay_of_attempt_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        schema="learning",
    )
    op.create_foreign_key(
        "fk_practice_attempt_replay",
        "practice_attempts",
        "practice_attempts",
        ["replay_of_attempt_id"],
        ["id"],
        source_schema="learning",
        referent_schema="learning",
    )
    op.create_unique_constraint(
        "uq_practice_attempt_unit_candidate_number",
        "practice_attempts",
        ["learning_unit_id", "candidate_id", "attempt_number"],
        schema="learning",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_practice_attempt_unit_candidate_number",
        "practice_attempts",
        schema="learning",
        type_="unique",
    )
    op.drop_constraint(
        "fk_practice_attempt_replay",
        "practice_attempts",
        schema="learning",
        type_="foreignkey",
    )
    op.drop_column("practice_attempts", "replay_of_attempt_id", schema="learning")
    op.drop_column("practice_attempts", "attempt_number", schema="learning")
    op.create_unique_constraint(
        "practice_attempts_learning_unit_id_candidate_id_key",
        "practice_attempts",
        ["learning_unit_id", "candidate_id"],
        schema="learning",
    )
