# Task 20 — Run End-to-End Hardening, Diagnostics, and Local Release Packaging

## Goal

Prove the reference scenario, inject failures, close documentation gaps, and package a reproducible V1 build.

## Context

The final gate is an observable meeting-to-roadmap workflow under manual and automatic policies.

## Scope
### In Scope
- Full scenario automation.
- Performance measurements.
- Fault injection.
- Secret/redaction audit.
- Workbook safety regression.
- Local packaging/start scripts.
- Operator/developer documentation.
- Final implementation report.

### Out of Scope
- Smartwatch.
- Symphonia production connector.
- Speaker identity.
- General autonomous desktop agent.

## Dependencies

- Tasks 01-19 complete.

## Implementation Steps

1. Assemble recorded two-speaker scenario.
2. Run manual-policy end-to-end test.
3. Run automatic-policy end-to-end test.
4. Inject speech, model, tool, file-lock, and UI reconnect failures.
5. Measure latency budgets.
6. Run security/redaction checks.
7. Package reproducible local build.
8. Update all docs and produce final report.

## Files Likely Touched

- e2e suite
- fixtures
- packaging scripts
- operator guide
- final report

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- No flaky hidden manual step in the reference scenario.
- Do not claim unsupported realtime/model access.
- Release package excludes secrets and enrollment audio.

## Testing Requirements

- Reference scenario manual.
- Reference scenario automatic.
- Mic-off/standby privacy.
- Provider failures.
- Diarization overlap.
- Ambiguous roadmap row.
- Workbook lock/write failure.
- UI reconnect/replay.
- Performance and redaction gates.

## Acceptance Criteria

- [ ] Reference scenarios pass repeatedly.
- [ ] A fresh operator can start the system from docs.
- [ ] Inspector shows full state, plan, calls, and result.
- [ ] All known failures produce actionable diagnostics.
- [ ] Final report lists residual risks and deferred features.

## Documentation Updates

- Validate every document against implementation.
- Mark all resolved open questions.
- Produce final implementation report.

## Handoff Notes

After this task, the V1 is ready for internal capability testing, not production deployment.
