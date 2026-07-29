# Task 05 — Implement Wake-Word Enrollment and Detection Adapter

## Goal

Allow configurable activation/deactivation phrases, multiple enrollment recordings, and observable wake detections.

## Context

The user wants to record several variants of “Hey Jarvis” and test detection behavior from the Inspector.

## Scope
### In Scope
- Wake detector port.
- Enrollment sample recording/storage metadata.
- Activation and deactivation phrase configuration.
- One initial detector adapter or intentionally simple V1 baseline.
- Detection score/event.
- False-wake labeling.

### Out of Scope
- Speaker identity recognition.
- Cloud standby audio.
- Production biometric model training.

## Dependencies

- Task 04.

## Implementation Steps

1. Lock detector choice in a small ADR.
2. Define enrollment and detector interfaces.
3. Capture and validate enrollment samples.
4. Implement detector over live frames/buffer.
5. Map activation/deactivation events to state commands.
6. Emit diagnostics and scores.

## Files Likely Touched

- wake domain/application modules
- detector adapter
- enrollment storage
- tests

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- Stay local in standby.
- Enrollment audio is separate from meeting recordings.
- Deletion must be supported.

## Testing Requirements

- Phrase configuration validation.
- Multiple-sample enrollment.
- Recorded positive/negative fixtures.
- False-wake labeling persistence.
- Activation/deactivation transition tests.

## Acceptance Criteria

- [ ] Operator can record, list, and delete samples.
- [ ] Wake detection emits score and timestamp.
- [ ] Activation/deactivation causes expected transitions.
- [ ] No standby audio leaves the local detector path.

## Documentation Updates

- Document detector limitations and tuning parameters.
- Resolve wake-engine item in open questions.

## Handoff Notes

A modest, testable detector is better than a magical but opaque V1. Keep the port replaceable.
