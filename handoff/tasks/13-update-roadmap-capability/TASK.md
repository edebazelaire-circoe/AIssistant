# Task 13 — Implement the Update Roadmap Capability

## Goal

Compose meeting-derived updates, policy evaluation, Excel tools, and visible artifacts into one end-to-end business capability.

## Context

This is the first real mutating capability and the main proof of the architecture.

## Scope
### In Scope
- `update_roadmap` input/output schemas.
- Workflow steps from discovery through preview.
- Deterministic candidate/ambiguity handling.
- Manual approval preview.
- Automatic mode.
- Result artifact/diff publication.
- Rollback reference when supported.

### Out of Scope
- General natural-language agent orchestration.
- Multiple workbook formats beyond configured roadmap schema.

## Dependencies

- Tasks 11-12.

## Implementation Steps

1. Register capability and workflow.
2. Map structured action/status input to roadmap lookup.
3. Create proposed change set.
4. Integrate policy decision and approval.
5. Execute safe write.
6. Publish verified artifact/diff.
7. Handle needs-resolution outcomes.

## Files Likely Touched

- capability definition
- workflow implementation
- integration tests
- scenario fixtures

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- Do not guess among equal row matches.
- Automatic mode obeys all file and schema guards.
- Output must include visible result references.

## Testing Requirements

- Manual approve/reject.
- Automatic success.
- Disabled.
- Ambiguous row.
- Missing workbook.
- Write failure/rollback.
- Repeated idempotent request.

## Acceptance Criteria

- [ ] Capability updates a fixture workbook under manual and automatic policies.
- [ ] Inspector data includes plan, calls, diff, preview, and diagnostics.
- [ ] Ambiguity yields structured resolution rather than mutation.

## Documentation Updates

- Add capability example and policy behavior.

## Handoff Notes

This task should not depend on a language model; feed it structured meeting facts first.
