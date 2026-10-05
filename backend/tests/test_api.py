from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Trace-Id"]


def test_learning_business_contract_is_exposed() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/classes/{class_offering_id}/learning" in paths
    assert "/api/v1/learning-units/{learning_unit_id}/start" in paths
    assert "/api/v1/learning-units/{learning_unit_id}/complete" in paths
    assert "/api/v1/practice-units/{learning_unit_id}/attempts" in paths
    assert "/api/v1/practice-attempts/{practice_attempt_id}/feedback" in paths
    assert "/api/v1/assignments/{assignment_id}/submissions" in paths
    assert "/api/v1/submissions/{submission_id}/feedback" in paths
    assert "post" in paths["/api/v1/assignments/{assignment_id}/submissions"]
    assert "post" in paths["/api/v1/submissions/{submission_id}/feedback"]


def test_practice_attempt_contract_exposes_replay_lineage() -> None:
    schemas = app.openapi()["components"]["schemas"]
    props = schemas["PracticeAttemptResponse"]["properties"]
    assert "attempt_number" in props
    assert "replay_of_attempt_id" in props


def test_learning_unit_contract_exposes_practice_kind() -> None:
    schemas = app.openapi()["components"]["schemas"]
    props = schemas["LearningUnitResponse"]["properties"]
    assert "practice_kind" in props


def test_mission_design_contract_is_exposed() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/studio/mission-templates" in paths
    assert "/api/v1/studio/mission-templates/{template_id}/versions" in paths
    assert "/api/v1/studio/mission-versions/{version_id}/validate-definition" in paths
    assert "/api/v1/studio/mission-versions/{version_id}/pilot" in paths
    assert "/api/v1/studio/mission-versions/{version_id}/mark-validated" in paths
    assert "/api/v1/studio/mission-versions/{version_id}/activate" in paths
    assert "/api/v1/studio/mission-versions/{version_id}/retire" in paths


def test_mission_runtime_contract_is_exposed() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/missions/active" in paths
    assert "/api/v1/me/mission-instances" in paths
    assert "/api/v1/missions/{version_id}/instances" in paths
    assert "/api/v1/mission-instances/{instance_id}" in paths
    assert "/api/v1/mission-instances/{instance_id}/actions" in paths

    schemas = app.openapi()["components"]["schemas"]
    action_props = schemas["MissionActionRequest"]["properties"]
    assert "expected_world_version" in action_props
    assert "idempotency_key" in action_props
    instance_props = schemas["MissionInstanceResponse"]["properties"]
    assert "world_state_version" in instance_props
    assert "observations" in instance_props
