"""scheduled effects and simulation clock

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
    op.add_column(
        "mission_instances",
        sa.Column(
            "simulation_time",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="mission_runtime",
    )

    op.create_table(
        "scheduled_effects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("origin_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("effect_code", sa.String(120), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effect_payload", postgresql.JSONB(), nullable=False),
        sa.Column("cancellable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cancel_condition", postgresql.JSONB(), nullable=False),
        sa.Column("visibility", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
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
            "idempotency_key",
            name="uq_scheduled_effect_instance_idempotency",
        ),
        schema="mission_runtime",
    )
    op.create_index(
        "ix_scheduled_effects_due",
        "scheduled_effects",
        ["mission_instance_id", "status", "due_at"],
        schema="mission_runtime",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scheduled_effects_due",
        table_name="scheduled_effects",
        schema="mission_runtime",
    )
    op.drop_table("scheduled_effects", schema="mission_runtime")
    op.drop_column("mission_instances", "simulation_time", schema="mission_runtime")
