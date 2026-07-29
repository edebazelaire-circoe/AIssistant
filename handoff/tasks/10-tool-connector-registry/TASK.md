# Task 10 — Implement Tool and Connector Registries

## Goal

Create typed, discoverable registries for deterministic operations and external-system adapters.

## Context

The Agent Inspector must list connectors, low-level tools, arguments, results, health, and permissions.

## Scope
### In Scope
- Connector contract and health status.
- Tool definition/version/schema contract.
- Registry and lookup.
- Permission/allowed-root metadata.
- Tool invocation runner with timeout, cancellation, result normalization, and events.
- Fake connector/tools.

### Out of Scope
- Excel-specific implementation.
- LLM capability planning.

## Dependencies

- Tasks 02-03, 08.

## Implementation Steps

1. Define connector and tool interfaces.
2. Implement registries and duplicate/version checks.
3. Implement invocation runner.
4. Emit started/completed/failed events.
5. Add connector health probes.
6. Expose read models for Inspector.

## Files Likely Touched

- connector/tool contracts
- registries
- runner
- fake adapters
- tests

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- Tools return typed results.
- Connectors do not know prompts or models.
- Arguments are validated and redacted before event emission.

## Testing Requirements

- Registration/version conflicts.
- Schema validation.
- Timeout/cancel.
- Health status.
- Secret redaction.
- Fake artifact result.

## Acceptance Criteria

- [ ] Inspector-facing API can list tools/connectors and status.
- [ ] Every invocation emits correlated lifecycle events.
- [ ] Opaque exceptions cannot escape the runner.

## Documentation Updates

- Document how to add a connector and tool.

## Handoff Notes

Keep low-level tools small; business-level behavior belongs in capabilities/workflows.
