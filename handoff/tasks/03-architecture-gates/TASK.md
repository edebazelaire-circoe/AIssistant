# Task 03 — Add Architecture and Dependency Regression Gates

## Goal

Make the intended boundaries executable before behavior-heavy implementation begins.

## Context

The project depends on replaceable adapters and strict separation between core, vendors, connectors, UI, and future Symphonia integration.

## Scope
### In Scope
- Dependency direction tests.
- Forbidden import rules.
- Secret serialization checks.
- Tool/model/connector boundary checks.
- CI wiring for architecture gates.

### Out of Scope
- Functional agent behavior.
- Performance benchmarks.

## Dependencies

- Tasks 01-02.

## Implementation Steps

1. Encode allowed package dependency graph.
2. Add forbidden imports for vendor SDKs and Symphonia in core.
3. Assert tools cannot import model orchestration.
4. Assert connectors cannot import prompts/profiles.
5. Run gates in CI.

## Files Likely Touched

- architecture test suite
- lint/dependency config
- CI pipeline

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- Tests must fail with a deliberately introduced violation.
- Keep rules understandable to future agents.

## Testing Requirements

- Positive graph test.
- Negative fixture or mutation proving each major rule catches violations.

## Acceptance Criteria

- [ ] CI blocks forbidden dependencies.
- [ ] Rules cover all current package roots.
- [ ] Failure messages identify the violated boundary.

## Documentation Updates

- Document dependency graph and how to add a new adapter safely.

## Handoff Notes

Do this early; later tasks should rely on the gate instead of repeating architecture warnings.
