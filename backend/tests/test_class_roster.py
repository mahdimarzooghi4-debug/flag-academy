from pathlib import Path

from app.main import app


def test_roster_is_a_get_only_read_model() -> None:
    path = "/api/v1/class-offerings/{class_offering_id}/roster"
    paths = app.openapi()["paths"]
    assert path in paths
    assert set(paths[path]) == {"get"}
    schemas = app.openapi()["components"]["schemas"]
    props = schemas["ClassRosterResponse"]["properties"]
    assert {
        "class_offering_id",
        "cohort_id",
        "title",
        "primary_capability_version_id",
        "members",
        "instructor_person_ids",
    }.issubset(props)


def test_roster_is_tenant_scoped_and_fail_closed() -> None:
    source = Path("app/academy/api.py").read_text()
    roster = source.split("async def class_offering_roster(", 1)[1]
    assert "Cohort.organization_context_id == actor.organization_context_id" in roster
    assert "InstructorAssignment.class_offering_id == offering.id" in roster
    assert "CohortMembership.cohort_id == cohort.id" in roster
    assert '"ACADEMY_ADMIN" in actor.roles' in roster
    assert '"INSTRUCTOR" in actor.roles' in roster
    assert '"CANDIDATE" in actor.roles' in roster
    assert "actor.person_id in instructor_rows" in roster
    assert "person_id == actor.person_id" in roster
    assert 'raise AppError("CLASS_NOT_FOUND"' in roster
    assert '"ASSESSOR" in actor.roles' in roster
    assert "await has_live_assessor_class_access(" in roster
    # The global role is not itself sufficient for Academy class visibility.


def test_roster_has_no_evidence_gate_or_attendance_write_side_effect() -> None:
    source = Path("app/academy/api.py").read_text()
    roster = source.split("async def class_offering_roster(", 1)[1]
    for forbidden in (
        "db.add(",
        "db.commit(",
        "record_event(",
        "AttendanceRecord(",
        "CapabilityClaim",
        "GateAssessment",
    ):
        assert forbidden not in roster
