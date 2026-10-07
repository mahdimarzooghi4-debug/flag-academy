from pathlib import Path

from app.ai_control_plane.models import (
    AIModelArtifact,
    AITrainingRun,
    AITrainingRunState,
)


def test_training_run_is_tenant_scoped_and_idempotent() -> None:
    columns = set(AITrainingRun.__table__.c.keys())
    assert {
        "organization_context_id",
        "request_key",
        "data_classification",
        "dataset_version_id",
        "model_family",
        "training_recipe_digest",
        "requested_by_type",
        "requested_by_reference",
        "requested_at",
    }.issubset(columns)

    migration = Path(
        "alembic/versions/0026_ai_training_run_control_plane.py"
    ).read_text()
    assert "uq_ai_training_run_request_key" in migration


def test_training_control_plane_pins_exact_governed_dataset_version() -> None:
    source = Path("app/ai_control_plane/training.py").read_text()
    request_source = source.split(
        "async def request_training_run", 1
    )[1].split(
        "async def start_training_run", 1
    )[0]

    assert "AIDatasetVersion.id == command.dataset_version_id" in request_source
    assert (
        "AIDataset.organization_context_id"
        in request_source
        and "command.organization_context_id" in request_source
    )
    assert "AI_TRAINING_DATASET_VERSION_NOT_FOUND" in request_source
    assert "pg_advisory_xact_lock" in request_source
    assert "await db.commit()" not in request_source


def test_training_control_plane_lifecycle_is_append_only() -> None:
    source = Path("app/ai_control_plane/training.py").read_text()

    start_source = source.split(
        "async def start_training_run", 1
    )[1].split(
        "async def complete_training_run", 1
    )[0]
    complete_source = source.split(
        "async def complete_training_run", 1
    )[1]

    assert "TrainingRunState.REQUESTED.value" in start_source
    assert "TrainingRunState.RUNNING.value" in start_source
    assert "AITrainingRunState(" in start_source

    assert "TrainingRunState.SUCCEEDED.value" in complete_source
    assert "TrainingRunState.FAILED.value" in complete_source
    assert "Only RUNNING Training Runs can complete." in complete_source
    assert "AITrainingRunState(" in complete_source

    for forbidden in (
        "run.state =",
        "latest.state =",
        "UPDATE ai_control_plane.training_run_states",
        "DELETE FROM ai_control_plane.training_run_states",
    ):
        assert forbidden not in source


def test_training_success_persists_state_before_artifact() -> None:
    source = Path("app/ai_control_plane/training.py").read_text()
    complete_source = source.split(
        "async def complete_training_run", 1
    )[1]

    state_add = complete_source.index("db.add(state)")
    state_flush = complete_source.index("await db.flush()", state_add)
    artifact_create = complete_source.index("artifact = AIModelArtifact(")

    assert state_add < state_flush < artifact_create
    assert "AI_TRAINING_TERMINAL_RETRY_MISMATCH" in complete_source


def test_failed_training_cannot_produce_artifact_or_model_version() -> None:
    source = Path("app/ai_control_plane/training.py").read_text()
    complete_source = source.split(
        "async def complete_training_run", 1
    )[1]

    assert "Failed Training Run cannot produce a model artifact." in complete_source
    assert "AIModelVersion(" not in source
    assert "ModelVersion" not in source


def test_training_events_are_atomic_with_caller_transaction() -> None:
    source = Path("app/ai_control_plane/training.py").read_text()

    for event_type in (
        "ai.training_run_requested.v1",
        "ai.training_run_started.v1",
        "ai.training_run_succeeded.v1",
        "ai.training_run_failed.v1",
    ):
        assert event_type in source

    assert "record_event(" in source
    assert "await db.commit()" not in source


def test_training_control_plane_has_no_external_trainer_or_ai_runtime() -> None:
    source = Path("app/ai_control_plane/training.py").read_text().lower()

    for forbidden in (
        "openai",
        "anthropic",
        "httpx",
        "requests.",
        "endpoint_url",
        "training_endpoint",
        "provider_token",
        "api_key",
        "transformers",
        "torch",
        "peft",
        "safetensors",
        "generate(",
        "optimizer",
        "backward(",
    ):
        assert forbidden not in source


def test_training_database_requires_success_before_artifact() -> None:
    migration = Path(
        "alembic/versions/0026_ai_training_run_control_plane.py"
    ).read_text()

    assert "require_succeeded_training" in migration
    assert "current_state IS DISTINCT FROM ''SUCCEEDED''" in migration
    assert "BEFORE INSERT ON ai_control_plane.model_artifacts" in migration
    assert "uq_ai_training_run_request_key" in migration


def test_training_tables_keep_local_foreign_keys_only() -> None:
    tables = (
        AITrainingRun.__table__,
        AITrainingRunState.__table__,
        AIModelArtifact.__table__,
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
