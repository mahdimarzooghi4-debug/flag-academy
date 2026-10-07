"""human model promotion governance

Revision ID: 0029
Revises: 0028
Create Date: 2026-10-07
"""

import sqlalchemy as sa

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    legacy_decision_exists = connection.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                  FROM ai_control_plane.model_promotion_decisions
                 LIMIT 1
            )
            """
        )
    ).scalar_one()
    if legacy_decision_exists:
        raise RuntimeError(
            "cannot harden Human Promotion with existing Promotion Decisions"
        )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION
                ai_control_plane.require_valid_human_promotion_lineage()
            RETURNS trigger
            LANGUAGE plpgsql
            AS 'DECLARE
                evaluated_model_version_id uuid;
                evaluation_organization_context_id uuid;
                promoted_model_organization_context_id uuid;
                prior_model_organization_context_id uuid;
                current_state text;
                result_exists boolean;
            BEGIN
                SELECT er.model_version_id, er.organization_context_id
                  INTO evaluated_model_version_id,
                       evaluation_organization_context_id
                  FROM ai_control_plane.evaluation_runs er
                 WHERE er.id = NEW.evaluation_run_id;

                IF evaluated_model_version_id IS NULL THEN
                    RAISE EXCEPTION
                        ''promotion requires existing Evaluation Run'';
                END IF;

                IF NEW.model_version_id IS DISTINCT FROM
                    evaluated_model_version_id
                THEN
                    RAISE EXCEPTION
                        ''promotion Model Version must match Evaluation Run'';
                END IF;

                SELECT tr.organization_context_id
                  INTO promoted_model_organization_context_id
                  FROM ai_control_plane.model_versions mv
                  JOIN ai_control_plane.training_runs tr
                    ON tr.id = mv.training_run_id
                 WHERE mv.id = NEW.model_version_id;

                IF promoted_model_organization_context_id IS DISTINCT FROM
                    evaluation_organization_context_id
                THEN
                    RAISE EXCEPTION
                        ''promotion Model Version organization mismatch'';
                END IF;

                SELECT ers.state
                  INTO current_state
                  FROM ai_control_plane.evaluation_run_states ers
                 WHERE ers.evaluation_run_id = NEW.evaluation_run_id
                 ORDER BY ers.sequence DESC
                 LIMIT 1;

                IF current_state IS DISTINCT FROM ''SUCCEEDED'' THEN
                    RAISE EXCEPTION
                        ''promotion requires SUCCEEDED Evaluation Run'';
                END IF;

                SELECT EXISTS (
                    SELECT 1
                      FROM ai_control_plane.evaluation_results result
                     WHERE result.evaluation_run_id = NEW.evaluation_run_id
                )
                  INTO result_exists;

                IF result_exists IS DISTINCT FROM TRUE THEN
                    RAISE EXCEPTION
                        ''promotion requires immutable Evaluation Result'';
                END IF;

                IF NEW.prior_active_model_version_id IS NOT NULL THEN
                    SELECT tr.organization_context_id
                      INTO prior_model_organization_context_id
                      FROM ai_control_plane.model_versions mv
                      JOIN ai_control_plane.training_runs tr
                        ON tr.id = mv.training_run_id
                     WHERE mv.id = NEW.prior_active_model_version_id;

                    IF prior_model_organization_context_id IS NULL THEN
                        RAISE EXCEPTION
                            ''prior active Model Version does not exist'';
                    END IF;

                    IF prior_model_organization_context_id IS DISTINCT FROM
                        evaluation_organization_context_id
                    THEN
                        RAISE EXCEPTION
                            ''prior active Model Version organization mismatch'';
                    END IF;
                END IF;

                RETURN NEW;
            END;';
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_model_promotion_requires_valid_lineage
            BEFORE INSERT ON ai_control_plane.model_promotion_decisions
            FOR EACH ROW
            EXECUTE FUNCTION
                ai_control_plane.require_valid_human_promotion_lineage()
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DROP TRIGGER IF EXISTS
                trg_model_promotion_requires_valid_lineage
            ON ai_control_plane.model_promotion_decisions
            """
        )
    )
    op.execute(
        sa.text(
            """
            DROP FUNCTION IF EXISTS
                ai_control_plane.require_valid_human_promotion_lineage()
            """
        )
    )
