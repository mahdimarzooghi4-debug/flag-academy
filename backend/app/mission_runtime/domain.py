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
