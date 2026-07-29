# 08 — Capability and Tool Contracts

## Vocabulary

### Connector

A boundary to an external system or artifact type: file system, Excel workbook engine, MCP server, document base.

### Tool

A small, deterministic operation exposed to workflows, for example:

- `files.find`
- `excel.open_workbook`
- `excel.read_table`
- `excel.update_cell`
- `excel.set_fill`
- `excel.save_workbook`
- `artifacts.render_preview`

### Workflow

An ordered, validated composition of tools with typed intermediate state.

### Capability

A user/business-level action such as `update_roadmap`.

### Agent profile

A runtime bundle containing instructions, extraction schemas, enabled capabilities, and defaults. `meeting` is the first profile.

## Tool contract

Each tool exposes:

- stable ID and version;
- description for planners;
- typed input schema;
- typed output schema;
- mutation flag;
- required connector and permission scope;
- timeout/retry policy;
- idempotency behavior;
- diagnostics schema.

Tools return typed result objects. They do not throw opaque vendor exceptions across the boundary.

## Workflow contract

A workflow defines:

- accepted capability input;
- ordered steps;
- preconditions;
- rollback/compensation where possible;
- produced artifacts and diffs;
- completion criteria;
- failure policy.

The model may choose or parameterize a workflow, but cannot invent unregistered tool names.

## Capability policy

### Disabled

- Planning may explain that the capability is unavailable.
- No execution or approval request.

### Manual

- Plan is created and displayed.
- Approval request contains material changes and target artifacts.
- Only a valid approval token releases mutating steps.

### Automatic

- Plan and policy decision are recorded.
- Execution begins without human approval.
- Results, diffs, and rollback metadata remain visible.

## `update_roadmap` capability

### Inputs

- meeting-derived action/status update;
- optional workbook path or allowed search root;
- optional sheet/month hint;
- optional owner;
- desired status.

### Workflow

1. Resolve allowed workspace/folder.
2. Find candidate roadmap workbooks.
3. Open selected workbook read-only.
4. Detect roadmap sheet/table schema.
5. Locate action row using deterministic matching plus confidence.
6. Produce proposed change set.
7. Evaluate capability policy.
8. If manual, request approval with row/cell preview.
9. Create a safe working copy.
10. Update status value.
11. Apply mapped color: red/yellow/green.
12. Save atomically.
13. Reopen and verify persisted values/styles.
14. Generate before/after diff and preview.
15. Emit artifact and audit events.

### Ambiguity rules

Do not mutate automatically when:

- multiple rows are equally plausible;
- no stable row match exists;
- workbook schema is unrecognized;
- file is outside allowed roots;
- workbook is locked or changed after read;
- status mapping is inconsistent.

Manual mode presents choices. Automatic mode returns a structured “needs resolution” result rather than guessing.
