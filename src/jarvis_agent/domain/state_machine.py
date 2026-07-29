from __future__ import annotations

from dataclasses import dataclass

from jarvis_agent.domain.models import AgentState, Diagnostic, ErrorCode


_ALLOWED: dict[AgentState, set[AgentState]] = {
    AgentState.MIC_OFF: {AgentState.STANDBY},
    AgentState.STANDBY: {AgentState.MIC_OFF, AgentState.TRANSCRIBING},
    AgentState.TRANSCRIBING: {
        AgentState.MIC_OFF,
        AgentState.STANDBY,
        AgentState.INTERACTIVE,
        AgentState.ERROR_RECOVERABLE,
    },
    AgentState.INTERACTIVE: {
        AgentState.MIC_OFF,
        AgentState.STANDBY,
        AgentState.TRANSCRIBING,
        AgentState.ERROR_RECOVERABLE,
    },
    AgentState.ERROR_RECOVERABLE: {
        AgentState.MIC_OFF,
        AgentState.STANDBY,
        AgentState.TRANSCRIBING,
        AgentState.INTERACTIVE,
    },
}


@dataclass(slots=True)
class StateTransition:
    previous: AgentState
    current: AgentState
    reason: str


class InvalidTransition(ValueError):
    def __init__(self, previous: AgentState, requested: AgentState):
        super().__init__(f"Illegal transition {previous} -> {requested}")
        self.diagnostic = Diagnostic(
            code=ErrorCode.INVALID_TRANSITION,
            message=str(self),
            component="state_machine",
            retryable=False,
            suggested_action="Use an explicit legal intermediate state.",
            details={"previous": previous.value, "requested": requested.value},
        )


class AgentStateMachine:
    def __init__(self, initial: AgentState = AgentState.MIC_OFF) -> None:
        self._state = initial
        self._previous_safe_state = initial

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def previous_safe_state(self) -> AgentState:
        return self._previous_safe_state

    def can_transition(self, requested: AgentState) -> bool:
        return requested == self._state or requested in _ALLOWED[self._state]

    def transition(self, requested: AgentState, reason: str) -> StateTransition:
        previous = self._state
        if requested == previous:
            return StateTransition(previous=previous, current=requested, reason=reason)
        if requested not in _ALLOWED[previous]:
            raise InvalidTransition(previous, requested)
        if requested != AgentState.ERROR_RECOVERABLE:
            self._previous_safe_state = requested
        self._state = requested
        return StateTransition(previous=previous, current=requested, reason=reason)

    def recover(self, reason: str) -> StateTransition:
        target = self._previous_safe_state
        if self._state != AgentState.ERROR_RECOVERABLE:
            raise InvalidTransition(self._state, target)
        return self.transition(target, reason)
