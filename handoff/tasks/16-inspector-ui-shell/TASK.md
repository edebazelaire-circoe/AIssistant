# Task 16 — Build the Agent Inspector UI Shell and Event Transport

## Goal

Create the local laboratory UI, session connection, timeline transport, and navigable panel structure.

## Context

The Inspector is the primary V1 product surface and must remain useful as later panels are added.

## Scope
### In Scope
- Application shell.
- Global control bar placeholders wired to application commands.
- Responsive multi-panel layout.
- Realtime event transport and reconnect/replay.
- Session selector.
- Raw event inspector behind progressive disclosure.
- Error boundary.

### Out of Scope
- Full panel-specific visualization.
- Polished consumer branding.

## Dependencies

- Tasks 01, 04, 08.

## Implementation Steps

1. Implement UI architecture from ADR.
2. Connect to command/event APIs.
3. Render current state and session metadata.
4. Implement timeline cursor/reconnect.
5. Create panel routes/tabs/cards.
6. Add raw event detail drawer.
7. Add UI test harness.

## Files Likely Touched

- UI shell
- event client
- state store/read models
- component tests

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- UI never imports runtime internals.
- Reconnection replays missed events.
- Diagnostics remain readable, not only console logs.

## Testing Requirements

- Render smoke test.
- Event replay/reconnect.
- Out-of-order/duplicate event handling.
- Command error display.
- Accessibility basics for controls.

## Acceptance Criteria

- [ ] UI connects to a session and displays state/timeline.
- [ ] Refresh does not lose session history.
- [ ] Panel architecture supports the full UX spec without a rewrite.

## Documentation Updates

- Document local UI start and event transport.

## Handoff Notes

Use progressive disclosure; do not dump every JSON payload into the main view.
