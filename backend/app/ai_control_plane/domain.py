from enum import StrEnum


class TrainingRunState(StrEnum):
    REQUESTED = "REQUESTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class EvaluationRunState(StrEnum):
    REQUESTED = "REQUESTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class PromotionDecisionState(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class GovernanceActorType(StrEnum):
    PERSON = "PERSON"
    SYSTEM = "SYSTEM"
