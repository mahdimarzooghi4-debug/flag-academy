"""governed offline evaluation control plane

Revision ID: 0028
Revises: 0027
Create Date: 2026-10-07
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    legacy_evaluation_run_exists = connection.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                  FROM ai_control_plane.evaluation_runs
                 LIMIT 1
            )
            """
        )
    ).scalar_one()
    if legacy_evaluation_run_exists:
        raise RuntimeError(
            "cannot harden Offline Evaluation with existing Evaluation Runs"
        )

    op.add_column(
        "evaluation_runs",
        sa.Column(
            "organization_context_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        schema="ai_control_plane",
    )
    op.add_column(
        "evaluation_runs",
        sa.Column("request_key", sa.String(160), nullable=False),
        schema="ai_control_plane",
    )
    op.add_column(
        "evaluation_runs",
        sa.Column("data_classification", sa.String(64), nullable=False),
        schema="ai_control_plane",
    )
    op.create_unique_constraint(
        "uq_ai_evaluation_run_request_key",
        "evaluation_runs",
        ["organization_context_id", "request_key"],
        schema="ai_control_plane",
    )

    op.add_column(
        "evaluation_results",
        sa.Column("metrics_byte_size", sa.BigInteger(), nullable=False),
        schema="ai_control_plane",
    )
    op.add_column(
        "evaluation_results",
        sa.Column(
            "attested_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        schema="ai_control_plane",
    )
    op.create_check_constraint(
        "ck_ai_evaluation_metrics_byte_size",
        "evaluation_results",
        "metrics_byte_size >= 0",
        schema="ai_control_plane",
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION
                ai_control_plane.require_valid_evaluation_run_lineage()
            RETURNS trigger
            LANGUAGE plpgsql
            AS 'DECLARE
                training_dataset_version_id uuid;
                model_organization_context_id uuid;
                evaluation_organization_context_id uuid;
            BEGIN
                SELECT mv.dataset_version_id, tr.organization_context_id
                  INTO training_dataset_version_id,
                       model_organization_context_id
                  FROM ai_control_plane.model_versions mv
                  JOIN ai_control_plane.training_runs tr
                    ON tr.id = mv.training_run_id
                 WHERE mv.id = NEW.model_version_id;

                IF training_dataset_version_id IS NULL THEN
                    RAISE EXCEPTION
                        ''evaluation run requires existing Model Version'';
                END IF;

                SELECT d.organization_context_id
                  INTO evaluation_organization_context_id
                  FROM ai_control_plane.dataset_versions dv
                  JOIN ai_control_plane.datasets d
                    ON d.id = dv.dataset_id
                 WHERE dv.id = NEW.evaluation_dataset_version_id;

                IF evaluation_organization_context_id IS NULL THEN
                    RAISE EXCEPTION
                        ''evaluation run requires existing Evaluation Dataset Version'';
                END IF;

                IF NEW.organization_context_id IS DISTINCT FROM
                    model_organization_context_id
                THEN
                    RAISE EXCEPTION
                        ''evaluation run Model Version organization mismatch'';
                END IF;

                IF NEW.organization_context_id IS DISTINCT FROM
                    evaluation_organization_context_id
                THEN
                    RAISE EXCEPTION
                        ''evaluation run Dataset Version organization mismatch'';
                END IF;

                IF NEW.evaluation_dataset_version_id IS NOT DISTINCT FROM
                    training_dataset_version_id
                THEN
                    RAISE EXCEPTION
                        ''evaluation Dataset Version must differ from Training Dataset Version'';
                END IF;

                RETURN NEW;
            END;';
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_evaluation_run_requires_valid_lineage
            BEFORE INSERT ON ai_control_plane.evaluation_runs
            FOR EACH ROW
            EXECUTE FUNCTION
                ai_control_plane.require_valid_evaluation_run_lineage()
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION
                ai_control_plane.require_succeeded_evaluation_result()
            RETURNS trigger
            LANGUAGE plpgsql
            AS 'DECLARE
                current_state text;
            BEGIN
                SELECT state
                  INTO current_state
                  FROM ai_control_plane.evaluation_run_states
                 WHERE evaluation_run_id = NEW.evaluation_run_id
                 ORDER BY sequence DESC
                 LIMIT 1;

                IF current_state IS DISTINCT FROM ''SUCCEEDED'' THEN
                    RAISE EXCEPTION
                        ''evaluation result requires SUCCEEDED Evaluation Run'';
                END IF;

                RETURN NEW;
            END;';
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_evaluation_result_requires_succeeded_run
            BEFORE INSERT ON ai_control_plane.evaluation_results
            FOR EACH ROW
            EXECUTE FUNCTION
                ai_control_plane.require_succeeded_evaluation_result()
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DROP TRIGGER IF EXISTS
                trg_evaluation_result_requires_succeeded_run
            ON ai_control_plane.evaluation_results
            """
        )
    )
    op.execute(
        sa.text(
            """
            DROP FUNCTION IF EXISTS
                ai_control_plane.require_succeeded_evaluation_result()
            """
        )
    )
    op.execute(
        sa.text(
            """
            DROP TRIGGER IF EXISTS
                trg_evaluation_run_requires_valid_lineage
            ON ai_control_plane.evaluation_runs
            """
        )
    )
    op.execute(
        sa.text(
            """
            DROP FUNCTION IF EXISTS
                ai_control_plane.require_valid_evaluation_run_lineage()
            """
        )
    )

    op.drop_constraint(
        "ck_ai_evaluation_metrics_byte_size",
        "evaluation_results",
        schema="ai_control_plane",
        type_="check",
    )
    op.drop_column(
        "evaluation_results",
        "attested_at",
        schema="ai_control_plane",
    )
    op.drop_column(
        "evaluation_results",
        "metrics_byte_size",
        schema="ai_control_plane",
    )

    op.drop_constraint(
        "uq_ai_evaluation_run_request_key",
        "evaluation_runs",
        schema="ai_control_plane",
        type_="unique",
    )
    op.drop_column(
        "evaluation_runs",
        "data_classification",
        schema="ai_control_plane",
    )
    op.drop_column(
        "evaluation_runs",
        "request_key",
        schema="ai_control_plane",
    )
    op.drop_column(
        "evaluation_runs",
        "organization_context_id",
        schema="ai_control_plane",
    )
