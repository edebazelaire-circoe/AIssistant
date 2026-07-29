# Task 19 — Implement Voice, Model, Connector, and Capability Settings

## Goal

Provide the configuration controls needed to test variants without editing source or environment model strings.

## Context

The user wants configurable voice commands, listed tools/connectors/actions, model selection, and disabled/manual/automatic policies.

## Scope
### In Scope
- Voice phrase/sample settings.
- Provider and model role assignments.
- Test configuration UI.
- Connector list, health, and allowed-root configuration.
- Capability list with workflow/tool expansion.
- Policy selector.
- Configuration validation and persistence.

### Out of Scope
- General marketplace.
- Production multi-user administration.

## Dependencies

- Tasks 05, 09-11, 16.

## Implementation Steps

1. Build settings read/write APIs if not already present.
2. Implement grouped settings pages/cards.
3. Add provider diagnostic result view.
4. Add connector permissions/health view.
5. Add capability hierarchy: capability -> workflow -> tools.
6. Implement policy selector and safeguards.
7. Add import/export of non-secret config if useful.

## Files Likely Touched

- settings backend/application services
- settings UI
- validation schemas
- tests

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- Manual is the initial default for mutating capabilities.
- Secrets are references only.
- Changing a model or policy emits audit/config events.

## Testing Requirements

- Persistence/reload.
- Invalid model-role assignment.
- Provider diagnostic stages.
- Capability policy change.
- Connector root validation.
- Secret non-exposure.

## Acceptance Criteria

- [ ] Operator can configure the full V1 without editing model strings in `.env`.
- [ ] Capabilities clearly show disabled/manual/automatic.
- [ ] Tools and connectors are discoverable under each capability.

## Documentation Updates

- Update configuration guide and examples with fake values only.

## Handoff Notes

Do not expose raw provider errors without redaction; retain a copy-safe diagnostic summary.
