"""academy foundation

Revision ID: 0001
Revises:
Create Date: 2026-10-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMAS = ("identity", "academy", "curriculum", "journey", "platform", "readmodel")


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(sa.text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

    op.create_table(
        "people",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("external_subject", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="identity",
    )
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="identity",
    )
    op.create_table(
        "organization_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("membership_role", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["identity.people.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["identity.organizations.id"]),
        sa.UniqueConstraint("person_id", "organization_id", "membership_role"),
        schema="identity",
    )

    op.create_table(
        "capabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(128), nullable=False, unique=True),
        schema="curriculum",
    )
    op.create_table(
        "capability_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("definition_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["definition_id"], ["curriculum.capabilities.id"]),
        sa.UniqueConstraint("definition_id", "version_number"),
        schema="curriculum",
    )
    op.create_table(
        "curricula",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.UniqueConstraint("code", "version_number"),
        schema="curriculum",
    )
    op.create_table(
        "curriculum_waves",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("curriculum_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["curriculum_id"], ["curriculum.curricula.id"]),
        sa.UniqueConstraint("curriculum_id", "code"),
        schema="curriculum",
    )
    op.create_table(
        "wave_capabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("wave_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("capability_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["wave_id"], ["curriculum.curriculum_waves.id"]),
        sa.ForeignKeyConstraint(["capability_version_id"], ["curriculum.capability_versions.id"]),
        sa.UniqueConstraint("wave_id", "capability_version_id"),
        schema="curriculum",
    )

    op.create_table(
        "cohorts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("track_code", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.UniqueConstraint("organization_context_id", "code"),
        schema="academy",
    )
    op.create_table(
        "cohort_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cohort_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_type", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["cohort_id"], ["academy.cohorts.id"]),
        sa.UniqueConstraint("cohort_id", "person_id", "member_type"),
        schema="academy",
    )
    op.create_table(
        "class_offerings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cohort_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("primary_capability_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["cohort_id"], ["academy.cohorts.id"]),
        schema="academy",
    )
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("class_offering_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivery_mode", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(["class_offering_id"], ["academy.class_offerings.id"]),
        schema="academy",
    )
    op.create_table(
        "instructor_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("class_offering_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["class_offering_id"], ["academy.class_offerings.id"]),
        sa.UniqueConstraint("class_offering_id", "person_id"),
        schema="academy",
    )

    op.create_table(
        "candidate_journeys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohort_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("track_code", sa.String(128), nullable=False),
        sa.Column("curriculum_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("current_wave", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("person_id", "organization_context_id", "track_code"),
        schema="journey",
    )

    op.create_table(
        "domain_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(160), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("aggregate_type", sa.String(128), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_version", sa.BigInteger(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", postgresql.JSONB(), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("causation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("data_classification", sa.String(32), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("trace_id", sa.String(128), nullable=False),
        schema="platform",
    )
    op.create_table(
        "outbox_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(160), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="platform",
    )
    op.create_table(
        "inbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("consumer_name", sa.String(128), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("consumer_name", "event_id"),
        schema="platform",
    )

    op.create_table(
        "candidate_home",
        sa.Column("person_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="readmodel",
    )
    op.create_table(
        "instructor_home",
        sa.Column("person_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="readmodel",
    )


def downgrade() -> None:
    for schema in reversed(SCHEMAS):
        op.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
