"""mission assignment and eligibility

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-05
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mission_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mission_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("assignment_reason", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_context_id"],
            ["identity.organizations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["identity.people.id"],
        ),
        sa.ForeignKeyConstraint(
            ["mission_version_id"],
            ["mission_design.mission_versions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by"],
            ["identity.people.id"],
        ),
        sa.UniqueConstraint(
            "organization_context_id",
            "idempotency_key",
            name="uq_mission_assignment_org_idempotency",
        ),
        schema="mission_runtime",
    )
    op.create_index(
        "ix_mission_assignments_candidate_status",
        "mission_assignments",
        ["organization_context_id", "candidate_id", "status"],
        schema="mission_runtime",
    )

    op.add_column(
        "mission_instances",
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema="mission_runtime",
    )
    op.create_foreign_key(
        "fk_mission_instances_assignment_id",
        "mission_instances",
        "mission_assignments",
        ["assignment_id"],
        ["id"],
        source_schema="mission_runtime",
        referent_schema="mission_runtime",
    )
    op.create_unique_constraint(
        "uq_mission_instances_assignment_id",
        "mission_instances",
        ["assignment_id"],
        schema="mission_runtime",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_mission_instances_assignment_id",
        "mission_instances",
        type_="unique",
        schema="mission_runtime",
    )
    op.drop_constraint(
        "fk_mission_instances_assignment_id",
        "mission_instances",
        type_="foreignkey",
        schema="mission_runtime",
    )
    op.drop_column("mission_instances", "assignment_id", schema="mission_runtime")
    op.drop_index(
        "ix_mission_assignments_candidate_status",
        table_name="mission_assignments",
        schema="mission_runtime",
    )
    op.drop_table("mission_assignments", schema="mission_runtime")
