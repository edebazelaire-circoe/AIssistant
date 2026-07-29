# Task 17 — Implement Inspector Audio, Wake, and Transcript Panels

## Goal

Expose sensing behavior and speaker-separated conversation in a way that allows rapid debugging.

## Context

The user explicitly wants buttons for modes, microphone control, wake enrollment, and visible transcript/diarization state.

## Scope
### In Scope
- Mic hard on/off and mode controls.
- Audio level/buffer/dropped-frame view.
- Wake phrase detection card.
- Enrollment recording/list/delete UI.
- Live partial/final transcript.
- Speaker labels, confidence, overlaps, and corrections.
- Manual text/audio fixture injection for tests if supported.

### Out of Scope
- Model/provider settings.
- Tool/result panels.

## Dependencies

- Tasks 05-07, 16.

## Implementation Steps

1. Bind mode and mic commands.
2. Render audio read model.
3. Implement wake enrollment workflow UI.
4. Render transcript revisions without duplication.
5. Render speaker timeline and warnings.
6. Add manual relabel/merge/split controls if backend supports them.

## Files Likely Touched

- audio panel
- wake settings card
- transcript panel
- speaker components
- UI tests

## Architecture Constraints

- Load `/caveman` and `/coding-guideline`.
- Clearly distinguish mic off from standby.
- Clearly distinguish partial from final text.
- Do not imply speaker identity when only clusters are known.

## Testing Requirements

- Mode control flows.
- Enrollment UI.
- Partial/final rendering.
- Speaker revision rendering.
- Overlap warning.
- Screen-reader labels.

## Acceptance Criteria

- [ ] Operator can control all four modes.
- [ ] Wake samples and detections are visible.
- [ ] Two-speaker transcript is understandable and corrects revisions cleanly.

## Documentation Updates

- Update Inspector operator guide.

## Handoff Notes

This panel is the main diagnostic surface for latency and false-wake problems.
