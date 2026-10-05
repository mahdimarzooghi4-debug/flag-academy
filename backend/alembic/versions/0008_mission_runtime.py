"""mission runtime v1

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-05
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS "mission_runtime"'))

    op.create_table(
        "mission_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mission_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("world_state", postgresql.JSONB(), nullable=False),
        sa.Column("world_state_version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("simulation_seed", sa.BigInteger(), nullable=False),
        sa.Column("start_idempotency_key", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["mission_version_id"],
            ["mission_design.mission_versions.id"],
        ),
        sa.UniqueConstraint(
            "mission_version_id",
            "candidate_id",
            "start_idempotency_key",
            name="uq_mission_instance_start_idempotency",
        ),
        schema="mission_runtime",
    )
    op.create_index(
        "ix_mission_instances_candidate_created",
        "mission_instances",
        ["organization_context_id", "candidate_id", "created_at"],
        schema="mission_runtime",
    )

    op.create_table(
        "candidate_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(48), nullable=False),
        sa.Column("target", sa.String(255), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resource_cost", postgresql.JSONB(), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.ForeignKeyConstraint(
            ["mission_instance_id"],
            ["mission_runtime.mission_instances.id"],
        ),
        sa.UniqueConstraint(
            "mission_instance_id",
            "idempotency_key",
            name="uq_candidate_action_instance_idempotency",
        ),
        schema="mission_runtime",
    )

    op.create_table(
        "decision_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("options_considered", postgresql.JSONB(), nullable=False),
        sa.Column("available_evidence", postgresql.JSONB(), nullable=False),
        sa.Column("assumptions", postgresql.JSONB(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("expected_outcome", sa.Text(), nullable=False),
        sa.Column("revisit_trigger", sa.Text(), nullable=False),
        sa.Column("decision_owner", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reversibility", sa.String(64), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["mission_instance_id"],
            ["mission_runtime.mission_instances.id"],
        ),
        sa.ForeignKeyConstraint(
            ["action_id"],
            ["mission_runtime.candidate_actions.id"],
        ),
        sa.UniqueConstraint("action_id", name="uq_decision_record_action"),
        schema="mission_runtime",
    )

    op.create_table(
        "runtime_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(160), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("trigger_type", sa.String(64), nullable=False),
        sa.Column("trigger_reference", sa.String(255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("visibility", sa.String(32), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("world_version_before", sa.BigInteger(), nullable=False),
        sa.Column("world_version_after", sa.BigInteger(), nullable=False),
        sa.Column("causal_parent_ids", postgresql.JSONB(), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.ForeignKeyConstraint(
            ["mission_instance_id"],
            ["mission_runtime.mission_instances.id"],
        ),
        sa.UniqueConstraint(
            "mission_instance_id",
            "sequence_number",
            name="uq_runtime_event_instance_sequence",
        ),
        sa.UniqueConstraint(
            "mission_instance_id",
            "idempotency_key",
            name="uq_runtime_event_instance_idempotency",
        ),
        schema="mission_runtime",
    )

    op.create_table(
        "observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mission_instance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("observation_type", sa.String(80), nullable=False),
        sa.Column("factual_statement", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["mission_instance_id"],
            ["mission_runtime.mission_instances.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_event_id"],
            ["mission_runtime.runtime_events.id"],
        ),
        sa.UniqueConstraint("source_event_id", name="uq_observation_source_event"),
        schema="mission_runtime",
    )


def downgrade() -> None:
    op.drop_table("observations", schema="mission_runtime")
    op.drop_table("runtime_events", schema="mission_runtime")
    op.drop_table("decision_records", schema="mission_runtime")
    op.drop_table("candidate_actions", schema="mission_runtime")
    op.drop_index(
        "ix_mission_instances_candidate_created",
        table_name="mission_instances",
        schema="mission_runtime",
    )
    op.drop_table("mission_instances", schema="mission_runtime")
    op.execute(sa.text('DROP SCHEMA IF EXISTS "mission_runtime"'))
