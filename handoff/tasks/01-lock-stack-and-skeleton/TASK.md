# Task 01 — Lock the Stack ADR and Create the Repository Skeleton

## Goal

Choose the implementation stack, record the decision, and create module boundaries that support the architecture without coupling core logic to vendors or Symphonia.

## Context

The session intentionally left the exact stack unresolved. A desktop-oriented UI, local runtime, audio/ML adapters, event transport, and Excel integration are required.

## Scope
### In Scope
- Evaluate one-process versus split-runtime options.
- Write an ADR covering language, UI shell, local service, IPC/event transport, persistence, and test frameworks.
- Create package/module skeletons for domain, application, adapters, connectors, UI, and tests.
- Add local development commands and baseline CI.

### Out of Scope
- Implement audio, model, Excel, or agent behavior.
- Integrate Symphonia.

## Dependencies

- Task 00.

## Implementation Steps

1. Inspect existing repository constraints if any.
2. Compare viable stacks against local audio, diarization, Excel preview, and UI needs.
3. Choose the smallest architecture that preserves replaceable adapters.
4. Write the ADR and update architecture docs if needed.
5. Create directories/packages and minimal build/test commands.
6. Add a smoke test and CI entrypoint.

## Files Likely Touched

- ADR directory
- package manifests
- source package roots
- test configuration
- CI configuration
- developer README

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- No vendor SDK in domain packages.
- No Symphonia dependency in core.
- Prefer a narrow sidecar boundary if multiple runtimes are chosen.

## Testing Requirements

- Build/typecheck/lint smoke test.
- Minimal test runner smoke test.
- Dependency-direction check placeholder or first enforceable rule.

## Acceptance Criteria

- [ ] ADR is explicit and justified.
- [ ] Fresh clone can install, build, and run tests.
- [ ] Module boundaries match `docs/02-architecture-spec.md`.
- [ ] No product behavior is prematurely hardcoded.

## Documentation Updates

- Add ADR and update setup instructions.
- Update `docs/09-open-questions.md` with resolved stack questions.

## Handoff Notes

Do not choose a split runtime merely because ML may use Python; prove the boundary is worth its operational cost.
