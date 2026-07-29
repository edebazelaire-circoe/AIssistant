# Task 11 — Implement Capability Registry, Workflow Runner, and Policy Engine

## Goal

Support high-level capabilities with disabled/manual/automatic execution policies and inspectable plans.

## Context

Manual is the default, but the architecture must support full automation without changing workflow code.

## Scope
### In Scope
- Capability definitions and registry.
- Workflow definitions/steps.
- Plan creation and validation.
- Policy store and evaluation.
- Approval request/token flow.
- Automatic execution path.
- Plan/policy/execution events.
- Fake capability scenario.

### Out of Scope
- Natural-language capability selection.
- Excel roadmap implementation.

## Dependencies

- Tasks 02, 08, 10.

## Implementation Steps

1. Implement registry and workflow schema.
2. Create deterministic plan validator.
3. Implement three policy modes.
4. Implement approval lifecycle.
5. Execute fake workflow through tool runner.
6. Expose plan and policy read models.

## Files Likely Touched

- capability/workflow modules
- policy engine
- approval service
- tests

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- No mutating tool runs before policy release.
- Automatic mode still emits plan and audit events.
- Approval tokens are scoped and single-use.

## Testing Requirements

- Disabled path.
- Manual approval granted/rejected/expired.
- Automatic path.
- Mixed read/write workflow.
- Invalid/unregistered tool in plan.
- Cancellation and retry.

## Acceptance Criteria

- [ ] All three policies behave as specified.
- [ ] A fake capability is fully inspectable from plan to result.
- [ ] Policy changes are persisted and auditable.

## Documentation Updates

- Document policy semantics and approval API.

## Handoff Notes

Do not add model reasoning yet; prove the deterministic execution boundary first.
