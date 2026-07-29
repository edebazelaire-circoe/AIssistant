# Task 18 — Implement Inspector Understanding, Plan, Tool, and Artifact Panels

## Goal

Make the agent's reasoning products, policies, execution, and external changes visible end to end.

## Context

The user wants the plan, every called tool, and especially the produced result such as a displayed updated workbook.

## Scope
### In Scope
- Meeting facts/understanding panel.
- Context/profile source panel.
- Plan and policy card.
- Approval controls.
- Tool-call timeline.
- Connector health status.
- Artifact viewer.
- Workbook preview and changed-cell highlights.
- Failure/retry/rollback controls when supported.

### Out of Scope
- Settings editing.
- New connector implementations.

## Dependencies

- Tasks 10-16.

## Implementation Steps

1. Render structured facts with source links.
2. Render plan steps and policy decision.
3. Implement approval/rejection controls.
4. Render correlated tool lifecycle.
5. Render typed results and diagnostics.
6. Build workbook diff/preview component.
7. Add retry/cancel/rollback actions behind capabilities.

## Files Likely Touched

- understanding panel
- plan/policy components
- tool timeline
- artifact viewer
- UI tests

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- Never display raw secrets.
- Automatic mode remains fully visible.
- Result view must distinguish proposal from persisted artifact.

## Testing Requirements

- Fact source navigation.
- Approval flow UI.
- Tool success/failure timeline.
- Workbook diff rendering.
- Automatic execution visibility.
- Redaction snapshots.

## Acceptance Criteria

- [ ] The complete roadmap capability can be understood from the UI without reading server logs.
- [ ] Changed cells and final file version are visible.
- [ ] Failures identify component, step, and recovery action.

## Documentation Updates

- Add screenshots later only after final UI validation; update operator guide now.

## Handoff Notes

No visuals were selected in the grill session, so final UI styling remains unvalidated.
