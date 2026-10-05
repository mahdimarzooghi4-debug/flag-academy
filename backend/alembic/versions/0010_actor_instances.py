"""mission actor instances

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-05
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "actor_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_key", sa.String(120), nullable=False),
        sa.Column("definition_name", sa.String(120), nullable=False),
        sa.Column("state", postgresql.JSONB(), nullable=False),
        sa.Column("state_version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["mission_instance_id"],
            ["mission_runtime.mission_instances.id"],
        ),
        sa.UniqueConstraint(
            "mission_instance_id",
            "actor_key",
            name="uq_actor_instance_mission_actor",
        ),
        schema="mission_runtime",
    )
    op.create_index(
        "ix_actor_instances_mission",
        "actor_instances",
        ["mission_instance_id", "actor_key"],
        schema="mission_runtime",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_actor_instances_mission",
        table_name="actor_instances",
        schema="mission_runtime",
    )
    op.drop_table("actor_instances", schema="mission_runtime")
