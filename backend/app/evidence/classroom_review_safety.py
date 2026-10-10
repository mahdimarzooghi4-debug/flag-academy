"""Necessary lineage and separation-of-duties checks for future classroom Evidence review.

This module is NOT a reviewer mandate, role permission, policy approval or API.
Even a passing result MUST NOT authorize review start or a final Evidence decision.
The live, Evidence-owned final reviewer appointment policy is unresolved.
"""

from uuid import UUID

from app.academy.models import ClassAssessorObservation
from app.evidence.models import (
    ClassroomObservationSourceReview,
    EvidenceCase,
    EvidenceInterpretation,
)


def classroom_review_lineage_independent(
    *,
    case: EvidenceCase,
    source: ClassAssessorObservation,
    source_review: ClassroomObservationSourceReview,
    interpretation: EvidenceInterpretation,
    final_reviewer_id: UUID,
    expected_version: int,
    current_source_sha256: str,
) -> bool:
    """Check necessary immutable lineage, identity separation and version only.

    Caller must separately attest a *live, explicitly issued Evidence final-review
    mandate* under transaction locks. Academy class access / ASSESSOR does not
    grant final Evidence authority. No current code path grants that mandate.
    """
    provenance = case.provenance
    if not isinstance(provenance, dict):
        return False
    independent_persons = (
        source.observer_person_id,
        source_review.reviewer_person_id,
        interpretation.created_by,
        source.candidate_person_id,
    )
    if final_reviewer_id in independent_persons:
        return False
    if provenance.get("created_by_person_id") in (None, str(final_reviewer_id)):
        return False
    return (
        case.status == "SUBMITTED"
        and case.version == expected_version
        and case.source_context == "CLASSROOM_OBSERVATION"
        and case.integrity_state == "SOURCE_REVIEWED"
        and case.candidate_visible is False
        and case.accepted_at is None
        and case.rejected_at is None
        and case.organization_context_id == source.organization_context_id
        and case.organization_context_id == source_review.organization_context_id
        and case.source_observation_id == source.id
        and case.subject_person_id == source.candidate_person_id
        and case.observed_fact == source.observed_fact
        and case.occurred_at == source.observed_at
        and interpretation.evidence_case_id == case.id
        and interpretation.status == "ACTIVE"
        and interpretation.version_number == 1
        and interpretation.ai_contribution == "NONE"
        and interpretation.created_by == source_review.reviewer_person_id
        and source_review.decision == "VERIFIED"
        and source_review.source_observation_id == source.id
        and source_review.class_offering_id == source.class_offering_id
        and source_review.session_id == source.session_id
        and source_review.observer_person_id == source.observer_person_id
        and source_review.subject_person_id == source.candidate_person_id
        and source_review.source_sha256 == current_source_sha256
        and provenance.get("source_review_id") == str(source_review.id)
        and provenance.get("source_sha256") == current_source_sha256
        and provenance.get("class_offering_id") == str(source.class_offering_id)
        and provenance.get("session_id") == str(source.session_id)
        and provenance.get("created_by_person_id")
        == str(source_review.reviewer_person_id)
        and provenance.get("source_grant_id") == str(source.grant_id)
        and provenance.get("source_grant_version") == source.grant_version
        and provenance.get("reviewer_grant_id")
        == str(source_review.reviewer_grant_id)
        and provenance.get("reviewer_grant_version")
        == source_review.reviewer_grant_version
    )
