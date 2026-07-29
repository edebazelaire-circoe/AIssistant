# Task 00 — Orchestrate the Implementation Program

## Goal

Act as the project manager for this handoff, keep the task graph accurate, and prevent agents from skipping validation or mixing unrelated slices.

## Context

This is the mandatory first task. The handoff describes a local-first meeting agent prototype centered on an Agent Inspector and an Excel roadmap vertical slice. The orchestrator owns sequencing, status, and plan corrections.

## Scope
### In Scope
- Read every root document and `tasks/TODO.md`.
- Create or update the implementation plan in the repository.
- Check prerequisites before dispatching each task.
- Mark task status only after acceptance evidence exists.
- Edit raw task files or create new task slices when implementation reality exposes a missing dependency.
- Ensure each coding agent loads `/caveman` and `/coding-guideline`.
- Require the final implementation report template after each task.

### Out of Scope
- Implement product code directly unless no separate coding task can reasonably own the change.
- Collapse multiple unfinished tasks into a single broad implementation pass.

## Dependencies

- None. This task always runs first and remains active throughout the program.

## Implementation Steps

1. Read `README.md`, all `docs/`, all task files, and templates.
2. Create an authoritative status ledger from `tasks/TODO.md`.
3. Validate task order against repository reality.
4. Select exactly one next task and dispatch it with its dependencies and constraints.
5. Review each returned report and test evidence.
6. Approve, request rework, or split the task.
7. Update `tasks/TODO.md` and affected task files before moving on.

## Files Likely Touched

- `tasks/TODO.md`
- `tasks/*/TASK.md` when corrections are needed
- repository planning/status files
- implementation reports

## Architecture Constraints

- Stay in orchestration mode.
- Do not declare completion from prose alone; require evidence.
- Preserve locked decisions and label any new decision explicitly.
- Do not let vendor details leak into core architecture.

## Testing Requirements

- Validate task numbering and dependency order.
- Verify every completed task has acceptance evidence and a report.
- Run project-wide gates at milestones.

## Acceptance Criteria

- [ ] An up-to-date task ledger exists.
- [ ] Exactly one next task is selected at a time.
- [ ] No task advances without completed dependencies.
- [ ] Plan/task changes are documented with rationale.

## Documentation Updates

- Keep `tasks/TODO.md` authoritative.
- Record new ADRs/open questions in the relevant docs.

## Handoff Notes

This task is the control plane for the entire handoff. It must continue until the final project gate passes.
