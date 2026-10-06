from enum import StrEnum


class ProfileUpdateCaseState(StrEnum):
    PROPOSED = "PROPOSED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    AUTO_ELIGIBLE = "AUTO_ELIGIBLE"
    APPROVED = "APPROVED"
    APPLIED = "APPLIED"


class CapabilityClaimState(StrEnum):
    UNPROVEN = "UNPROVEN"
    EMERGING = "EMERGING"
    DEMONSTRATED = "DEMONSTRATED"
    PROVEN = "PROVEN"


class CapabilityLevel(StrEnum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"


class ClaimPatternRelationship(StrEnum):
    SUPPORTING = "SUPPORTING"
    CONTRADICTORY = "CONTRADICTORY"
