from pathlib import Path

import pytest

from app.academy.domain import AttendanceStatus, attendance_resulting_version
from app.academy.models import AttendanceRecord, AttendanceRevision
from app.main import app


def test_attendance_vocabulary_is_minimal_and_explicit() -> None:
    assert {item.value for item in AttendanceStatus} == {
        "PRESENT",
        "ABSENT",
    }


def test_missing_attendance_is_not_absent_and_create_starts_at_version_one() -> None:
    assert (
        attendance_resulting_version(
            current_status=None,
            current_version=0,
            requested_status="ABSENT",
        )
        == 1
    )
    with pytest.raises(ValueError):
        attendance_resulting_version(
            current_status=None,
            current_version=1,
            requested_status="ABSENT",
        )


def test_same_attendance_status_is_a_noop_for_business_version() -> None:
    assert (
        attendance_resulting_version(
            current_status="PRESENT",
            current_version=4,
            requested_status="PRESENT",
        )
        == 4
    )
    assert (
        attendance_resulting_version(
            current_status="PRESENT",
            current_version=4,
            requested_status="ABSENT",
        )
        == 5
    )


def test_attendance_models_keep_current_truth_and_append_only_revision_lineage() -> None:
    current = set(AttendanceRecord.__table__.c.keys())
    revisions = set(AttendanceRevision.__table__.c.keys())

    assert {
        "version",
        "organization_context_id",
        "session_id",
        "person_id",
        "status",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    }.issubset(current)
    assert {
        "attendance_record_id",
        "organization_context_id",
        "session_id",
        "person_id",
        "expected_version",
        "prior_version",
        "prior_status",
        "resulting_version",
        "resulting_status",
        "changed_by",
        "changed_at",
        "idempotency_key",
    }.issubset(revisions)


def test_attendance_migration_enforces_status_identity_and_audit_constraints() -> None:
    source = Path(
        "alembic/versions/0030_attendance_foundation.py"
    ).read_text()

    assert "attendance_records" in source
    assert "attendance_revisions" in source
    assert "PRESENT" in source
    assert "ABSENT" in source
    assert "uq_attendance_record_session_person" in source
    assert "uq_attendance_revision_idempotency" in source
    assert "expected_version >= 0" in source
    assert "resulting_version >= 1" in source
    assert "reject_attendance_revision_mutation" in source
    assert "trg_attendance_revisions_immutable" in source
    assert "BEFORE UPDATE OR DELETE" in source


def test_attendance_http_contract_is_admin_mutation_and_role_scoped_read() -> None:
    paths = app.openapi()["paths"]
    list_path = "/api/v1/sessions/{session_id}/attendance"
    mutate_path = "/api/v1/sessions/{session_id}/attendance/{person_id}"

    assert list_path in paths
    assert set(paths[list_path]) == {"get"}
    assert mutate_path in paths
    assert set(paths[mutate_path]) == {"post"}

    schemas = app.openapi()["components"]["schemas"]
    request = schemas["AttendanceMutationRequest"]
    props = request["properties"]
    required = set(request["required"])

    assert props["status"]["enum"] == ["PRESENT", "ABSENT"]
    assert {"status", "expected_version", "idempotency_key"}.issubset(required)


def test_attendance_api_has_no_formal_growth_mutation_dependency() -> None:
    source = Path("app/academy/api.py").read_text()

    assert 'require_role("ACADEMY_ADMIN")' in source
    assert 'require_role("ACADEMY_ADMIN", "INSTRUCTOR", "ASSESSOR")' in source
    assert "academy.attendance_recorded.v1" in source
    assert "academy.attendance_corrected.v1" in source

    for forbidden in (
        "app.evidence",
        "app.patterns",
        "app.flag_profile",
        "app.gate_assessment",
        "CapabilityClaim",
        "GateAssessment",
        "EvidenceCase",
        "BehaviourPattern",
    ):
        assert forbidden not in source


def test_attendance_model_has_no_score_or_progression_fields() -> None:
    fields = set(AttendanceRecord.__table__.c.keys())
    for forbidden in (
        "score",
        "percentage",
        "grade",
        "gpa",
        "proof_state",
        "learning_state",
        "gate_state",
    ):
        assert forbidden not in fields
