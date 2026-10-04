from enum import StrEnum


class LearningUnitType(StrEnum):
    LESSON = "LESSON"
    EXERCISE = "EXERCISE"
    KNOWLEDGE_CHECK = "KNOWLEDGE_CHECK"
    RESOURCE = "RESOURCE"
    TUTOR_SESSION = "TUTOR_SESSION"


class LearningPhase(StrEnum):
    PRE_WORK = "PRE_WORK"
    IN_CLASS = "IN_CLASS"
    POST_CLASS = "POST_CLASS"
    PRACTICE = "PRACTICE"


class LearningUnitProgressState(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class AssignmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class SubmissionStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    FEEDBACK_PROVIDED = "FEEDBACK_PROVIDED"


class PracticeAttemptStatus(StrEnum):
    SUBMITTED = "SUBMITTED"
    FEEDBACK_PROVIDED = "FEEDBACK_PROVIDED"


class PracticeReplayState(StrEnum):
    WAITING_FOR_FEEDBACK = "WAITING_FOR_FEEDBACK"
    REPLAY_AVAILABLE = "REPLAY_AVAILABLE"
