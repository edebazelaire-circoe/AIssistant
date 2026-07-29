# Task 06 — Implement Streaming Transcription Adapter

## Goal

Convert active audio frames into partial and final transcript segments through a replaceable speech adapter.

## Context

Transcription must be live enough for the Inspector while preserving revisions and provider diagnostics.

## Scope
### In Scope
- Speech adapter port.
- One initial local or remote streaming adapter.
- Partial/final segment handling.
- Pre-roll injection after wake.
- Language/config parameters.
- Typed provider errors.

### Out of Scope
- Diarization.
- Meeting analysis.
- Provider model manager UI.

## Dependencies

- Tasks 02, 04.

## Implementation Steps

1. Choose initial speech adapter based on Task 01 ADR.
2. Map audio frames to provider/local stream.
3. Normalize partial and final results.
4. Preserve segment revisions.
5. Emit transcript and latency events.
6. Implement cancellation/reconnect behavior.

## Files Likely Touched

- speech port
- speech adapter
- transcription service
- tests/fixtures

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- Vendor objects stay inside adapter.
- No transcription in `MIC_OFF` or `STANDBY`.
- Provider errors map to stable error taxonomy.

## Testing Requirements

- Recorded audio contract test.
- Partial-to-final revision test.
- Cancellation/reconnect test.
- Unsupported format and provider failure tests.
- Latency metric emission.

## Acceptance Criteria

- [ ] Fixture and live audio can produce normalized segments.
- [ ] Pre-roll words are not lost after wake.
- [ ] Partial/final revisions are inspectable.
- [ ] Failures do not corrupt session state.

## Documentation Updates

- Document speech adapter configuration and fallback behavior.

## Handoff Notes

Do not embed meeting prompts or tool logic in this adapter.
