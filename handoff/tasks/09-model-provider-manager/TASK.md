# Task 09 — Implement Provider and Role-Based Model Manager

## Goal

Move model selection out of environment strings and provide precise provider/model access diagnostics.

## Context

The user's earlier realtime experiment failed ambiguously. The V1 must test authentication, project, quota, model access, role compatibility, and session transport separately.

## Scope
### In Scope
- Provider config store without raw secrets.
- Provider adapter contract.
- Model inventory/manual ID support.
- Role assignments.
- Configuration diagnostic workflow.
- One initial provider adapter plus a fake.
- Redacted diagnostics.

### Out of Scope
- Agent reasoning prompts.
- Building every provider integration.

## Dependencies

- Tasks 02-03, 08.

## Implementation Steps

1. Implement provider/model contracts from doc 07.
2. Add secret resolver abstraction.
3. Implement fake provider diagnostic matrix.
4. Implement initial provider inventory and probe adapter.
5. Add role compatibility validation.
6. Persist assignments and emit diagnostic events.

## Files Likely Touched

- provider/model domain modules
- secret resolver
- provider adapters
- diagnostic service
- tests

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- No raw key persistence/logging.
- Do not hardcode an unverified realtime model ID as the architecture.
- Current provider docs/access must be verified during adapter implementation.

## Testing Requirements

- All error taxonomy branches with fake provider.
- Secret redaction snapshot.
- Unsupported role/model validation.
- Stale model ID handling.
- Realtime handshake probe contract.

## Acceptance Criteria

- [ ] Operator can configure a provider and assign models by role.
- [ ] Test configuration reports separate stage results.
- [ ] The system can distinguish access, quota, model, and transport failures.

## Documentation Updates

- Update provider setup and record verified model capabilities/date.

## Handoff Notes

Any claim that a model supports realtime/audio must be grounded in the adapter's verified capability probe or current official documentation.
