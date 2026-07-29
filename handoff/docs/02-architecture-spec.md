# 02 — Architecture Specification

## Architectural principles

1. **Local-first sensing:** microphone capture, wake detection, and circular buffer are local.
2. **Replaceable adapters:** audio, speech, models, Excel, MCP, storage, and UI transports sit behind typed ports.
3. **Capabilities above tools:** the agent requests business capabilities; workflows call tools; tools use connectors.
4. **Observable by construction:** all important operations emit typed timeline events.
5. **Safe mutation:** policy evaluation, approval, diff production, and audit records surround write operations.
6. **No Symphonia coupling:** integration belongs in an adapter added later.

## Logical component map

```text
Microphone
  -> Audio Capture Service
  -> Circular Buffer
  -> Wake Detector
  -> Agent State Machine
       -> Streaming Speech Adapter
       -> Diarization Adapter
       -> Meeting Session Store
       -> Agent Orchestrator
            -> Profile Loader
            -> Context Builder
            -> Model Role Router
            -> Capability Registry
                 -> Policy Engine
                 -> Workflow Runner
                      -> Tool Registry
                           -> File Connector
                           -> Excel Connector
                           -> Future MCP Connector

All components -> Event Bus / Timeline Store -> Agent Inspector UI
```

## Process boundaries

The stack is unresolved, but the following boundaries are mandatory regardless of language:

- **UI process:** renders controls, transcript, plans, calls, settings, and artifact previews.
- **Agent runtime:** owns state machine, orchestration, policy, workflow execution, and session lifecycle.
- **Audio/ML adapters:** can run in-process or as a local sidecar, but expose stable typed interfaces.
- **Connector layer:** isolated from model prompts and business reasoning.
- **Persistence:** stores session/events/config metadata; secrets remain external.

A provisional implementation may use a desktop/web UI plus a local service. If Python-only ML libraries are chosen while the main runtime is TypeScript, use a narrow local RPC boundary rather than mixing domain logic across both runtimes.

## Agent state machine

### States

- `MIC_OFF`
- `STANDBY`
- `TRANSCRIBING`
- `INTERACTIVE`
- `ERROR_RECOVERABLE`

### Required transitions

- `MIC_OFF -> STANDBY` through explicit UI control.
- `STANDBY -> TRANSCRIBING` through wake command, meeting start, or explicit button.
- `TRANSCRIBING -> INTERACTIVE` through wake command or explicit button.
- `INTERACTIVE -> TRANSCRIBING` through completion, deactivation phrase, or timeout.
- Any active state -> `MIC_OFF` through explicit hard stop.
- Recoverable failures -> previous safe state with diagnostics.

### Mode behavior

| State | Audio capture | Circular buffer | Remote speech/model | Tool calls | Agent speech |
|---|---:|---:|---:|---:|---:|
| MIC_OFF | No | No | No | No | No |
| STANDBY | Yes, local | Yes | No | No | No |
| TRANSCRIBING | Yes | Optional pre-roll | Speech/diarization allowed | Read-only or explicit command only | Silent by default |
| INTERACTIVE | Yes | Optional | Yes | Policy-controlled | Allowed |

## Runtime event model

Every subsystem emits immutable events with:

- `event_id`
- `session_id`
- `timestamp`
- `event_type`
- `source_component`
- `correlation_id`
- `payload`
- `severity`
- `duration_ms` when relevant
- `diagnostics`

Examples:

- `agent.state.changed`
- `audio.level.sampled`
- `wake.detected`
- `transcript.segment.finalized`
- `speaker.cluster.assigned`
- `understanding.action.detected`
- `plan.created`
- `policy.approval.requested`
- `tool.call.started`
- `tool.call.completed`
- `artifact.diff.created`
- `meeting.summary.completed`

## Meeting pipeline

1. Create `MeetingSession`.
2. Load meeting profile.
3. Capture audio frames.
4. Detect wake commands and state transitions.
5. Produce partial/final transcript segments.
6. Apply diarization labels.
7. Build structured conversational events.
8. Run live extraction at controlled intervals or on explicit request.
9. Route user requests to the orchestrator.
10. Plan capabilities and tool calls.
11. Evaluate capability policy.
12. Execute or request approval.
13. Render outputs and diffs.
14. On meeting end, run final extraction and persist a summary package.

## Capability execution

```text
Intent/request
  -> Capability selection
  -> Typed input resolution
  -> Execution plan
  -> Policy evaluation
  -> Optional approval
  -> Workflow steps
  -> Tool calls
  -> Typed results
  -> Artifact diff/preview
  -> Audit event
```

The model may propose a plan, but deterministic runtime code validates tool names, argument schemas, permissions, file scope, and policy before execution.

## Failure handling

- Speech failures must not corrupt meeting state.
- Tool failures return typed errors and preserve prior artifacts.
- Workbook writes use copy/temporary-file/atomic-replace semantics when possible.
- Automatic mode does not suppress diagnostics.
- A failed workflow exposes the last successful step and recovery action.
- UI reconnection must replay the session timeline from storage.
