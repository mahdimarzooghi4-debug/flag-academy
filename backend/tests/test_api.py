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
    assert "/api/v1/mission-assignments" in paths
    assert "/api/v1/studio/mission-assignment-candidates" in paths
    assert "/api/v1/studio/mission-assignments" in paths
    assert "/api/v1/missions/active" in paths
    assert "/api/v1/me/mission-instances" in paths
    assert "/api/v1/missions/{version_id}/instances" in paths
    assert "/api/v1/mission-instances/{instance_id}" in paths
    assert "/api/v1/mission-instances/{instance_id}/actions" in paths
    assert "/api/v1/mission-instances/{instance_id}/advance-to-next-event" in paths

    schemas = app.openapi()["components"]["schemas"]
    assignment_props = schemas["MissionAssignmentCreateRequest"]["properties"]
    assert "candidate_id" in assignment_props
    assert "mission_version_id" in assignment_props
    start_props = schemas["MissionStartRequest"]["properties"]
    assert "assignment_id" in start_props
    catalog_props = schemas["MissionCatalogItem"]["properties"]
    assert "assignment_id" in catalog_props
    assert "assignment_status" in catalog_props

    action_props = schemas["MissionActionRequest"]["properties"]
    assert "expected_world_version" in action_props
    assert "expected_actor_version" in action_props
    assert "idempotency_key" in action_props
    instance_props = schemas["MissionInstanceResponse"]["properties"]
    assert "world_state_version" in instance_props
    assert "simulation_time" in instance_props
    assert "scheduled_effects" in instance_props
    assert "observations" in instance_props
    assert "actors" in instance_props
    assert "escalation_options" in instance_props
    assert "delegation_options" in instance_props
    assert "scope_change_options" in instance_props
    assert "resource_allocation_options" in instance_props
    assert "experiment_options" in instance_props
    assert "no_action_options" in instance_props
    assert "simulation_seed" not in instance_props
    scheduled_props = schemas["ScheduledEffectResponse"]["properties"]
    assert "due_at" in scheduled_props
    assert "trigger_mode" in scheduled_props

    advance_props = schemas["AdvanceSimulationRequest"]["properties"]
    assert "expected_world_version" in advance_props
    assert "idempotency_key" in advance_props


def test_evidence_engine_contract_is_exposed() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/evidence-cases" in paths
    assert "/api/v1/evidence-cases/{case_id}" in paths
    assert "/api/v1/me/evidence-cases" in paths
    assert "/api/v1/evidence-cases/{case_id}/submit" in paths
    assert "/api/v1/evidence-cases/{case_id}/reviews" in paths
    assert "/api/v1/evidence-cases/{case_id}/accept" in paths
    assert "/api/v1/evidence-cases/{case_id}/reject" in paths
    assert "/api/v1/evidence-cases/{case_id}/request-context" in paths
    assert "/api/v1/evidence-cases/{case_id}/candidate-response" in paths

    schemas = app.openapi()["components"]["schemas"]
    case_props = schemas["EvidenceCaseResponse"]["properties"]
    assert "source_observation_id" in case_props
    assert "source_independence_group" in case_props
    assert "interpretation" in case_props
    assert "reviews" in case_props
    assert "candidate_responses" in case_props

    candidate_props = schemas["CandidateEvidenceCaseResponse"]["properties"]
    assert "accepted_interpretation" in candidate_props
    assert "reviews" not in candidate_props
    assert "source_independence_group" not in candidate_props
    assert "provenance" not in candidate_props
    assert "source_runtime_event_id" not in candidate_props

    submit_props = schemas["EvidenceSubmitRequest"]["properties"]
    assert "expected_version" in submit_props
    assert "interpretation" in submit_props

    response_props = schemas["CandidateResponseCreate"]["properties"]
    assert "expected_version" in response_props
    assert "idempotency_key" in response_props

def test_pattern_read_contract_exposes_full_lineage() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/patterns" in paths
    assert "/api/v1/patterns/{pattern_id}/lineage" in paths
    assert "get" in paths["/api/v1/patterns"]
    assert "get" in paths["/api/v1/patterns/{pattern_id}/lineage"]

    schemas = app.openapi()["components"]["schemas"]
    lineage_props = schemas["ReviewedPatternLineageResponse"]["properties"]
    assert "candidate" in lineage_props
    assert "evidence_set" in lineage_props
    assert "review" in lineage_props
    assert "evidence" in lineage_props

    evidence_props = schemas["PatternEvidenceLineageResponse"]["properties"]
    assert "relationship" in evidence_props
    assert "evidence_case_id" in evidence_props
    assert "interpretation_id" in evidence_props
    assert "interpretation_version" in evidence_props
    assert "target_links" in evidence_props
    assert "source_lineage" in evidence_props

    source_props = schemas["PatternSourceLineageResponse"]["properties"]
    assert "source_observation_id" in source_props
    assert "source_context" in source_props
    assert "source_reference" in source_props
    assert "observation_type" in source_props


def test_pattern_read_api_keeps_evidence_boundary_snapshot_only() -> None:
    from pathlib import Path

    source = Path("app/patterns/api.py").read_text()
    assert "app.evidence" not in source
    assert "EvidenceCase" not in source
    assert "EvidenceInterpretation" not in source


def test_candidate_pattern_projection_is_safe() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/me/patterns" in paths
    assert "get" in paths["/api/v1/me/patterns"]

    schemas = app.openapi()["components"]["schemas"]
    props = schemas["CandidatePatternResponse"]["properties"]

    assert set(props) == {
        "id",
        "behaviour_code",
        "behaviour_description",
        "pattern_status",
        "scope",
        "reviewed_at",
        "updated_at",
    }

    for hidden_field in (
        "version",
        "subject_person_id",
        "organization_context_id",
        "reviewed_by",
        "rationale",
        "candidate",
        "review",
        "evidence",
        "evidence_set",
        "source_lineage",
        "created_by",
        "idempotency_key",
    ):
        assert hidden_field not in props


def test_candidate_pattern_projection_is_self_scoped_and_reviewed_only() -> None:
    from pathlib import Path

    source = Path("app/patterns/api.py").read_text()
    candidate_source = source.split(
        '@router.get("/me/patterns"',
        1,
    )[1].split('@router.get("/patterns"', 1)[0]

    assert 'require_role("CANDIDATE")' in candidate_source
    assert "BehaviourPattern.subject_person_id == actor.person_id" in candidate_source
    assert (
        "BehaviourPattern.organization_context_id"
        in candidate_source
    )
    assert "PatternReview" not in candidate_source
    assert "EvidenceSetMember" not in candidate_source
    assert "PatternCandidateEvidence" not in candidate_source
    assert "source_lineage" not in candidate_source


def test_pattern_command_contract_is_exposed() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/pattern-evidence-sets" in paths
    assert "/api/v1/pattern-candidates" in paths
    assert "/api/v1/pattern-candidates/{candidate_id}/review" in paths
    assert "post" in paths["/api/v1/pattern-evidence-sets"]
    assert "post" in paths["/api/v1/pattern-candidates"]
    assert "post" in paths["/api/v1/pattern-candidates/{candidate_id}/review"]

    schemas = app.openapi()["components"]["schemas"]

    evidence_set_props = schemas["EvidenceSetCreateRequest"]["properties"]
    assert "subject_person_id" in evidence_set_props
    assert "evidence_case_ids" in evidence_set_props
    assert "expected_version" in evidence_set_props
    assert "idempotency_key" in evidence_set_props

    candidate_props = schemas["PatternCandidateCreateRequest"]["properties"]
    assert "evidence_set_id" in candidate_props
    assert "proposed_pattern_status" in candidate_props
    assert "evidence" in candidate_props
    assert "expected_version" in candidate_props
    assert "idempotency_key" in candidate_props

    review_props = schemas["PatternReviewRequest"]["properties"]
    assert "resulting_pattern_status" in review_props
    assert "rationale" in review_props
    assert "expected_version" in review_props
    assert "idempotency_key" in review_props


def test_pattern_command_api_uses_evidence_reader_adapter_boundary() -> None:
    from pathlib import Path

    api_source = Path("app/patterns/api.py").read_text()
    adapter_source = Path("app/patterns/evidence_reader.py").read_text()
    application_source = Path("app/patterns/application.py").read_text()

    assert "SqlAcceptedEvidenceReader" in api_source
    assert "from app.evidence" not in api_source
    assert "from app.evidence" in adapter_source
    assert "from app.evidence" not in application_source

