from dataclasses import fields
from hashlib import sha256
from pathlib import Path

import pytest

from app.ai_control_plane.evaluation import (
    CompleteEvaluationRun,
    LocalFileMetricsArtifactReader,
    RequestEvaluationRun,
)
from app.ai_control_plane.models import (
    AIEvaluationResult,
    AIEvaluationRun,
)
from app.errors import AppError


def test_evaluation_request_input_does_not_accept_derived_training_lineage() -> None:
    names = {field.name for field in fields(RequestEvaluationRun)}
    assert names == {
        "organization_context_id",
        "request_key",
        "model_version_id",
        "evaluation_dataset_version_id",
        "evaluation_policy_key",
        "evaluation_policy_version",
        "requested_by_type",
        "requested_by_reference",
        "data_classification",
        "trace_id",
    }
    for forbidden in (
        "training_run_id",
        "training_dataset_version_id",
        "model_family",
        "model_artifact_id",
        "model_artifact_sha256",
        "model_artifact_byte_size",
    ):
        assert forbidden not in names


def test_evaluation_run_is_tenant_scoped_and_retry_identified() -> None:
    columns = set(AIEvaluationRun.__table__.c.keys())
    assert {
        "organization_context_id",
        "request_key",
        "data_classification",
        "model_version_id",
        "evaluation_dataset_version_id",
        "evaluation_policy_key",
        "evaluation_policy_version",
        "requested_by_type",
        "requested_by_reference",
        "requested_at",
    }.issubset(columns)

    migration = Path(
        "alembic/versions/0028_offline_evaluation_control_plane.py"
    ).read_text()
    assert "uq_ai_evaluation_run_request_key" in migration


def test_evaluation_result_persists_live_attestation() -> None:
    columns = set(AIEvaluationResult.__table__.c.keys())
    assert {
        "evaluation_run_id",
        "metrics_artifact_reference",
        "metrics_digest",
        "metrics_byte_size",
        "attested_at",
        "created_at",
    }.issubset(columns)


@pytest.mark.asyncio
async def test_local_metrics_reader_recomputes_sha256_and_size(
    tmp_path: Path,
) -> None:
    content = b'{"metric":"value"}\n'
    artifact = tmp_path / "evaluation.json"
    artifact.write_bytes(content)

    attestation = await LocalFileMetricsArtifactReader().attest(
        artifact_reference=str(artifact)
    )

    assert attestation.content_sha256 == sha256(content).hexdigest()
    assert attestation.byte_size == len(content)


@pytest.mark.asyncio
async def test_local_metrics_reader_rejects_remote_reference() -> None:
    with pytest.raises(AppError) as error:
        await LocalFileMetricsArtifactReader().attest(
            artifact_reference="https://evaluation.example/metrics.json"
        )

    assert (
        error.value.code
        == "AI_EVALUATION_ARTIFACT_REFERENCE_UNSUPPORTED"
    )


def test_offline_evaluation_derives_model_lineage_and_separates_datasets() -> None:
    source = Path("app/ai_control_plane/evaluation.py").read_text()
    request = source.split(
        "async def request_evaluation_run", 1
    )[1].split(
        "async def start_evaluation_run", 1
    )[0]

    assert "AITrainingRun.id == AIModelVersion.training_run_id" in source
    assert "AITrainingRun.organization_context_id" in source
    assert "AIDataset.organization_context_id" in source
    assert "model_version.dataset_version_id" in request
    assert "AI_EVALUATION_DATASET_NOT_INDEPENDENT" in request
    assert "pg_advisory_xact_lock" in request


def test_offline_evaluation_lifecycle_is_append_only_and_retry_safe() -> None:
    source = Path("app/ai_control_plane/evaluation.py").read_text()

    start = source.split(
        "async def start_evaluation_run", 1
    )[1].split(
        "async def complete_evaluation_run", 1
    )[0]
    complete = source.split(
        "async def complete_evaluation_run", 1
    )[1]

    assert "EvaluationRunState.REQUESTED.value" in start
    assert "EvaluationRunState.RUNNING.value" in start
    assert "Only REQUESTED Evaluation Runs can transition to RUNNING." in start
    assert "EvaluationRunState.SUCCEEDED.value" in complete
    assert "EvaluationRunState.FAILED.value" in complete
    assert "Only RUNNING Evaluation Runs can complete." in complete
    assert "AI_EVALUATION_TERMINAL_RETRY_MISMATCH" in complete
    assert "await artifact_reader.attest(" in complete
    assert "AI_EVALUATION_RESULT_ATTESTATION_FAILED" in complete
    assert "await db.commit()" not in source

    for forbidden in (
        "run.state =",
        "latest.state = outcome",
        "UPDATE ai_control_plane.evaluation_run_states",
        "DELETE FROM ai_control_plane.evaluation_run_states",
    ):
        assert forbidden not in source


def test_failed_evaluation_cannot_produce_result_or_promotion() -> None:
    source = Path("app/ai_control_plane/evaluation.py").read_text()
    complete = source.split(
        "async def complete_evaluation_run", 1
    )[1]

    assert (
        "Failed Evaluation Run cannot produce an evaluation result."
        in complete
    )
    assert "AIModelPromotionDecision(" not in source
    assert "runtime_activation" not in source.lower()


def test_evaluation_events_are_atomic_and_do_not_auto_decide() -> None:
    source = Path("app/ai_control_plane/evaluation.py").read_text()

    for event_type in (
        "ai.evaluation_run_requested.v1",
        "ai.evaluation_run_started.v1",
        "ai.evaluation_run_succeeded.v1",
        "ai.evaluation_run_failed.v1",
    ):
        assert event_type in source

    assert "record_event(" in source
    assert "await db.commit()" not in source

    for forbidden in (
        "pass_threshold",
        "passing_score",
        "quality_threshold",
        "fairness_threshold",
        "weighted_score",
        "overall_score",
        "winner",
        "pass_confirmed",
    ):
        assert forbidden not in source.lower()


def test_evaluation_database_enforces_lineage_and_success_before_result() -> None:
    migration = Path(
        "alembic/versions/0028_offline_evaluation_control_plane.py"
    ).read_text()

    assert "require_valid_evaluation_run_lineage" in migration
    assert "Model Version organization mismatch" in migration
    assert "Dataset Version organization mismatch" in migration
    assert (
        "evaluation Dataset Version must differ from Training Dataset Version"
        in migration
    )
    assert "require_succeeded_evaluation_result" in migration
    assert "current_state IS DISTINCT FROM ''SUCCEEDED''" in migration
    assert (
        "BEFORE INSERT ON ai_control_plane.evaluation_results"
        in migration
    )
    assert (
        "cannot harden Offline Evaluation with existing Evaluation Runs"
        in migration
    )


def test_evaluation_tables_keep_control_plane_foreign_keys_only() -> None:
    tables = (
        AIEvaluationRun.__table__,
        AIEvaluationResult.__table__,
    )
    targets = {
        fk.target_fullname
        for table in tables
        for fk in table.foreign_keys
    }
    assert targets
    assert all(
        target.startswith("ai_control_plane.")
        for target in targets
    )


def test_offline_evaluation_has_no_external_provider_or_runtime() -> None:
    source = Path("app/ai_control_plane/evaluation.py").read_text().lower()

    for forbidden in (
        "openai",
        "anthropic",
        "httpx",
        "requests.",
        "endpoint_url",
        "provider_token",
        "api_key",
        "transformers",
        "torch",
        "peft",
        "safetensors",
        "generate(",
    ):
        assert forbidden not in source


def test_completion_input_contains_only_result_evidence_not_training_lineage() -> None:
    names = {field.name for field in fields(CompleteEvaluationRun)}
    assert {
        "organization_context_id",
        "evaluation_run_id",
        "outcome",
        "actor_type",
        "actor_reference",
        "trace_id",
        "failure_code",
        "metrics_artifact_reference",
        "metrics_digest",
        "metrics_byte_size",
    } == names
    for forbidden in (
        "training_run_id",
        "training_dataset_version_id",
        "model_family",
        "model_artifact_id",
    ):
        assert forbidden not in names
