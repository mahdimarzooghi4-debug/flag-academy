"""Necessary-only Evidence final-review mandate preconditions.

NO caller may use a True result as authority to start or finalize Evidence review.
An Evidence-owned human issuance/revocation policy and transactional validation of
the issuing authority have NOT been approved or wired. The SQL decision barrier
continues to reject all classroom UNDER_REVIEW/ACCEPTED/REJECTED transitions.
"""
from datetime import datetime

from app.academy.assessor_grants_policy import GrantWindow, active_class_grant
from app.academy.models import AssessorClassGrant, ClassAssessorObservation
from app.evidence.classroom_review_safety import classroom_review_lineage_independent
from app.evidence.models import (
    ClassroomFinalEvidenceReviewMandate,
    ClassroomObservationSourceReview,
    EvidenceCase,
    EvidenceInterpretation,
)
from app.identity.auth import ActorContext


def final_review_mandate_prerequisites(
    *,
    actor: ActorContext,
    mandate: ClassroomFinalEvidenceReviewMandate,
    case: EvidenceCase,
    source: ClassAssessorObservation,
    source_review: ClassroomObservationSourceReview,
    interpretation: EvidenceInterpretation,
    current_class_grant: AssessorClassGrant,
    current_org_assessor_membership_confirmed: bool,
    class_status: str,
    cohort_status: str,
    current_source_sha256: str,
    expected_case_version: int,
    now: datetime,
    expected_case_status: str = "SUBMITTED",
) -> bool:
    """Check scope, temporal validity, live class access and reviewer separation.

    A True value is necessary, NEVER sufficient: issuer authority, mandate
    issuance/revocation audit, verified persisted membership and DB locks are
    separate unapproved/unimplemented requirements, not inferred here.
    """
    if (
        now.tzinfo is None
        or now.utcoffset() is None
        or "ASSESSOR" not in actor.roles
        or not current_org_assessor_membership_confirmed
        or mandate.version < 1
        or mandate.organization_context_id != actor.organization_context_id
        or mandate.evidence_case_id != case.id
        or mandate.class_offering_id != source.class_offering_id
        or mandate.reviewer_person_id != actor.person_id
        or mandate.issued_at.tzinfo is None
        or mandate.issued_at.utcoffset() is None
        or mandate.issued_at > now
        or mandate.starts_at.tzinfo is None
        or mandate.starts_at.utcoffset() is None
        or mandate.ends_at.tzinfo is None
        or mandate.ends_at.utcoffset() is None
        or mandate.revoked_at is not None
        or not (mandate.starts_at <= now < mandate.ends_at)
        or current_class_grant.organization_context_id != actor.organization_context_id
        or current_class_grant.class_offering_id != source.class_offering_id
        or current_class_grant.assessor_person_id != actor.person_id
    ):
        return False

    if not active_class_grant(
        GrantWindow(
            current_class_grant.starts_at,
            current_class_grant.ends_at,
            current_class_grant.revoked_at,
        ),
        now=now,
        class_status=class_status,
        cohort_status=cohort_status,
    ):
        return False

    return classroom_review_lineage_independent(
        case=case,
        source=source,
        source_review=source_review,
        interpretation=interpretation,
        final_reviewer_id=actor.person_id,
        expected_version=expected_case_version,
        current_source_sha256=current_source_sha256,
        expected_case_status=expected_case_status,
    )
