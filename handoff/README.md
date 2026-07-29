# Jarvis Local Meeting Agent V1 — Implementation Handoff

This bundle converts the voice grilling session into an implementation-ready handoff for a fresh coding agent.

## Start here

1. Open `tasks/TODO.md`.
2. Run Task 00 first. It is the project orchestrator and must keep the task plan synchronized with implementation reality.
3. Complete tasks in order unless Task 00 records a justified dependency change.
4. For every coding task, load `/caveman` and `/coding-guideline` from `~/ai/skills/` before changing code.
5. Finish each task with the report format in `templates/final-implementation-report-template.md`.

## Bundle map

- `grill-session.md` — faithful reconstructed session and user corrections.
- `docs/00-overview.md` — goals, scope, non-goals, and product mental model.
- `docs/01-decision-log.md` — locked, provisional, and unresolved decisions.
- `docs/02-architecture-spec.md` — target architecture and runtime boundaries.
- `docs/03-implementation-strategy.md` — staged delivery plan.
- `docs/04-testing-and-quality.md` — test pyramid, diagnostics, and regression gates.
- `docs/05-data-model.md` — core entities and typed contracts.
- `docs/06-agent-inspector-ux.md` — V1 laboratory UI specification.
- `docs/07-model-and-provider-configuration.md` — model manager and access diagnostics.
- `docs/08-capability-and-tool-contracts.md` — capability, workflow, tool, and policy model.
- `docs/09-open-questions.md` — decisions that remain to be locked.
- `docs/10-security-and-data-handling.md` — local-first boundaries and secret handling.
- `tasks/TODO.md` — authoritative implementation entrypoint.

## Current status

The product direction is clear enough to implement a V1. The exact application stack, audio libraries, wake-word engine, model providers, and Excel integration mechanism remain explicit architecture decisions rather than hidden assumptions.
