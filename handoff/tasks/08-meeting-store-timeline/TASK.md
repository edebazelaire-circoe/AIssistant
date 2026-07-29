# Task 08 — Implement Meeting Session Store and Replayable Timeline

## Goal

Persist meetings, transcripts, facts, plans, calls, and artifacts as a replayable event-driven session.

## Context

The Inspector must reconnect and explain what happened without accessing hidden mutable runtime state.

## Scope
### In Scope
- Persistence adapter selected by ADR.
- Meeting lifecycle service.
- Append-only event/timeline storage.
- Read models for transcript, facts, calls, and artifacts.
- Replay/cursor API.
- Retention hooks.

### Out of Scope
- Long-term personal memory graph.
- Cross-meeting semantic search.

## Dependencies

- Tasks 02-03.

## Implementation Steps

1. Define storage ports.
2. Implement in-memory fake first.
3. Implement chosen local persistent adapter.
4. Build event replay and read-model projection.
5. Add session start/end commands.
6. Add retention/deletion operations.

## Files Likely Touched

- storage ports
- meeting service
- event repository
- projection/read models
- tests

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- Events are append-only/versioned.
- Secrets and raw provider objects are excluded.
- UI reads projections/events, not database internals.

## Testing Requirements

- Append/replay ordering.
- Crash/restart recovery.
- Projection rebuild.
- Concurrent cursor reads.
- Retention and deletion.

## Acceptance Criteria

- [ ] A session can be closed, reopened, and replayed.
- [ ] Inspector data can be rebuilt from persisted events.
- [ ] Corrupted event or migration failure returns diagnostics.

## Documentation Updates

- Document storage schema/migrations and retention controls.

## Handoff Notes

Keep the persistence interface simple enough to replace if the V1 storage choice proves wrong.
