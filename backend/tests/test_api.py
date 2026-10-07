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
    assert "/api/v1/pattern-candidates/{candidate_id}/lineage" in paths
    assert "/api/v1/pattern-candidates/{candidate_id}/review" in paths
    assert "post" in paths["/api/v1/pattern-evidence-sets"]
    assert "post" in paths["/api/v1/pattern-candidates"]
    assert "get" in paths["/api/v1/pattern-candidates/{candidate_id}/lineage"]
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


def test_pattern_command_api_uses_evidence_owned_contract_boundary() -> None:
    from pathlib import Path

    api_source = Path("app/patterns/api.py").read_text()
    adapter_source = Path("app/patterns/evidence_reader.py").read_text()
    application_source = Path("app/patterns/application.py").read_text()
    contract_source = Path("app/evidence/contracts.py").read_text()

    assert "SqlAcceptedEvidenceReader" in api_source
    assert "from app.evidence" not in api_source
    assert "from app.evidence.models" not in adapter_source
    assert "from app.evidence.contracts import" in adapter_source
    assert "from app.evidence.models" in contract_source
    assert "from app.evidence" not in application_source


def test_pattern_candidate_lineage_is_assessor_only_and_pre_review() -> None:
    from pathlib import Path

    source = Path("app/patterns/api.py").read_text()
    segment = source.split(
        '@router.get(\n    "/pattern-candidates/{candidate_id}/lineage"',
        1,
    )[1].split(
        '@router.post(\n    "/pattern-candidates/{candidate_id}/review"',
        1,
    )[0]

    assert 'require_role("ASSESSOR")' in segment
    assert "_candidate_review_lineage_response" in segment

    schemas = app.openapi()["components"]["schemas"]
    props = schemas["PatternCandidateReviewLineageResponse"]["properties"]
    assert set(props) == {
        "organization_context_id",
        "subject_person_id",
        "candidate",
        "evidence_set",
        "evidence",
    }
    evidence_props = schemas["PatternEvidenceLineageResponse"]["properties"]
    assert "relationship" in evidence_props
    assert "source_lineage" in evidence_props


def test_flag_profile_assessor_contract_is_exposed() -> None:
    paths = app.openapi()["paths"]

    expected = {
        "/api/v1/profile-update-cases",
        "/api/v1/profile-update-cases/{case_id}",
        "/api/v1/profile-update-cases/{case_id}/lineage",
        "/api/v1/profile-update-cases/{case_id}/request-review",
        "/api/v1/profile-update-cases/{case_id}/approve",
        "/api/v1/profile-update-cases/{case_id}/apply",
        "/api/v1/people/{person_id}/flag-profile",
        "/api/v1/profile/claims/{claim_id}/lineage",
    }
    assert expected.issubset(paths)
    assert "post" in paths["/api/v1/profile-update-cases"]
    assert "get" in paths["/api/v1/profile-update-cases"]
    assert "post" in paths["/api/v1/profile-update-cases/{case_id}/request-review"]
    assert "post" in paths["/api/v1/profile-update-cases/{case_id}/approve"]
    assert "post" in paths["/api/v1/profile-update-cases/{case_id}/apply"]


def test_flag_profile_http_contract_has_no_direct_patch() -> None:
    paths = app.openapi()["paths"]
    for path in (
        "/api/v1/profile-update-cases",
        "/api/v1/people/{person_id}/flag-profile",
        "/api/v1/profile/claims/{claim_id}/lineage",
    ):
        assert "patch" not in paths[path]


def test_profile_update_api_exposes_explicit_human_review_values() -> None:
    schemas = app.openapi()["components"]["schemas"]

    create_props = schemas["ProfileUpdateCaseCreateRequest"]["properties"]
    assert "proposed_claim_state" in create_props
    assert "proposed_level" in create_props
    assert "patterns" in create_props
    assert "expected_version" in create_props
    assert "idempotency_key" in create_props

    approval_props = schemas["ProfileUpdateApprovalRequest"]["properties"]
    assert "reviewed_claim_state" in approval_props
    assert "reviewed_level" in approval_props
    assert "reviewed_proven_scope" in approval_props
    assert "reviewed_evidence_recency" in approval_props
    assert "reviewed_confidence_in_claim" in approval_props
    assert "reviewed_next_evidence_needed" in approval_props
    assert "rationale" in approval_props
    assert "expected_version" in approval_props
    assert "idempotency_key" in approval_props


def test_profile_update_lineage_contract_reaches_observation_and_source() -> None:
    schemas = app.openapi()["components"]["schemas"]

    lineage_props = schemas["CapabilityClaimLineageResponse"]["properties"]
    assert "claim" in lineage_props
    assert "patterns" in lineage_props

    pattern_props = schemas["ProfileUpdatePatternLineageResponse"]["properties"]
    assert "relationship" in pattern_props
    assert "evidence" in pattern_props

    evidence_props = schemas["ProfileUpdateEvidenceLineageResponse"]["properties"]
    for field in (
        "evidence_case_id",
        "interpretation_id",
        "interpretation_version",
        "source_observation_id",
        "source_context",
        "source_reference",
        "observation_type",
    ):
        assert field in evidence_props


def test_flag_profile_api_is_assessor_only_and_local_snapshot_based() -> None:
    from pathlib import Path

    source = Path("app/flag_profile/api.py").read_text()

    assert 'require_role("ASSESSOR")' in source
    assert "app.patterns.models" not in source
    assert "app.evidence" not in source
    assert "ProfileUpdatePatternEvidence" in source
    assert "CapabilityClaimPattern" in source
    assert "GateAssessment" not in source
    assert "ResponsibilityRecommendation" not in source


def test_flag_profile_read_contract_has_no_overall_score() -> None:
    schemas = app.openapi()["components"]["schemas"]
    props = schemas["CapabilityClaimResponse"]["properties"]

    assert "state" in props
    assert "level" in props
    assert "proven_scope" in props
    assert "evidence_recency" in props
    assert "next_evidence_needed" in props
    assert "score" not in props
    assert "overall_score" not in props


def test_candidate_flag_profile_projection_is_exposed() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/me/flag-profile" in paths
    assert "get" in paths["/api/v1/me/flag-profile"]

    schemas = app.openapi()["components"]["schemas"]
    claim_props = schemas["CandidateCapabilityClaimResponse"]["properties"]
    assert set(claim_props) == {
        "capability_id",
        "state",
        "level",
        "proven_scope",
        "evidence_recency",
        "next_evidence_needed",
        "updated_at",
    }

    hidden = {
        "id",
        "version",
        "subject_person_id",
        "organization_context_id",
        "confidence_in_claim",
        "reviewed_at",
        "reviewed_by",
        "source_profile_update_case_id",
        "patterns",
        "rationale",
        "review_rationale",
        "created_by",
        "applied_by",
        "idempotency_key",
        "lineage",
    }
    assert hidden.isdisjoint(claim_props)


def test_candidate_flag_profile_projection_is_self_scoped_and_fail_closed() -> None:
    from pathlib import Path

    source = Path("app/flag_profile/api.py").read_text()
    segment = source.split(
        '@router.get(\n    "/me/flag-profile"',
        1,
    )[1].split(
        '@router.get(\n    "/people/{person_id}/flag-profile"',
        1,
    )[0]

    assert 'require_role("CANDIDATE")' in segment
    assert "FlagProfile.organization_context_id" in segment
    assert "FlagProfile.subject_person_id == actor.person_id" in segment
    assert "CapabilityClaim.organization_context_id" in segment
    assert "CapabilityClaim.subject_person_id == actor.person_id" in segment

    for forbidden in (
        "ProfileUpdateCase",
        "ProfileUpdatePattern",
        "ProfileUpdatePatternEvidence",
        "CapabilityClaimPattern",
        "reviewed_by",
        "review_rationale",
        "source_profile_update_case_id",
        "confidence_in_claim",
        "source_observation_id",
        "source_reference",
        "interpretation_id",
    ):
        assert forbidden not in segment


def test_candidate_flag_profile_has_no_overall_score_or_gate_state() -> None:
    schemas = app.openapi()["components"]["schemas"]
    claim_props = schemas["CandidateCapabilityClaimResponse"]["properties"]
    track_props = schemas["CandidateFlagProfileTrackResponse"]["properties"]

    assert "score" not in claim_props
    assert "overall_score" not in claim_props
    assert "gate_state" not in claim_props
    assert "responsibility_state" not in claim_props
    assert "score" not in track_props
    assert "overall_score" not in track_props



def test_profile_review_request_requires_idempotency_key() -> None:
    schemas = app.openapi()["components"]["schemas"]
    props = schemas["ProfileUpdateReviewRequest"]["properties"]
    required = set(schemas["ProfileUpdateReviewRequest"]["required"])

    assert "expected_version" in props
    assert "idempotency_key" in props
    assert {"expected_version", "idempotency_key"}.issubset(required)


def test_candidate_gate_projection_is_exposed_with_strict_allowlist() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/me/gate-assessments" in paths
    assert "get" in paths["/api/v1/me/gate-assessments"]

    schemas = app.openapi()["components"]["schemas"]
    props = schemas["CandidateGateResponse"]["properties"]
    assert set(props) == {
        "gate_code",
        "gate_name",
        "status",
        "evidence_gaps",
        "remediation_status",
    }

    hidden = {
        "id",
        "version",
        "organization_context_id",
        "subject_person_id",
        "gate_assessment_id",
        "gate_definition_version_id",
        "profile_snapshot_id",
        "profile_snapshot_version",
        "reviewer_id",
        "reviewed_by",
        "opened_by",
        "rationale",
        "review_rationale",
        "decision_rationale",
        "trace_id",
        "idempotency_key",
        "source_reference",
        "source_observation_id",
        "interpretation_id",
        "lineage",
        "risk_patterns",
        "supporting_patterns",
        "contradictory_patterns",
    }
    assert hidden.isdisjoint(props)


def test_candidate_gate_projection_endpoint_is_self_scoped_candidate_only() -> None:
    from pathlib import Path

    source = Path("app/gate_assessment/api.py").read_text()
    segment = source.split(
        '@router.get(\n    "/me/gate-assessments"',
        1,
    )[1]

    assert 'require_role("CANDIDATE")' in segment
    assert "organization_context_id=actor.organization_context_id" in segment
    assert "subject_person_id=actor.person_id" in segment

    for forbidden in (
        "GateReviewDecision",
        "GateReassessmentDecision",
        "GateSnapshotEvidenceRef",
        "GateSnapshotPatternRef",
        "rationale",
        "reviewer_id",
        "source_reference",
        "interpretation_id",
    ):
        assert forbidden not in segment


def test_gate_assessor_http_contract_is_exposed_and_human_only() -> None:
    paths = app.openapi()["paths"]

    expected = {
        "/api/v1/gate-assessments",
        "/api/v1/gate-assessments/{assessment_id}/reviews",
        "/api/v1/gate-reviews/{review_id}/pre-decision",
        "/api/v1/gate-reviews/{review_id}/decision",
    }
    assert expected.issubset(paths)
    assert "get" in paths["/api/v1/gate-assessments"]
    assert "post" in paths["/api/v1/gate-assessments/{assessment_id}/reviews"]
    assert "get" in paths["/api/v1/gate-reviews/{review_id}/pre-decision"]
    assert "post" in paths["/api/v1/gate-reviews/{review_id}/decision"]

    schemas = app.openapi()["components"]["schemas"]
    decision_props = schemas["CompleteGateReviewRequest"]["properties"]
    decision_enum = decision_props["decision_state"]["enum"]
    assert decision_enum == ["PASS_CONFIRMED", "FAIL"]
    assert "rationale" in decision_props
    assert "expected_version" in decision_props
    assert "expected_gate_definition_version_id" in decision_props
    assert "expected_profile_snapshot_id" in decision_props
    assert "expected_profile_snapshot_version" in decision_props


def test_gate_assessor_api_uses_existing_governed_commands() -> None:
    from pathlib import Path

    source = Path("app/gate_assessment/api.py").read_text()

    assert 'require_role("ASSESSOR")' in source
    assert "open_gate_review(" in source
    assert "load_assessor_pre_decision_read(" in source
    assert "complete_gate_review(" in source
    assert "FlagProfileSnapshotReader(db)" in source

    for forbidden in (
        "assessment.state =",
        "GateReviewDecision(",
        "GateProfileSnapshot(",
        "CapabilityClaim",
        "ResponsibilityRecommendation",
    ):
        assert forbidden not in source


def test_gate_assessor_pre_decision_schema_keeps_lineage_out_of_candidate_schema() -> None:
    schemas = app.openapi()["components"]["schemas"]
    assessor_props = schemas["GateEvidenceLineageResponse"]["properties"]
    candidate_props = schemas["CandidateGateResponse"]["properties"]

    assert "source_reference" in assessor_props
    assert "source_observation_id" in assessor_props
    assert "interpretation_id" in assessor_props

    assert "source_reference" not in candidate_props
    assert "source_observation_id" not in candidate_props
    assert "interpretation_id" not in candidate_props
    assert "reviewer_id" not in candidate_props
    assert "rationale" not in candidate_props
