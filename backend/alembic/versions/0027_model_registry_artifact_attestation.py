"""model registry and artifact attestation

Revision ID: 0027
Revises: 0026
Create Date: 2026-10-07
"""

import sqlalchemy as sa

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $
            BEGIN
                IF EXISTS (
                    SELECT 1
                      FROM ai_control_plane.model_versions
                     LIMIT 1
                ) THEN
                    RAISE EXCEPTION
                        'cannot add artifact attestation to existing Model Versions';
                END IF;
            END
            $;
            """
        )
    )

    op.add_column(
        "model_versions",
        sa.Column("attestation_sha256", sa.String(64), nullable=False),
        schema="ai_control_plane",
    )
    op.add_column(
        "model_versions",
        sa.Column("attestation_byte_size", sa.BigInteger(), nullable=False),
        schema="ai_control_plane",
    )
    op.add_column(
        "model_versions",
        sa.Column(
            "attested_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        schema="ai_control_plane",
    )
    op.create_check_constraint(
        "ck_ai_model_version_attestation_sha256",
        "model_versions",
        "attestation_sha256 ~ '^[0-9a-f]{64}$'",
        schema="ai_control_plane",
    )
    op.create_check_constraint(
        "ck_ai_model_version_attestation_byte_size",
        "model_versions",
        "attestation_byte_size >= 0",
        schema="ai_control_plane",
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION
                ai_control_plane.require_valid_model_version_lineage()
            RETURNS trigger
            LANGUAGE plpgsql
            AS 'DECLARE
                artifact_training_run_id uuid;
                artifact_sha256 text;
                artifact_byte_size bigint;
                run_dataset_version_id uuid;
                run_model_family text;
                current_state text;
            BEGIN
                SELECT training_run_id, content_sha256, byte_size
                  INTO artifact_training_run_id,
                       artifact_sha256,
                       artifact_byte_size
                  FROM ai_control_plane.model_artifacts
                 WHERE id = NEW.model_artifact_id;

                IF artifact_training_run_id IS NULL THEN
                    RAISE EXCEPTION
                        ''model version requires existing model artifact'';
                END IF;

                SELECT dataset_version_id, model_family
                  INTO run_dataset_version_id, run_model_family
                  FROM ai_control_plane.training_runs
                 WHERE id = artifact_training_run_id;

                SELECT state
                  INTO current_state
                  FROM ai_control_plane.training_run_states
                 WHERE training_run_id = artifact_training_run_id
                 ORDER BY sequence DESC
                 LIMIT 1;

                IF current_state IS DISTINCT FROM ''SUCCEEDED'' THEN
                    RAISE EXCEPTION
                        ''model version requires SUCCEEDED Training Run'';
                END IF;

                IF NEW.training_run_id IS DISTINCT FROM
                    artifact_training_run_id
                THEN
                    RAISE EXCEPTION
                        ''model version Training Run lineage mismatch'';
                END IF;

                IF NEW.dataset_version_id IS DISTINCT FROM
                    run_dataset_version_id
                THEN
                    RAISE EXCEPTION
                        ''model version Dataset Version lineage mismatch'';
                END IF;

                IF NEW.model_family IS DISTINCT FROM run_model_family THEN
                    RAISE EXCEPTION
                        ''model version model family lineage mismatch'';
                END IF;

                IF NEW.attestation_sha256 IS DISTINCT FROM
                    artifact_sha256
                THEN
                    RAISE EXCEPTION
                        ''model version artifact digest mismatch'';
                END IF;

                IF NEW.attestation_byte_size IS DISTINCT FROM
                    artifact_byte_size
                THEN
                    RAISE EXCEPTION
                        ''model version artifact byte size mismatch'';
                END IF;

                RETURN NEW;
            END;';
            """
        )
    )
    op.execute(
        sa.text(
            """
            CREATE TRIGGER trg_model_version_requires_valid_lineage
            BEFORE INSERT ON ai_control_plane.model_versions
            FOR EACH ROW
            EXECUTE FUNCTION
                ai_control_plane.require_valid_model_version_lineage()
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DROP TRIGGER IF EXISTS
                trg_model_version_requires_valid_lineage
            ON ai_control_plane.model_versions
            """
        )
    )
    op.execute(
        sa.text(
            """
            DROP FUNCTION IF EXISTS
                ai_control_plane.require_valid_model_version_lineage()
            """
        )
    )
    op.drop_constraint(
        "ck_ai_model_version_attestation_byte_size",
        "model_versions",
        schema="ai_control_plane",
        type_="check",
    )
    op.drop_constraint(
        "ck_ai_model_version_attestation_sha256",
        "model_versions",
        schema="ai_control_plane",
        type_="check",
    )
    op.drop_column(
        "model_versions",
        "attested_at",
        schema="ai_control_plane",
    )
    op.drop_column(
        "model_versions",
        "attestation_byte_size",
        schema="ai_control_plane",
    )
    op.drop_column(
        "model_versions",
        "attestation_sha256",
        schema="ai_control_plane",
    )
