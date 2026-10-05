"""mission design v1

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-05
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS "mission_design"'))

    op.create_table(
        "mission_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "organization_context_id",
            "code",
            name="uq_mission_template_org_code",
        ),
        schema="mission_design",
    )

    op.create_table(
        "mission_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("aggregate_version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("primary_capability_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mission_mode", sa.String(32), nullable=False),
        sa.Column("difficulty", sa.String(8), nullable=False),
        sa.Column("world_context", postgresql.JSONB(), nullable=False),
        sa.Column("actors", postgresql.JSONB(), nullable=False),
        sa.Column("information_items", postgresql.JSONB(), nullable=False),
        sa.Column("constraints", postgresql.JSONB(), nullable=False),
        sa.Column("decision_points", postgresql.JSONB(), nullable=False),
        sa.Column("consequence_rules", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_opportunities", postgresql.JSONB(), nullable=False),
        sa.Column("replay_policy", postgresql.JSONB(), nullable=False),
        sa.Column("safety_policy", postgresql.JSONB(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["mission_design.mission_templates.id"],
        ),
        sa.UniqueConstraint(
            "template_id",
            "version_number",
            name="uq_mission_version_template_number",
        ),
        schema="mission_design",
    )
    op.create_index(
        "ix_mission_versions_template_status",
        "mission_versions",
        ["template_id", "status"],
        schema="mission_design",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_mission_versions_template_status",
        table_name="mission_versions",
        schema="mission_design",
    )
    op.drop_table("mission_versions", schema="mission_design")
    op.drop_table("mission_templates", schema="mission_design")
    op.execute(sa.text('DROP SCHEMA IF EXISTS "mission_design"'))
