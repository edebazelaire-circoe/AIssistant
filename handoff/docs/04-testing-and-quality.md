# 04 — Testing and Quality

## Mandatory quality gates

Every coding task must load `/caveman` and `/coding-guideline` and leave evidence in its final report.

No task is complete with only “it runs locally.” Each task needs automated tests at the lowest useful boundary plus diagnostics visible in the Agent Inspector or logs.

## Test layers

### 1. Domain unit tests

- State-machine transitions.
- Policy evaluation.
- Capability plan validation.
- Transcript segment merging.
- Speaker label assignment.
- Roadmap row/status mapping.
- Model-role compatibility.

### 2. Contract tests

- Speech adapter contract.
- Diarization adapter contract.
- Provider/model inventory contract.
- Tool and connector typed-result contracts.
- Excel workbook adapter contract.
- Event transport/replay contract.

Use fakes and golden payloads. Vendor SDK objects must not escape adapter modules.

### 3. Integration tests

- Microphone input to finalized transcript where practical.
- Recorded audio fixture to diarized segments.
- Model access diagnostic against a mocked provider server.
- Excel fixture update with style preservation.
- Approval flow from plan to execution.
- UI event stream reconnect and replay.

### 4. Scenario tests

Reference scenario:

1. Start with microphone off.
2. Enable standby.
3. Trigger wake detection.
4. Start meeting profile.
5. Feed two-speaker fixture audio.
6. Detect an action/status statement.
7. Generate `update_roadmap` plan.
8. In manual mode, request and grant approval.
9. Update the workbook.
10. Display changed cells and saved artifact.
11. Produce final meeting decisions/actions.

Repeat with automatic mode and verify no approval request is created.

## Architecture tests

Enforce:

- core/domain cannot import UI, vendor SDKs, Excel libraries, or Symphonia code;
- orchestration depends on interfaces, not concrete providers;
- tools do not call language models;
- connectors do not know meeting prompts;
- UI receives events/read models rather than reading internal mutable objects;
- secrets are not serializable in event payloads.

## Regression fixtures

Maintain versioned fixtures for:

- clean two-speaker audio;
- overlapping speech;
- wake phrase variants;
- false wake examples;
- partial/final transcript corrections;
- roadmap workbook before/after;
- missing row, duplicate row, locked file, malformed workbook;
- provider authentication, quota, access, transport, and unsupported-model failures.

## Diagnostics requirements

Every failure result includes:

- stable error code;
- human-readable message;
- source component;
- retryability;
- correlation ID;
- redacted provider details;
- suggested next diagnostic action.

## Performance budgets

Initial budgets are provisional and must be measured, not assumed:

- UI state update visible within 250 ms of a local event.
- Wake event processing target under 500 ms after phrase completion.
- Partial transcript visible within 2 seconds under normal local conditions.
- Tool-call timeline event emitted before external execution begins.
- Workbook preview refreshed within 2 seconds after save for test-size files.

## Definition of done

A task is complete only when:

- acceptance criteria pass;
- tests are added and green;
- architecture constraints remain enforced;
- diagnostics are inspectable;
- docs are updated;
- no secret or raw biometric enrollment audio is accidentally committed;
- the task report records commands, results, and residual risks.
