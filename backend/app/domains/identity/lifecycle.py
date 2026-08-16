from __future__ import annotations

from app.domains.identity.models import LifecycleState

_LEGAL_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.RESERVED: {LifecycleState.SIGNED},
    LifecycleState.SIGNED: {LifecycleState.PRINTED},
    LifecycleState.PRINTED: {LifecycleState.PRINT_VERIFIED, LifecycleState.PRINT_REJECTED},
    LifecycleState.PRINT_VERIFIED: {LifecycleState.RECONCILED, LifecycleState.PRINT_REJECTED},
    LifecycleState.RECONCILED: {LifecycleState.ACTIVATED, LifecycleState.PRINT_REJECTED},
    LifecycleState.ACTIVATED: set(),
    LifecycleState.PRINT_REJECTED: set(),
}


class IllegalLifecycleTransitionError(ValueError):
    def __init__(self, current: LifecycleState, requested: LifecycleState) -> None:
        self.current = current
        self.requested = requested
        super().__init__(
            f"Illegal identity lifecycle transition: {current.value} -> {requested.value}"
        )


def assert_legal_transition(current: LifecycleState, requested: LifecycleState) -> None:
    allowed = _LEGAL_TRANSITIONS.get(current, set())
    if requested not in allowed:
        raise IllegalLifecycleTransitionError(current, requested)


def legal_next_states(current: LifecycleState) -> set[LifecycleState]:
    return set(_LEGAL_TRANSITIONS.get(current, set()))


def is_terminal(state: LifecycleState) -> bool:
    return not _LEGAL_TRANSITIONS.get(state, set())
