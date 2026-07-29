# Task 14 — Implement Agent Orchestrator and Live Request Routing

## Goal

Route live user requests and meeting facts to model roles, capabilities, and responses while preserving deterministic execution guards.

## Context

The user wants silent transcription by default and on-demand interactive questions/actions during a meeting.

## Scope
### In Scope
- Context builder interface.
- Model role router integration.
- User request lifecycle.
- Structured intent/capability proposal.
- Plan handoff to capability engine.
- Read-only answer path.
- Interactive/transcription mode behavior.
- Correlation across transcript, model call, plan, and tool calls.

### Out of Scope
- Final meeting profile prompt content.
- Long-term memory graph.
- General desktop control.

## Dependencies

- Tasks 06-11, 13.

## Implementation Steps

1. Define orchestrator input/output commands.
2. Build context from active session/profile and recent segments.
3. Call configured analysis/realtime adapter through role interface.
4. Validate structured model output.
5. Route capability proposals to deterministic engine.
6. Return answer/display events.
7. Handle cancellation and fallback.

## Files Likely Touched

- orchestrator service
- context builder
- model role ports
- structured output validators
- tests

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- Models cannot invoke connectors directly.
- Unregistered capabilities/tools are rejected.
- Transcription mode remains silent unless explicitly invoked.

## Testing Requirements

- Read-only question path.
- Capability proposal path.
- Malformed model output.
- Disabled/manual/auto policy integration.
- Mode permission checks.
- Cancellation and provider failure.

## Acceptance Criteria

- [ ] A live request can produce an answer or a validated capability plan.
- [ ] Tool execution remains behind policy engine.
- [ ] Every stage is correlated in the timeline.

## Documentation Updates

- Document orchestration flow and structured model contract.

## Handoff Notes

Use fake model adapters in most tests; vendor prompt tuning belongs in the next task.
