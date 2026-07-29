# Reconstructed Grill Session

> This is a reconstructed grill session based on the available voice-conversation context. It preserves the user's corrections, terminology, constraints, and accepted directions. It is not a verbatim transcript.

## 1. Initial idea

The user wants an always-available personal agent, provisionally called **Jarvis**, that can be activated by voice without opening a laptop. The first idea involved a connected watch, but the discussion converged on treating hardware as an interface and keeping the heavier processing on a phone or computer.

The assistant proposed three operating states:

1. **Standby / veille** — minimal local processing and a short circular audio buffer.
2. **Passive listening / wake detection** — local wake-word or intent detection, still without cloud processing.
3. **Active** — capture, transcription, reasoning, tool calls, and responses.

The circular buffer exists so the system does not lose the first words immediately before or after “Hey Jarvis”.

## 2. Relation to Symphonia

The user clarified that the first prototype must be **isolated from Symphonia**. Symphonia may later become one client or connector among others. The prototype should prove the interaction model and technical capabilities inside the company before any product integration.

The long-term Symphonia vision still includes a personal agent able to navigate, display information, and call MCP tools. However, the current project must not become a full skill platform or duplicate Symphonia's future architecture.

## 3. First valuable use case: meetings

The first concrete capability is a meeting assistant:

- record and transcribe a conversation;
- separate speakers as `Speaker 1`, `Speaker 2`, etc.;
- later associate speakers with identities, possibly via consensual voice enrollment;
- extract decisions, actions, owners, and questions;
- run end-of-meeting analysis;
- allow live, manually triggered analysis or actions during the meeting;
- eventually operate reactively or autonomously.

The user emphasized that speaker separation matters because a single undifferentiated transcript damages later reasoning. Question/answer structure and attribution improve decision and action extraction.

## 4. Live interaction versus silent transcription

The desired runtime supports distinct modes:

- **Transcription mode**: listen, structure, and remain silent.
- **Interactive mode**: answer questions, display information, and call tools live.
- **Standby mode**: wait for the wake word.
- **Microphone off**: fully stop audio capture.

The agent should be able to answer questions such as the price of a feature, retrieve information, or trigger an analysis while the meeting continues. End-of-meeting extraction remains important, but individual capabilities must also be invokable during the conversation.

## 5. Autonomous actions and safeguards

The target is full automation, not permanent micromanagement through voice commands. The user wants the agent to understand when an update is required and execute it.

For V1, every capability is configurable with three policies:

- **Disabled**
- **Manual verification**
- **Automatic**

Manual verification is the default. The user can progressively switch selected actions to automatic mode from settings. The interface must preserve visibility into plans, calls, outputs, diffs, and failures.

## 6. Excel roadmap example

The primary action scenario is updating an Excel roadmap:

- one row per action for the month;
- status represented visually;
- yellow = in progress;
- red = not done;
- green = done;
- agent reads the relevant folder/file;
- identifies the target row;
- edits values and colors;
- displays the workbook or an accurate preview;
- highlights the changed cells;
- shows the produced result rather than editing silently.

The user wants the high-level capability **Update roadmap** represented as a workflow composed of lower-level calls such as locate file, open workbook, read rows, map action, write value, change style, save, and display result.

## 7. Agent Inspector test interface

The user does not need a polished final product first. The V1 should be a technical laboratory, described during the session as an **Agent Inspector**.

The page should expose:

- microphone on/off;
- force state buttons for standby, transcription, and interactive modes;
- live audio level;
- wake-word detection and circular-buffer state;
- wake-word enrollment with multiple recordings;
- configurable activation and deactivation phrases;
- live conversation and raw transcript;
- speaker-separated transcript;
- extracted topics, decisions, actions, owners, confidence, and doubts;
- loaded context and memory;
- agent execution plan;
- tool calls in progress and historical calls;
- connector status;
- final tool outputs;
- file previews and visible diffs;
- capability policy controls;
- model/provider configuration and diagnostics.

The user explicitly asked to see not just that a tool was called, but what it produced.

## 8. Meeting mode loading

The user challenged whether “meeting mode” should be a separate page, a prompt, or a dynamically loaded skill. The accepted V1 direction is lightweight:

- a generic test conversation / Agent Inspector;
- a meeting profile loaded at runtime as a prompt-and-capability bundle;
- activation through UI or voice command;
- no need to build a generalized enterprise skill marketplace in this prototype.

## 9. Voice enrollment and diarization

The discussion distinguished:

- **Diarization**: separate speakers without naming them;
- **Speaker identification**: map a diarized speaker to a known person.

V1 includes diarization with anonymous speaker labels. Manual association can follow. Consensual voice embeddings, calendar context, Bluetooth proximity, and identity matching are later enhancements.

## 10. Model and provider configuration

The user previously tried a realtime model through environment variables and received access/configuration/credit errors despite text API calls working.

The accepted direction is:

- environment variables contain secrets only;
- model IDs are not hardcoded as the only configuration mechanism;
- a Model Manager lists or accepts available models by provider;
- separate roles can use separate models: realtime conversation, transcription, classification, analysis, embeddings, local routing;
- a “Test configuration” action reports authentication, project, billing/quota, model access, transport/session, and capability errors separately;
- the UI must make it hard to accidentally select an obsolete or incompatible communication model.

No exact model name was locked during the session.

## 11. Deferred items

The following were explicitly or implicitly deferred:

- connected-watch application;
- production integration with Symphonia;
- full personal-memory graph;
- autonomous meeting detection from calendar or nearby voices;
- voiceprint identity enrollment;
- generalized skill marketplace;
- complex local micro-agent optimization;
- polished end-user product UX.

## 12. Final handoff request

The user asked to convert the entire grilling session into a task-oriented implementation handoff.
