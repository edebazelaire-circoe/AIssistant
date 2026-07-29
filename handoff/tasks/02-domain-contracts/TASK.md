# Task 02 — Define Domain Models, Events, and Typed Results

## Goal

Implement the stable domain contracts that all later adapters and UI panels depend on.

## Context

The Inspector requires replayable events, and capabilities/tools require typed input/output without vendor leakage.

## Scope
### In Scope
- Agent state enum and transition commands.
- Meeting session, transcript segment, speaker cluster, meeting fact, capability, policy, plan, tool call/result, artifact, diff, provider config, and model assignment types.
- Immutable runtime event envelope.
- Stable error/diagnostic type.
- Serialization boundaries.

### Out of Scope
- Business behavior beyond simple invariants.
- Database persistence.
- Vendor SDK mappings.

## Dependencies

- Task 01.

## Implementation Steps

1. Translate `docs/05-data-model.md` into code.
2. Define discriminated unions/enums for states, facts, policies, statuses, and errors.
3. Define typed result objects for all boundaries.
4. Add validators/serializers.
5. Create test builders/fixtures.

## Files Likely Touched

- domain model modules
- event modules
- diagnostic/result modules
- domain tests
- test builders

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- No UI or SDK imports.
- Prefer immutable values and explicit IDs.
- Keep `speaker_cluster_id` independent from `person_id`.

## Testing Requirements

- Round-trip serialization tests.
- Invalid state/value rejection tests.
- Secret-field exclusion tests.
- Backward-compatible event version field tests.

## Acceptance Criteria

- [ ] All core entities compile and serialize.
- [ ] Typed errors can represent retryable and non-retryable failures.
- [ ] No external SDK type appears in public domain contracts.

## Documentation Updates

- Update `docs/05-data-model.md` if code reveals necessary clarifications.

## Handoff Notes

These contracts are expensive to change later; keep them small, explicit, and versionable.
