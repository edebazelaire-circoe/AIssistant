# 06 — Agent Inspector UX

## Purpose

The Agent Inspector is a developer/operator laboratory. It must answer, at a glance:

- What state is the agent in?
- What audio is being captured?
- What did speech processing produce?
- What does the agent think is happening?
- What context and model configuration are active?
- What plan did it create?
- Which tools ran?
- What changed in the outside world?
- Why did something fail?

## Recommended layout

### Global control bar

- Microphone hard on/off.
- Force standby.
- Force transcription.
- Force interactive mode.
- Start/end meeting.
- Active profile indicator.
- Session timer.
- Provider health summary.
- Emergency stop for current execution.

### Left column — Sensing

#### Audio card

- input device selector;
- signal level;
- mute state;
- buffer duration and occupancy;
- dropped-frame counter;
- local/remote indicator.

#### Wake-word card

- active phrase;
- deactivation phrase;
- detection score;
- last detection timestamp;
- false-wake mark button;
- enrollment recording controls;
- list of accepted recordings.

### Center column — Conversation

#### Live conversation

- assistant/user turns;
- partial versus final transcript distinction;
- current listening/speaking indicator;
- manual text injection for test cases.

#### Speaker transcript

- timeline with `Speaker 1`, `Speaker 2`, etc.;
- confidence and overlap warnings;
- manual relabel/merge/split controls;
- jump from extracted fact to source segment.

### Right column — Understanding and action

#### Understanding card

- current topic;
- decisions;
- action items;
- owners;
- questions and answers;
- confidence;
- unresolved ambiguity;
- manual “run analysis now” action.

#### Context card

- active meeting profile;
- loaded documents/artifacts;
- current project hints;
- context token/size diagnostics where available;
- source list, not hidden prompt text only.

#### Plan and policy card

- selected capability;
- ordered plan steps;
- capability policy;
- approval status;
- reason/confidence;
- cancel/retry controls.

#### Tool timeline

For each call:

- tool name;
- connector;
- start/end time;
- arguments with secrets redacted;
- success/error;
- duration;
- output summary;
- correlation ID.

#### Results/artifact viewer

- file opened or created;
- workbook sheet preview;
- before/after cells;
- highlighted changes;
- save location/version;
- rollback action when supported.

## Settings areas

### Voice

- input device;
- activation phrase;
- deactivation phrase;
- enrollment samples;
- detector threshold;
- buffer duration.

### Models

- provider configurations;
- model assignment by role;
- test configuration;
- access/credit/quota/transport diagnostics;
- local versus remote labels.

### Connectors

- file system;
- Excel;
- future MCP/Symphonia;
- health, permissions, and allowed roots.

### Capabilities

- disabled/manual/automatic selector;
- required connectors;
- workflow step list;
- mutation indicator;
- last execution status.

## UX constraints

- Do not hide partial failures behind a generic red toast.
- Do not represent “automatic” as “unobservable.”
- Keep the live conversation readable even when diagnostics are dense.
- Use progressive disclosure: summary cards first, expandable raw payloads second.
- Preserve one timeline across audio, understanding, planning, calls, and artifacts through correlation IDs.
