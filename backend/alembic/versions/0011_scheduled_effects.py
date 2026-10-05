"""temporal scheduled effects

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-05
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduled_effects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("origin_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("effect_code", sa.String(120), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("world_effect", postgresql.JSONB(), nullable=False),
        sa.Column("candidate_message", sa.Text(), nullable=True),
        sa.Column("cancellable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "cancel_condition",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("workflow_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["mission_instance_id"],
            ["mission_runtime.mission_instances.id"],
        ),
        sa.ForeignKeyConstraint(
            ["origin_event_id"],
            ["mission_runtime.runtime_events.id"],
        ),
        sa.UniqueConstraint(
            "mission_instance_id",
            "effect_code",
            "origin_event_id",
            name="uq_scheduled_effect_origin_code",
        ),
        sa.UniqueConstraint(
            "workflow_id",
            name="uq_scheduled_effect_workflow_id",
        ),
        schema="mission_runtime",
    )
    op.create_index(
        "ix_scheduled_effects_status_due_at",
        "scheduled_effects",
        ["status", "due_at"],
        schema="mission_runtime",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scheduled_effects_status_due_at",
        table_name="scheduled_effects",
        schema="mission_runtime",
    )
    op.drop_table("scheduled_effects", schema="mission_runtime")
