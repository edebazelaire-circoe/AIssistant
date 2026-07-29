# Task 15 — Implement the Meeting Agent Profile and Extraction Pipeline

## Goal

Load a meeting-specific prompt/capability bundle, extract structured facts live/on-demand, and finalize the meeting summary.

## Context

Meeting mode should be loadable at runtime without creating a generalized skill marketplace.

## Scope
### In Scope
- Narrow `AgentProfile` contract.
- Meeting profile manifest/config.
- Allowed capabilities and defaults.
- Live/on-demand extraction of decisions, actions, owners, questions, and answers.
- Final summary pipeline.
- UI and voice commands to load/unload profile at application-service level.

### Out of Scope
- Marketplace/distribution system.
- Automatic calendar meeting detection.
- Speaker identity enrollment.

## Dependencies

- Tasks 08-09, 14.

## Implementation Steps

1. Define profile contract and loader.
2. Create meeting extraction schemas.
3. Implement incremental extraction from finalized segments.
4. Add explicit “analyze now” command.
5. Implement final meeting close analysis.
6. Persist facts and source segment references.
7. Expose profile metadata to Inspector.

## Files Likely Touched

- profile contract/loader
- meeting profile
- prompt/config assets
- extraction service
- tests

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- Facts cite source segment IDs.
- Prompt content is versioned and inspectable.
- Profile cannot bypass capability policy.

## Testing Requirements

- Profile hot load/unload.
- Incremental extraction.
- Question/answer attribution.
- Action owner uncertainty.
- Final summary.
- Prompt/schema version migration.

## Acceptance Criteria

- [ ] Meeting profile changes runtime behavior without restart.
- [ ] Facts are structured and traceable to transcript.
- [ ] “Analyze now” works during the meeting.
- [ ] End-of-meeting summary is persisted.

## Documentation Updates

- Document profile format and meeting extraction schema.

## Handoff Notes

Keep the profile format deliberately small. Symphonia may own a richer skill system later.
