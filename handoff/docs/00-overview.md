# 00 — Overview

## Product goal

Build a local-first experimental agent runtime, provisionally called **Jarvis**, that can listen to meetings, separate speakers, transcribe continuously, answer or act live when requested, and execute visible workflows through tools.

The V1 is not a polished assistant. It is a capability-validation laboratory whose central UI is the **Agent Inspector**.

## Core user outcome

A user can:

1. turn the microphone fully off or place the agent in standby;
2. activate it with a configurable wake phrase;
3. start a meeting mode;
4. observe live transcription and speaker separation;
5. ask a live question or trigger a capability;
6. inspect the agent's plan and tool calls;
7. review or automatically accept an action depending on policy;
8. see the actual result, including an Excel roadmap diff and workbook preview;
9. end the meeting and receive structured decisions and actions.

## Mental model

The system has four layers:

- **Sensing** — audio capture, circular buffer, wake-word detection, transcription, diarization.
- **Understanding** — meeting context, event extraction, confidence, and structured memory.
- **Acting** — capabilities, workflows, tool calls, connectors, policy evaluation, and rollback metadata.
- **Inspecting** — live UI exposing every material state transition and output.

## V1 scope

- Local desktop-oriented prototype.
- Agent state machine with microphone off, standby, transcription, and interactive modes.
- Configurable wake-word enrollment.
- Streaming transcript and speaker diarization.
- Meeting profile loaded dynamically.
- Live and end-of-meeting analysis.
- Connector/tool registry.
- Per-capability policy: disabled, manual, automatic.
- Excel roadmap integration and visible updates.
- Model/provider manager with access diagnostics.
- Structured logs, plans, outputs, and file diffs.

## Non-goals

- Production-ready Symphonia integration.
- Smartwatch or phone app.
- Guaranteed speaker identity recognition.
- Fully autonomous general-purpose desktop control.
- Full long-term personal memory graph.
- General skill marketplace.
- Invisible background mutation without audit evidence.
- Legal-policy implementation; consent and company policy are managed outside this prototype.

## Success criteria

The prototype succeeds when a developer can run one end-to-end scenario:

> Start in standby, say the wake phrase, launch meeting mode, observe two speakers in a transcript, say that an action changed status, let Jarvis propose or automatically perform an Excel roadmap update according to policy, and inspect the plan, tool calls, changed cells, saved file, and final meeting summary.
