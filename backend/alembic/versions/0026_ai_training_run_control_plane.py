"""governed AI training run control plane

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-07
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "training_runs",
        sa.Column(
            "organization_context_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        schema="ai_control_plane",
    )
    op.add_column(
        "training_runs",
        sa.Column("request_key", sa.String(160), nullable=False),
        schema="ai_control_plane",
    )
    op.add_column(
        "training_runs",
        sa.Column("data_classification", sa.String(64), nullable=False),
        schema="ai_control_plane",
    )
    op.create_unique_constraint(
        "uq_ai_training_run_request_key",
        "training_runs",
        ["organization_context_id", "request_key"],
        schema="ai_control_plane",
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION ai_control_plane.require_succeeded_training()
            RETURNS trigger
            LANGUAGE plpgsql
            AS 'DECLARE
                current_state text;
            BEGIN
                SELECT state
                  INTO current_state
                  FROM ai_control_plane.training_run_states
                 WHERE training_run_id = NEW.training_run_id
                 ORDER BY sequence DESC
                 LIMIT 1;

                IF current_state IS DISTINCT FROM ''SUCCEEDED'' THEN
                    RAISE EXCEPTION
                        ''model artifact requires SUCCEEDED Training Run'';
                END IF;

                RETURN NEW;
            END;';
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_model_artifact_requires_succeeded_training
            BEFORE INSERT ON ai_control_plane.model_artifacts
            FOR EACH ROW
            EXECUTE FUNCTION ai_control_plane.require_succeeded_training()
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DROP TRIGGER IF EXISTS
                trg_model_artifact_requires_succeeded_training
            ON ai_control_plane.model_artifacts
            """
        )
    )
    op.execute(
        sa.text(
            """
            DROP FUNCTION IF EXISTS
                ai_control_plane.require_succeeded_training()
            """
        )
    )
    op.drop_constraint(
        "uq_ai_training_run_request_key",
        "training_runs",
        schema="ai_control_plane",
        type_="unique",
    )
    op.drop_column(
        "training_runs",
        "data_classification",
        schema="ai_control_plane",
    )
    op.drop_column(
        "training_runs",
        "request_key",
        schema="ai_control_plane",
    )
    op.drop_column(
        "training_runs",
        "organization_context_id",
        schema="ai_control_plane",
    )
