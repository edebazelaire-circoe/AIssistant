# 05 — Data Model

## Core entities

### AgentSession

- `id`
- `created_at`
- `current_state`
- `active_profile_id`
- `meeting_session_id?`
- `selected_model_config_id`
- `event_cursor`

### MeetingSession

- `id`
- `title?`
- `started_at`
- `ended_at?`
- `status`
- `participant_hints[]`
- `transcript_segment_ids[]`
- `decision_ids[]`
- `action_item_ids[]`
- `artifact_ids[]`
- `summary_status`

### TranscriptSegment

- `id`
- `meeting_session_id`
- `start_ms`
- `end_ms`
- `text`
- `is_final`
- `speaker_cluster_id?`
- `person_id?`
- `language?`
- `confidence?`
- `source_adapter`
- `revision_of?`

### SpeakerCluster

- `id`
- `meeting_session_id`
- `display_label`
- `person_id?`
- `confidence?`
- `embedding_ref?` — deferred and never required for V1

### MeetingFact

A union of:

- `Decision`
- `ActionItem`
- `Question`
- `Answer`
- `Risk`
- `OpenPoint`

Common fields:

- `id`
- `meeting_session_id`
- `fact_type`
- `text`
- `source_segment_ids[]`
- `speaker_cluster_ids[]`
- `confidence`
- `status`
- `created_at`

### ActionItem

- `description`
- `owner_person_id?`
- `owner_speaker_cluster_id?`
- `due_date?`
- `roadmap_row_ref?`
- `execution_status`

### CapabilityDefinition

- `id`
- `name`
- `description`
- `input_schema`
- `output_schema`
- `workflow_id`
- `mutates_external_state`
- `default_policy`
- `required_connector_ids[]`

### CapabilityPolicy

- `capability_id`
- `mode`: `disabled | manual | automatic`
- `scope_constraints`
- `confidence_threshold?`
- `updated_at`

### ExecutionPlan

- `id`
- `session_id`
- `capability_id`
- `steps[]`
- `reason`
- `confidence?`
- `status`
- `approval_request_id?`

### ToolCall

- `id`
- `plan_id`
- `tool_id`
- `arguments_redacted`
- `started_at`
- `completed_at?`
- `status`
- `result_ref?`
- `error?`
- `correlation_id`

### ToolResult

- `status`
- `summary`
- `data`
- `artifact_refs[]`
- `diff_refs[]`
- `diagnostics[]`
- `rollback_ref?`

### Artifact

- `id`
- `artifact_type`
- `display_name`
- `uri_or_local_ref`
- `mime_type`
- `preview_ref?`
- `version`
- `created_by_tool_call_id?`

### ArtifactDiff

- `id`
- `artifact_id`
- `before_version`
- `after_version`
- `changes[]`
- `visual_highlights[]`

### ProviderConfig

- `id`
- `provider_type`
- `display_name`
- `secret_reference`
- `base_url?`
- `project_or_org_ref?`
- `enabled`

### ModelAssignment

- `role`: `realtime | transcription | diarization | analysis | classification | embedding | local_router`
- `provider_config_id`
- `model_id`
- `capabilities[]`
- `parameters`

## Roadmap row contract

The workbook adapter must map each row to a typed `RoadmapItem`:

- `row_id` or stable row key
- `action_text`
- `owner?`
- `month?`
- `status`: `not_done | in_progress | done`
- `status_cell`
- `display_color`
- `source_sheet`
- `source_row_number`

Colors are presentation outputs, not the source of truth when a status value exists. The adapter should preserve both value and style mapping.
