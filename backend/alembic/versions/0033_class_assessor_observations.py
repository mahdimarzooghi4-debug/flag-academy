"""Academy immutable factual classroom observations; never automatic Evidence.

Revision ID: 0033
Revises: 0032
Create Date: 2026-10-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "class_assessor_observations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_context_id", uuid, nullable=False),
        sa.Column("class_offering_id", uuid, nullable=False),
        sa.Column("session_id", uuid, nullable=False),
        sa.Column("candidate_person_id", uuid, nullable=False),
        sa.Column("observer_person_id", uuid, nullable=False),
        sa.Column("grant_id", uuid, nullable=False),
        sa.Column("grant_version", sa.BigInteger(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_fact", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.ForeignKeyConstraint(["class_offering_id"], ["academy.class_offerings.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["academy.sessions.id"]),
        sa.ForeignKeyConstraint(["grant_id"], ["academy.assessor_class_grants.id"]),
        sa.UniqueConstraint(
            "organization_context_id", "observer_person_id", "idempotency_key",
            name="uq_class_observation_actor_idempotency",
        ),
        sa.CheckConstraint(
            "observed_at <= recorded_at",
            name="ck_class_observation_recorded_after_observed",
        ),
        sa.CheckConstraint(
            "length(trim(observed_fact)) > 0",
            name="ck_class_observation_nonblank_fact",
        ),
        schema="academy",
    )
    op.execute(sa.text("""
        CREATE FUNCTION academy.reject_class_observation_mutation()
        RETURNS trigger LANGUAGE plpgsql AS '
        BEGIN
            RAISE EXCEPTION ''Class observations are immutable'';
        END;'
    """))
    op.execute(sa.text("""
        CREATE TRIGGER trg_class_observation_immutable
        BEFORE UPDATE OR DELETE ON academy.class_assessor_observations
        FOR EACH ROW EXECUTE FUNCTION academy.reject_class_observation_mutation()
    """))


def downgrade() -> None:
    op.execute(sa.text(
        "DROP TRIGGER IF EXISTS trg_class_observation_immutable "
        "ON academy.class_assessor_observations"
    ))
    op.execute(sa.text(
        "DROP FUNCTION IF EXISTS academy.reject_class_observation_mutation()"
    ))
    op.drop_table("class_assessor_observations", schema="academy")
