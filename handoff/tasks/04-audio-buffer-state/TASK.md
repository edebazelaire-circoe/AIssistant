# Task 04 — Implement Audio Capture, Circular Buffer, and Agent State Machine

## Goal

Create the local sensing spine and deterministic operating-mode transitions.

## Context

V1 needs microphone off, standby, transcription, and interactive modes with visible state and bounded pre-roll audio.

## Scope
### In Scope
- Audio input port and one initial adapter.
- Bounded circular buffer.
- Agent state machine and transition commands.
- Audio-level and state events.
- Hard microphone stop.
- Recorded-audio fake for tests.

### Out of Scope
- Wake-word inference.
- Speech transcription.
- UI beyond a minimal debug harness.

## Dependencies

- Tasks 02-03.

## Implementation Steps

1. Define audio frame contract and monotonic timestamps.
2. Implement capture service and fake source.
3. Implement ring buffer with configurable duration.
4. Implement legal state transitions and side effects.
5. Emit runtime events.
6. Expose a minimal control API.

## Files Likely Touched

- audio application service
- audio adapter
- ring buffer
- state machine
- tests

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- `MIC_OFF` must release/stop capture.
- `STANDBY` cannot invoke remote adapters.
- Buffer memory must be bounded.

## Testing Requirements

- Ring-buffer wraparound and ordering.
- State transition matrix.
- Mic-off no-frame test.
- Standby no-remote-call test.
- Dropped-frame diagnostics.

## Acceptance Criteria

- [ ] Real or fixture audio produces level events.
- [ ] Buffer returns correct pre-roll frames.
- [ ] Illegal transitions return typed errors.
- [ ] Mic-off stops capture deterministically.

## Documentation Updates

- Document audio adapter and state-transition API.

## Handoff Notes

Avoid coupling the buffer format to a specific transcription SDK.
