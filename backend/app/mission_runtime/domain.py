from copy import deepcopy
from enum import StrEnum
from typing import Any


class MissionInstanceStatus(StrEnum):
    CREATED = "CREATED"
    ELIGIBILITY_CHECK = "ELIGIBILITY_CHECK"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED_WORLD_STATE = "FAILED_WORLD_STATE"
    TIME_EXPIRED = "TIME_EXPIRED"
    ABORTED = "ABORTED"
    WITHDRAWN = "WITHDRAWN"
    INVALIDATED = "INVALIDATED"


class MissionAssignmentStatus(StrEnum):
    ASSIGNED = "ASSIGNED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ScheduledEffectStatus(StrEnum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    CANCELLED = "CANCELLED"


class MissionActionType(StrEnum):
    REQUEST_INFORMATION = "REQUEST_INFORMATION"
    COMMUNICATE = "COMMUNICATE"
    DECIDE = "DECIDE"
    ESCALATE = "ESCALATE"
    DELEGATE = "DELEGATE"
    CHANGE_SCOPE = "CHANGE_SCOPE"
    ALLOCATE_RESOURCE = "ALLOCATE_RESOURCE"
    RUN_EXPERIMENT = "RUN_EXPERIMENT"
    NO_ACTION = "NO_ACTION"


TERMINAL_STATUSES = frozenset(
    {
        MissionInstanceStatus.COMPLETED,
        MissionInstanceStatus.FAILED_WORLD_STATE,
        MissionInstanceStatus.TIME_EXPIRED,
        MissionInstanceStatus.ABORTED,
        MissionInstanceStatus.WITHDRAWN,
        MissionInstanceStatus.INVALIDATED,
    }
)

ALLOWED_RUNTIME_TRANSITIONS: dict[
    MissionInstanceStatus, frozenset[MissionInstanceStatus]
] = {
    MissionInstanceStatus.CREATED: frozenset({MissionInstanceStatus.ELIGIBILITY_CHECK}),
    MissionInstanceStatus.ELIGIBILITY_CHECK: frozenset({MissionInstanceStatus.READY}),
    MissionInstanceStatus.READY: frozenset({MissionInstanceStatus.RUNNING}),
    MissionInstanceStatus.RUNNING: TERMINAL_STATUSES,
    MissionInstanceStatus.COMPLETED: frozenset(),
    MissionInstanceStatus.FAILED_WORLD_STATE: frozenset(),
    MissionInstanceStatus.TIME_EXPIRED: frozenset(),
    MissionInstanceStatus.ABORTED: frozenset(),
    MissionInstanceStatus.WITHDRAWN: frozenset(),
    MissionInstanceStatus.INVALIDATED: frozenset(),
}

RESERVED_WORLD_NAMESPACES = frozenset({"profile", "evidence", "competency", "gate"})
RESERVED_ACTOR_STATE_KEYS = frozenset(
    {"profile", "evidence", "competency", "gate", "world_state"}
)


def runtime_transition_allowed(current: str, target: str) -> bool:
    current_status = MissionInstanceStatus(current)
    target_status = MissionInstanceStatus(target)
    return target_status in ALLOWED_RUNTIME_TRANSITIONS[current_status]


def apply_world_effect(
    world_state: dict[str, Any],
    effect: dict[str, Any],
) -> dict[str, Any]:
    forbidden = RESERVED_WORLD_NAMESPACES.intersection(effect)
    if forbidden:
        names = ", ".join(sorted(forbidden))
        raise ValueError(f"Runtime effect cannot mutate reserved namespaces: {names}")

    next_state = deepcopy(world_state)
    for namespace, patch in effect.items():
        if not isinstance(patch, dict):
            raise ValueError("Runtime effects must be namespace objects.")
        current = next_state.get(namespace, {})
        if current is None:
            current = {}
        if not isinstance(current, dict):
            raise ValueError("World-state namespaces must be objects.")
        merged = deepcopy(current)
        merged.update(deepcopy(patch))
        next_state[namespace] = merged
    return next_state


def apply_actor_effect(
    actor_state: dict[str, Any],
    effect: dict[str, Any],
) -> dict[str, Any]:
    forbidden = RESERVED_ACTOR_STATE_KEYS.intersection(effect)
    if forbidden:
        names = ", ".join(sorted(forbidden))
        raise ValueError(f"Actor effect cannot mutate reserved keys: {names}")

    next_state = deepcopy(actor_state)
    for key, value in effect.items():
        next_state[key] = deepcopy(value)
    return next_state


ALLOWED_ASSIGNMENT_TRANSITIONS: dict[
    MissionAssignmentStatus, frozenset[MissionAssignmentStatus]
] = {
    MissionAssignmentStatus.ASSIGNED: frozenset(
        {MissionAssignmentStatus.STARTED, MissionAssignmentStatus.CANCELLED}
    ),
    MissionAssignmentStatus.STARTED: frozenset(
        {MissionAssignmentStatus.COMPLETED, MissionAssignmentStatus.CANCELLED}
    ),
    MissionAssignmentStatus.COMPLETED: frozenset(),
    MissionAssignmentStatus.CANCELLED: frozenset(),
}


def assignment_transition_allowed(current: str, target: str) -> bool:
    current_status = MissionAssignmentStatus(current)
    target_status = MissionAssignmentStatus(target)
    return target_status in ALLOWED_ASSIGNMENT_TRANSITIONS[current_status]


CANDIDATE_EVENT_PAYLOAD_ALLOWLIST: dict[str, frozenset[str]] = {
    "mission.status_changed": frozenset(
        {"from_status", "to_status", "mission_version_id", "assignment_id"}
    ),
    "mission.eligibility_passed": frozenset({"assignment_id", "checks"}),
    "mission.started": frozenset(
        {"assignment_id", "mission_version_id", "mission_code"}
    ),
    "information.disclosed": frozenset({"label", "content", "access"}),
    "communication.sent": frozenset(
        {"actor_key", "communication_code", "utterance"}
    ),
    "actor.responded": frozenset(
        {
            "actor_key",
            "communication_code",
            "reply",
            "actor_state_version_before",
            "actor_state_version_after",
        }
    ),
    "escalation.requested": frozenset(
        {"actor_key", "escalation_code", "rationale"}
    ),
    "escalation.accepted": frozenset(
        {
            "actor_key",
            "escalation_code",
            "response",
            "world_version_before",
            "world_version_after",
            "actor_state_version_before",
            "actor_state_version_after",
        }
    ),
    "scheduled_effect.created": frozenset(
        {"effect_code", "label", "due_at"}
    ),
    "simulation.time_advanced": frozenset(
        {"from_time", "to_time"}
    ),
    "scheduled_effect.applied": frozenset(
        {
            "effect_code",
            "label",
            "due_at",
            "world_version_before",
            "world_version_after",
        }
    ),
    "no_action.committed": frozenset(
        {
            "no_action_code",
            "reasoning",
            "simulation_time_before",
            "simulation_time_after",
        }
    ),
    "mission.time_expired": frozenset(
        {
            "from_status",
            "to_status",
            "effect_code",
            "expired_at",
        }
    ),
    "decision.committed": frozenset({"decision_code"}),
    "mission.completed": frozenset({"from_status", "to_status"}),
}

CANDIDATE_OBSERVATION_PAYLOAD_ALLOWLIST: dict[str, frozenset[str]] = {
    "MISSION_STARTED": frozenset({"assignment_id", "mission_version_id"}),
    "INFORMATION_REQUESTED": frozenset({"label", "access"}),
    "ACTOR_RESPONSE_OBSERVED": frozenset(
        {
            "actor_key",
            "communication_code",
            "actor_state_version_before",
            "actor_state_version_after",
        }
    ),
    "ESCALATION_OBSERVED": frozenset(
        {
            "actor_key",
            "escalation_code",
            "world_version_before",
            "world_version_after",
            "actor_state_version_before",
            "actor_state_version_after",
        }
    ),
    "SCHEDULED_EFFECT_OBSERVED": frozenset(
        {
            "effect_code",
            "due_at",
            "world_version_before",
            "world_version_after",
        }
    ),
    "NO_ACTION_OBSERVED": frozenset(
        {
            "no_action_code",
            "simulation_time_before",
            "simulation_time_after",
            "world_version_before",
            "world_version_after",
        }
    ),
    "MISSION_TIME_EXPIRED": frozenset(
        {
            "effect_code",
            "expired_at",
            "world_version_before",
            "world_version_after",
        }
    ),
    "DECISION_COMMITTED": frozenset(
        {"decision_code", "world_version_before", "world_version_after"}
    ),
}


def project_candidate_visible_state(
    world_state: dict[str, Any],
    visible_paths: list[str],
) -> dict[str, Any]:
    projected: dict[str, Any] = {}
    for raw_path in visible_paths:
        parts = [part for part in raw_path.split(".") if part]
        if not parts:
            continue

        source: Any = world_state
        found = True
        for part in parts:
            if not isinstance(source, dict) or part not in source:
                found = False
                break
            source = source[part]
        if not found:
            continue

        target = projected
        for part in parts[:-1]:
            existing = target.get(part)
            if not isinstance(existing, dict):
                existing = {}
                target[part] = existing
            target = existing
        target[parts[-1]] = deepcopy(source)

    return projected


def candidate_event_visible(event_type: str) -> bool:
    return event_type in CANDIDATE_EVENT_PAYLOAD_ALLOWLIST


def candidate_event_payload(
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    allowed = CANDIDATE_EVENT_PAYLOAD_ALLOWLIST.get(event_type, frozenset())
    return {key: deepcopy(payload[key]) for key in allowed if key in payload}


def candidate_observation_visible(observation_type: str) -> bool:
    return observation_type in CANDIDATE_OBSERVATION_PAYLOAD_ALLOWLIST


def candidate_observation_payload(
    observation_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    allowed = CANDIDATE_OBSERVATION_PAYLOAD_ALLOWLIST.get(
        observation_type,
        frozenset(),
    )
    return {key: deepcopy(payload[key]) for key in allowed if key in payload}
