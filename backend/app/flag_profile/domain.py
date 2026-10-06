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


def profile_claim_state_valid(value: str) -> bool:
    return value in {item.value for item in CapabilityClaimState}


def capability_level_valid(value: str) -> bool:
    return value in {item.value for item in CapabilityLevel}


def claim_pattern_relationship_valid(value: str) -> bool:
    return value in {item.value for item in ClaimPatternRelationship}


def profile_update_transition_allowed(current: str, target: str) -> bool:
    transitions = {
        ProfileUpdateCaseState.PROPOSED.value: {
            ProfileUpdateCaseState.REVIEW_REQUIRED.value,
            ProfileUpdateCaseState.AUTO_ELIGIBLE.value,
        },
        ProfileUpdateCaseState.REVIEW_REQUIRED.value: {
            ProfileUpdateCaseState.APPROVED.value,
        },
        ProfileUpdateCaseState.AUTO_ELIGIBLE.value: {
            ProfileUpdateCaseState.APPROVED.value,
        },
        ProfileUpdateCaseState.APPROVED.value: {
            ProfileUpdateCaseState.APPLIED.value,
        },
        ProfileUpdateCaseState.APPLIED.value: set(),
    }
    return target in transitions.get(current, set())
