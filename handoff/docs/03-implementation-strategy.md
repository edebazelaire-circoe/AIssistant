# 03 — Implementation Strategy

## Delivery philosophy

The fastest useful route is not “build an autonomous assistant.” It is “prove every boundary through one observable meeting-to-roadmap scenario.”

## Stage 0 — Lock foundations

- Record the stack ADR.
- Create module boundaries and architecture tests.
- Define typed domain contracts and event envelopes.
- Implement fakes before external adapters.

Exit condition: a fake meeting can drive the state machine and emit events visible to a minimal UI.

## Stage 1 — Sensing spine

- Audio capture.
- Circular buffer.
- Wake-word enrollment and detector adapter.
- Streaming transcription.
- Anonymous speaker diarization.

Exit condition: the inspector shows state, audio, wake detections, transcript segments, and speaker labels from a real microphone.

## Stage 2 — Meeting memory and model configuration

- Meeting session/timeline store.
- Provider and role-based model manager.
- Configuration tests with precise failure categories.
- Meeting profile loading.

Exit condition: a meeting survives UI refresh/reconnect, and the operator can validate model access without editing source code.

## Stage 3 — Action architecture

- Tool and connector registries.
- Capability contracts.
- Policy engine with disabled/manual/automatic.
- Fake workflow execution and approval flow.

Exit condition: a simulated capability shows plan, approval, calls, results, and audit events.

## Stage 4 — Excel roadmap vertical slice

- Workbook discovery and read adapter.
- Roadmap schema/mapping.
- Safe write and style update.
- Before/after diff and preview.
- `update_roadmap` workflow.

Exit condition: a spoken meeting statement updates a fixture workbook and visibly highlights the change.

## Stage 5 — Complete Agent Inspector

- Audio/state controls.
- Transcript/diarization panel.
- Understanding and meeting facts panel.
- Plan/tool/result timeline.
- Capability/connectors/model/wake settings.
- Artifact preview.

Exit condition: a developer can identify whether a failure originated in audio, speech, reasoning, policy, tool selection, connector execution, or rendering.

## Stage 6 — End-to-end hardening

- Scenario tests.
- Fault injection.
- Secret redaction.
- Performance budgets.
- Packaging and reproducible local setup.

Exit condition: the reference scenario passes repeatedly and produces a final implementation report with evidence.

## Rollout sequence for autonomy

1. All mutating capabilities default to manual.
2. Observe plans and compare proposed versus accepted changes.
3. Enable automatic mode for the roadmap capability on test workbooks.
4. Add confidence/rule gates if real usage exposes ambiguity.
5. Expand to additional capabilities only after traceability remains strong.

The architecture must support full auto from the beginning; the rollout does not require full auto from the first run.
