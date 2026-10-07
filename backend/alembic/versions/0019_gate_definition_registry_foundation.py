"""gate definition registry foundation

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-06
"""

from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

_GATE_DEFINITIONS = (
    (
        UUID("a1000000-0000-0000-0000-000000000001"),
        "A",
        "Foundation Readiness",
        UUID("a1100000-0000-0000-0000-000000000001"),
        "آیا فرد آماده ورود جدی به Product Core است؟",
        (
            "Trustworthiness = PASS",
            "Ownership = PASS",
            "Accountability = PASS",
            "Problem Framing حداقل Demonstrated",
            "Decision Making حداقل Demonstrated",
            "Data Thinking حداقل Demonstrated",
            "Reflection فعال",
        ),
        ("ENTER PRODUCT CORE", "NOT YET"),
    ),
    (
        UUID("a1000000-0000-0000-0000-000000000002"),
        "B",
        "Product Judgment Readiness",
        UUID("a1100000-0000-0000-0000-000000000002"),
        "آیا فرد می‌تواند در مسئله محصولی پیچیده Judgment نشان دهد؟",
        (
            "Customer Understanding حداقل Demonstrated",
            "Product Discovery حداقل Demonstrated",
            "Metrics & Experimentation حداقل Demonstrated",
            "Decision Making در چند Context",
            "Replay معتبر",
        ),
        ("ENTER INTEGRATED SIMULATION", "NOT YET"),
    ),
    (
        UUID("a1000000-0000-0000-0000-000000000003"),
        "C",
        "Real Project Readiness",
        UUID("a1100000-0000-0000-0000-000000000003"),
        "آیا امن است بخشی از واقعیت کسب‌وکار را به او بسپاریم؟",
        (
            "Gates رفتاری PASS",
            "Integrated Simulation",
            "Delivery حداقل Demonstrated",
            "Stakeholder Alignment حداقل Demonstrated",
            "Product Judgment قابل اتکا",
            "Behaviour Change اثبات‌شده",
        ),
        ("ENTER APPRENTICESHIP", "NOT YET"),
    ),
    (
        UUID("a1000000-0000-0000-0000-000000000004"),
        "D",
        "Ownership Trial Readiness",
        UUID("a1100000-0000-0000-0000-000000000004"),
        "آیا می‌توان Outcome واقعی را به او سپرد؟",
        (
            "Evidence واقعی از Delivery",
            "Evidence واقعی از Stakeholder Alignment",
            "Accountability معتبر",
            "Strategy / Prioritization متناسب با Scope",
            "Real Project Evidence کافی",
        ),
        ("GRANT OUTCOME OWNERSHIP", "REMEDIATE"),
    ),
    (
        UUID("a1000000-0000-0000-0000-000000000005"),
        "E",
        "Flag Board",
        UUID("a1100000-0000-0000-0000-000000000005"),
        "دقیقاً چه مسئولیتی را می‌توان با اطمینان به این فرد سپرد؟",
        (
            "Flag Profile کامل",
            "Real Project Evidence",
            "Replay",
            "Gate History",
            "Evidence Conflict Review",
            "Outcome History",
        ),
        ("READY", "NOT YET", "DIFFERENT SCOPE"),
    ),
)


def upgrade() -> None:
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS "gate_assessment"'))

    op.create_table(
        "gate_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(8), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="gate_assessment",
    )
    op.create_table(
        "gate_definition_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "gate_definition_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("decision_question", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["gate_definition_id"],
            ["gate_assessment.gate_definitions.id"],
        ),
        sa.UniqueConstraint(
            "gate_definition_id",
            "version_number",
            name="uq_gate_definition_version",
        ),
        schema="gate_assessment",
    )
    op.create_table(
        "gate_definition_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "gate_definition_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["gate_definition_version_id"],
            ["gate_assessment.gate_definition_versions.id"],
        ),
        sa.UniqueConstraint(
            "gate_definition_version_id",
            "position",
            name="uq_gate_definition_requirement_position",
        ),
        schema="gate_assessment",
    )
    op.create_table(
        "gate_definition_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "gate_definition_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("outcome_text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["gate_definition_version_id"],
            ["gate_assessment.gate_definition_versions.id"],
        ),
        sa.UniqueConstraint(
            "gate_definition_version_id",
            "position",
            name="uq_gate_definition_outcome_position",
        ),
        schema="gate_assessment",
    )

    created_at = datetime(2026, 10, 6, tzinfo=UTC)
    definition_table = sa.table(
        "gate_definitions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        schema="gate_assessment",
    )
    version_table = sa.table(
        "gate_definition_versions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("gate_definition_id", postgresql.UUID(as_uuid=True)),
        sa.column("version_number", sa.Integer),
        sa.column("name", sa.String),
        sa.column("decision_question", sa.Text),
        sa.column("created_at", sa.DateTime(timezone=True)),
        schema="gate_assessment",
    )
    requirement_table = sa.table(
        "gate_definition_requirements",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("gate_definition_version_id", postgresql.UUID(as_uuid=True)),
        sa.column("position", sa.Integer),
        sa.column("requirement_text", sa.Text),
        schema="gate_assessment",
    )
    outcome_table = sa.table(
        "gate_definition_outcomes",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("gate_definition_version_id", postgresql.UUID(as_uuid=True)),
        sa.column("position", sa.Integer),
        sa.column("outcome_text", sa.Text),
        schema="gate_assessment",
    )

    for gate_index, (
        definition_id,
        code,
        name,
        version_id,
        question,
        requirements,
        outcomes,
    ) in enumerate(_GATE_DEFINITIONS, start=1):
        op.bulk_insert(
            definition_table,
            [
                {
                    "id": definition_id,
                    "code": code,
                    "created_at": created_at,
                }
            ],
        )
        op.bulk_insert(
            version_table,
            [
                {
                    "id": version_id,
                    "gate_definition_id": definition_id,
                    "version_number": 1,
                    "name": name,
                    "decision_question": question,
                    "created_at": created_at,
                }
            ],
        )
        op.bulk_insert(
            requirement_table,
            [
                {
                    "id": UUID(
                        f"a12{gate_index:01d}{position:02d}00-0000-0000-0000-000000000000"
                    ),
                    "gate_definition_version_id": version_id,
                    "position": position,
                    "requirement_text": requirement,
                }
                for position, requirement in enumerate(requirements, start=1)
            ],
        )
        op.bulk_insert(
            outcome_table,
            [
                {
                    "id": UUID(
                        f"a13{gate_index:01d}{position:02d}00-0000-0000-0000-000000000000"
                    ),
                    "gate_definition_version_id": version_id,
                    "position": position,
                    "outcome_text": outcome,
                }
                for position, outcome in enumerate(outcomes, start=1)
            ],
        )


    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION gate_assessment.reject_gate_definition_mutation()
            RETURNS trigger
            LANGUAGE plpgsql
            AS 'BEGIN
                RAISE EXCEPTION
                    ''gate definition registry rows are immutable; create a new version instead'';
            END;';
            """
        )
    )
    immutable_tables = (
        "gate_definitions",
        "gate_definition_versions",
        "gate_definition_requirements",
        "gate_definition_outcomes",
    )
    for table_name in immutable_tables:
        op.execute(
            sa.text(
                f"""
                CREATE TRIGGER trg_{table_name}_immutable
                BEFORE UPDATE OR DELETE ON gate_assessment.{table_name}
                FOR EACH ROW
                EXECUTE FUNCTION gate_assessment.reject_gate_definition_mutation()
                """
            )
        )


def downgrade() -> None:
    op.drop_table("gate_definition_outcomes", schema="gate_assessment")
    op.drop_table("gate_definition_requirements", schema="gate_assessment")
    op.drop_table("gate_definition_versions", schema="gate_assessment")
    op.drop_table("gate_definitions", schema="gate_assessment")
    op.execute(
        sa.text(
            "DROP FUNCTION IF EXISTS "
            "gate_assessment.reject_gate_definition_mutation()"
        )
    )
    op.execute(sa.text('DROP SCHEMA IF EXISTS "gate_assessment"'))
