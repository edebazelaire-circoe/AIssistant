# Task 12 — Implement Safe Excel Roadmap Connector and Tools

## Goal

Read, identify, modify, style, verify, and preview roadmap workbooks safely.

## Context

The reference workbook uses one action per row with red/yellow/green status coloring. The user must see the real result.

## Scope
### In Scope
- Allowed-root file discovery.
- Workbook open/read tools.
- Roadmap schema detection/mapping.
- Row matching API.
- Status value and fill update.
- Safe copy/atomic save.
- Reopen verification.
- Cell-level diff and preview artifact.
- Fixture workbooks.

### Out of Scope
- Natural-language interpretation.
- Agent planning.
- Desktop Excel automation unless chosen by ADR.

## Dependencies

- Tasks 02, 10.

## Implementation Steps

1. Define roadmap schema configuration.
2. Build fixture workbooks including edge cases.
3. Implement read-only discovery and mapping.
4. Implement proposed change set.
5. Implement safe write and color mapping.
6. Reopen and verify.
7. Generate artifact diff and preview payload.

## Files Likely Touched

- Excel connector
- roadmap mapper
- tool definitions
- fixtures
- tests

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- Operate only in allowed roots.
- Preserve unrelated formulas/styles.
- Never overwrite on ambiguous schema or row match.
- Colors: red not done, yellow in progress, green done.

## Testing Requirements

- Read/map fixture.
- Each status/color update.
- Unrelated-cell preservation.
- Duplicate/missing row.
- Locked/changed file.
- Idempotent repeated update.
- Path traversal.

## Acceptance Criteria

- [ ] A typed roadmap item can be located and updated.
- [ ] Saved workbook reopens with expected value/style.
- [ ] Before/after diff identifies exact cells.
- [ ] Failure leaves original workbook intact.

## Documentation Updates

- Document workbook schema configuration and safety behavior.

## Handoff Notes

Prefer status values as the source of truth and colors as mapped presentation when the workbook supports both.
