"""evidence engine foundation

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-05
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text('CREATE SCHEMA IF NOT EXISTS "evidence"'))

    op.create_table(
        "evidence_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("organization_context_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_context", sa.String(64), nullable=False),
        sa.Column("source_reference", sa.String(255), nullable=False),
        sa.Column("source_runtime_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("observation_type", sa.String(80), nullable=False),
        sa.Column("observed_fact", sa.Text(), nullable=False),
        sa.Column("observed_payload", postgresql.JSONB(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_independence_group", sa.String(255), nullable=False),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        sa.Column("integrity_state", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("context_request", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "source_observation_id",
            name="uq_evidence_case_source_observation",
        ),
        schema="evidence",
    )
    op.create_index(
        "ix_evidence_case_org_status",
        "evidence_cases",
        ["organization_context_id", "status", "created_at"],
        schema="evidence",
    )
    op.create_index(
        "ix_evidence_case_subject",
        "evidence_cases",
        ["organization_context_id", "subject_person_id", "created_at"],
        schema="evidence",
    )

    op.create_table(
        "evidence_interpretations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evidence_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("behaviour_code", sa.String(120), nullable=False),
        sa.Column("behaviour_description", sa.Text(), nullable=False),
        sa.Column("signal", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(255), nullable=False),
        sa.Column("confidence", sa.String(32), nullable=False),
        sa.Column("context_difficulty", sa.String(255), nullable=False),
        sa.Column("prompt_contamination", sa.String(255), nullable=False),
        sa.Column("ai_contribution", sa.String(255), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_case_id"],
            ["evidence.evidence_cases.id"],
        ),
        sa.UniqueConstraint(
            "evidence_case_id",
            "version_number",
            name="uq_evidence_interpretation_case_version",
        ),
        schema="evidence",
    )

    op.create_table(
        "evidence_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("interpretation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("target_ref", sa.String(255), nullable=False),
        sa.Column("signal", sa.String(32), nullable=False),
        sa.Column("scope", sa.String(255), nullable=False),
        sa.Column("relevance", sa.String(32), nullable=False),
        sa.Column("confidence", sa.String(32), nullable=False),
        sa.ForeignKeyConstraint(
            ["interpretation_id"],
            ["evidence.evidence_interpretations.id"],
        ),
        schema="evidence",
    )

    op.create_table(
        "evidence_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evidence_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_case_id"],
            ["evidence.evidence_cases.id"],
        ),
        schema="evidence",
    )

    op.create_table(
        "candidate_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evidence_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["evidence_case_id"],
            ["evidence.evidence_cases.id"],
        ),
        sa.UniqueConstraint(
            "evidence_case_id",
            "idempotency_key",
            name="uq_candidate_response_case_idempotency",
        ),
        schema="evidence",
    )


def downgrade() -> None:
    op.drop_table("candidate_responses", schema="evidence")
    op.drop_table("evidence_reviews", schema="evidence")
    op.drop_table("evidence_links", schema="evidence")
    op.drop_table("evidence_interpretations", schema="evidence")
    op.drop_index(
        "ix_evidence_case_subject",
        table_name="evidence_cases",
        schema="evidence",
    )
    op.drop_index(
        "ix_evidence_case_org_status",
        table_name="evidence_cases",
        schema="evidence",
    )
    op.drop_table("evidence_cases", schema="evidence")
    op.execute(sa.text('DROP SCHEMA IF EXISTS "evidence"'))
