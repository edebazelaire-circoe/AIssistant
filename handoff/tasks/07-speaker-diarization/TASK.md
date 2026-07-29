# Task 07 — Implement Anonymous Speaker Diarization

## Goal

Assign stable anonymous speaker clusters to transcript segments and expose overlap/confidence diagnostics.

## Context

V1 needs `Speaker 1`, `Speaker 2`, etc. Identity enrollment is explicitly deferred.

## Scope
### In Scope
- Diarization port.
- One initial adapter.
- Streaming or chunked reconciliation strategy.
- Speaker cluster creation and segment assignment.
- Overlap/uncertainty indicators.
- Manual relabel/merge/split application commands if feasible.

### Out of Scope
- Known-person voiceprints.
- Calendar/Bluetooth identity inference.

## Dependencies

- Tasks 02, 06.

## Implementation Steps

1. Lock diarization mode and latency tradeoff.
2. Implement adapter normalization.
3. Reconcile diarization windows with transcript timings.
4. Create stable cluster labels within a meeting.
5. Emit assignment and revision events.
6. Add manual correction commands to domain/application layer.

## Files Likely Touched

- diarization port/adapter
- speaker assignment service
- tests/fixtures

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- Identity is optional and separate.
- Corrections are versioned, not destructive.

## Testing Requirements

- Two-speaker fixture.
- Overlapping speech fixture.
- Late cluster revision.
- Manual merge/split/relabel.
- No-identity serialization.

## Acceptance Criteria

- [ ] Transcript visibly separates speakers.
- [ ] Cluster labels stay stable enough across the session.
- [ ] Uncertain overlap is surfaced instead of hidden.
- [ ] Manual corrections replay correctly.

## Documentation Updates

- Document diarization limitations and latency.
- Resolve diarization engine question.

## Handoff Notes

Batching by short windows is acceptable if the UI exposes provisional versus settled assignments.
