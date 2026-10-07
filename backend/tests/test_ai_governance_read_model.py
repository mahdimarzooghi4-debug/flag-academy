from pathlib import Path

from app.main import app


def test_admin_ai_governance_contract_is_read_only() -> None:
    paths = app.openapi()["paths"]
    path = "/api/v1/admin/ai/governance"
    assert path in paths
    assert set(paths[path]) == {"get"}


def test_admin_ai_governance_response_omits_secret_or_artifact_location_surface() -> None:
    schemas = app.openapi()["components"]["schemas"]
    governance_props = schemas["AIGovernanceResponse"]["properties"]

    assert {
        "organization_context_id",
        "dataset_versions",
        "training_runs",
        "model_versions",
        "evaluation_runs",
        "promotion_decisions",
    } == set(governance_props)

    model_props = schemas["ModelVersionResponse"]["properties"]
    evaluation_props = schemas["EvaluationRunResponse"]["properties"]

    for forbidden in (
        "artifact_reference",
        "metrics_artifact_reference",
        "provider",
        "provider_token",
        "api_key",
        "endpoint",
        "credential",
        "secret",
    ):
        assert forbidden not in model_props
        assert forbidden not in evaluation_props


def test_admin_ai_governance_read_model_is_tenant_scoped() -> None:
    source = Path("app/ai_control_plane/read_models.py").read_text()

    assert (
        "AIDataset.organization_context_id"
        in source
    )
    assert (
        "AITrainingRun.organization_context_id"
        in source
    )
    assert (
        "AIEvaluationRun.organization_context_id"
        in source
    )
    assert (
        "AITrainingRun.organization_context_id\n"
        "                == organization_context_id"
        in source
    )


def test_admin_ai_governance_endpoint_requires_academy_admin() -> None:
    source = Path("app/ai_governance_api.py").read_text()

    assert 'require_role("ACADEMY_ADMIN")' in source
    assert "@router.get" in source
    assert "@router.post" not in source
    assert "@router.put" not in source
    assert "@router.patch" not in source
    assert "@router.delete" not in source


def test_ai_governance_ui_is_read_only_and_marks_authorization_boundary() -> None:
    source = Path(
        "../frontend/src/components/AIGovernanceWorkspace.tsx"
    ).read_text()

    assert "READ ONLY" in source
    assert "NO RUNTIME ACTIVATION" in source
    assert "این رکورد به‌تنهایی Runtime را فعال نمی‌کند" in source
    assert "<button" not in source
    assert "onClick" not in source
    assert "api_key" not in source.lower()
    assert "provider_token" not in source.lower()
