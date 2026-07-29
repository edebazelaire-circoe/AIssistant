# Implementation TODO

## Project context

Build a local-first meeting agent prototype named **Jarvis**. The V1 is centered on an **Agent Inspector** that exposes operating state, audio, wake detection, transcription, diarization, understanding, plans, policies, tool calls, connector health, and visible artifact results. The first mutating vertical slice is an Excel roadmap update.

## Mandatory operating rules

- Run Task 00 first and keep it active as the project orchestrator.
- Complete one focused task at a time.
- Do not start a task before its dependencies are complete.
- For every coding task, load `/caveman` and `/coding-guideline` from `~/ai/skills/`.
- Preserve the domain/adapter/UI boundaries and architecture tests.
- Manual is the default policy for mutating capabilities; disabled and automatic must also work.
- Never hide automatic execution, tool results, or artifact diffs.
- Never hardcode an unverified realtime model ID as a product assumption.
- Keep Symphonia integration out of the V1 core.
- Use `templates/final-implementation-report-template.md` after every task.

## How to select the next task

1. Find the first unchecked task whose dependencies are checked.
2. Re-read that task and the referenced docs.
3. Let Task 00 verify repository reality and adjust the task file if necessary.
4. Implement only that slice.
5. Run all task tests plus architecture gates.
6. Produce the final report.
7. Mark the task complete only after review.

## Ordered tasks

- [ ] Task 00 — Orchestrate the Implementation Program
  - Path: `tasks/00-orchestrate-handoff/TASK.md`
  - Depends on: None. This task always runs first and remains active throughout the program.
  - Status: not started
- [ ] Task 01 — Lock the Stack ADR and Create the Repository Skeleton
  - Path: `tasks/01-lock-stack-and-skeleton/TASK.md`
  - Depends on: Task 00.
  - Status: not started
- [ ] Task 02 — Define Domain Models, Events, and Typed Results
  - Path: `tasks/02-domain-contracts/TASK.md`
  - Depends on: Task 01.
  - Status: not started
- [ ] Task 03 — Add Architecture and Dependency Regression Gates
  - Path: `tasks/03-architecture-gates/TASK.md`
  - Depends on: Tasks 01-02.
  - Status: not started
- [ ] Task 04 — Implement Audio Capture, Circular Buffer, and Agent State Machine
  - Path: `tasks/04-audio-buffer-state/TASK.md`
  - Depends on: Tasks 02-03.
  - Status: not started
- [ ] Task 05 — Implement Wake-Word Enrollment and Detection Adapter
  - Path: `tasks/05-wake-word-enrollment/TASK.md`
  - Depends on: Task 04.
  - Status: not started
- [ ] Task 06 — Implement Streaming Transcription Adapter
  - Path: `tasks/06-streaming-transcription/TASK.md`
  - Depends on: Tasks 02, 04.
  - Status: not started
- [ ] Task 07 — Implement Anonymous Speaker Diarization
  - Path: `tasks/07-speaker-diarization/TASK.md`
  - Depends on: Tasks 02, 06.
  - Status: not started
- [ ] Task 08 — Implement Meeting Session Store and Replayable Timeline
  - Path: `tasks/08-meeting-store-timeline/TASK.md`
  - Depends on: Tasks 02-03.
  - Status: not started
- [ ] Task 09 — Implement Provider and Role-Based Model Manager
  - Path: `tasks/09-model-provider-manager/TASK.md`
  - Depends on: Tasks 02-03, 08.
  - Status: not started
- [ ] Task 10 — Implement Tool and Connector Registries
  - Path: `tasks/10-tool-connector-registry/TASK.md`
  - Depends on: Tasks 02-03, 08.
  - Status: not started
- [ ] Task 11 — Implement Capability Registry, Workflow Runner, and Policy Engine
  - Path: `tasks/11-capability-policy-engine/TASK.md`
  - Depends on: Tasks 02, 08, 10.
  - Status: not started
- [ ] Task 12 — Implement Safe Excel Roadmap Connector and Tools
  - Path: `tasks/12-excel-roadmap-adapter/TASK.md`
  - Depends on: Tasks 02, 10.
  - Status: not started
- [ ] Task 13 — Implement the Update Roadmap Capability
  - Path: `tasks/13-update-roadmap-capability/TASK.md`
  - Depends on: Tasks 11-12.
  - Status: not started
- [ ] Task 14 — Implement Agent Orchestrator and Live Request Routing
  - Path: `tasks/14-agent-orchestrator/TASK.md`
  - Depends on: Tasks 06-11, 13.
  - Status: not started
- [ ] Task 15 — Implement the Meeting Agent Profile and Extraction Pipeline
  - Path: `tasks/15-meeting-profile/TASK.md`
  - Depends on: Tasks 08-09, 14.
  - Status: not started
- [ ] Task 16 — Build the Agent Inspector UI Shell and Event Transport
  - Path: `tasks/16-inspector-ui-shell/TASK.md`
  - Depends on: Tasks 01, 04, 08.
  - Status: not started
- [ ] Task 17 — Implement Inspector Audio, Wake, and Transcript Panels
  - Path: `tasks/17-inspector-audio-transcript/TASK.md`
  - Depends on: Tasks 05-07, 16.
  - Status: not started
- [ ] Task 18 — Implement Inspector Understanding, Plan, Tool, and Artifact Panels
  - Path: `tasks/18-inspector-reasoning-tools-results/TASK.md`
  - Depends on: Tasks 10-16.
  - Status: not started
- [ ] Task 19 — Implement Voice, Model, Connector, and Capability Settings
  - Path: `tasks/19-settings-console/TASK.md`
  - Depends on: Tasks 05, 09-11, 16.
  - Status: not started
- [ ] Task 20 — Run End-to-End Hardening, Diagnostics, and Local Release Packaging
  - Path: `tasks/20-e2e-hardening-release/TASK.md`
  - Depends on: Tasks 01-19 complete.
  - Status: not started

## Milestone gates

- **Foundation gate:** Tasks 00-03 complete; build, tests, and architecture rules pass.
- **Sensing gate:** Tasks 04-07 complete; real/fixture audio yields wake, transcript, and speakers.
- **Action gate:** Tasks 08-13 complete; structured update safely changes a workbook.
- **Agent gate:** Tasks 14-15 complete; live and final meeting reasoning routes through policies.
- **Inspector gate:** Tasks 16-19 complete; all critical states and results are visible/configurable.
- **V1 gate:** Task 20 complete; manual and automatic reference scenarios pass.

## Global reporting requirements

Every task report must include changed files, architecture decisions, exact test commands/results, diagnostics added, documentation updates, deviations, residual risks, and the recommended next task.
