from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=False)


class AgentState(StrEnum):
    MIC_OFF = "MIC_OFF"
    STANDBY = "STANDBY"
    TRANSCRIBING = "TRANSCRIBING"
    INTERACTIVE = "INTERACTIVE"
    ERROR_RECOVERABLE = "ERROR_RECOVERABLE"


class PolicyMode(StrEnum):
    DISABLED = "disabled"
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class ResultStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    NEEDS_APPROVAL = "needs_approval"
    NEEDS_RESOLUTION = "needs_resolution"
    CANCELLED = "cancelled"


class ExecutionStatus(StrEnum):
    PROPOSED = "proposed"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class FactType(StrEnum):
    DECISION = "decision"
    ACTION_ITEM = "action_item"
    QUESTION = "question"
    ANSWER = "answer"
    RISK = "risk"
    OPEN_POINT = "open_point"


class RoadmapStatus(StrEnum):
    NOT_DONE = "not_done"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class ModelRole(StrEnum):
    REALTIME = "realtime"
    TRANSCRIPTION = "transcription"
    DIARIZATION = "diarization"
    ANALYSIS = "analysis"
    CLASSIFICATION = "classification"
    EMBEDDING = "embedding"
    LOCAL_ROUTER = "local_router"


class ErrorCode(StrEnum):
    INVALID_TRANSITION = "invalid_transition"
    VALIDATION_FAILED = "validation_failed"
    SECRET_MISSING = "secret_missing"
    AUTHENTICATION_FAILED = "authentication_failed"
    PROJECT_NOT_FOUND = "project_not_found"
    BILLING_OR_QUOTA_BLOCKED = "billing_or_quota_blocked"
    MODEL_NOT_FOUND = "model_not_found"
    MODEL_ACCESS_DENIED = "model_access_denied"
    ROLE_NOT_SUPPORTED = "role_not_supported"
    TRANSPORT_NOT_SUPPORTED = "transport_not_supported"
    SESSION_HANDSHAKE_FAILED = "session_handshake_failed"
    RATE_LIMITED = "rate_limited"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PATH_NOT_ALLOWED = "path_not_allowed"
    FILE_CHANGED = "file_changed"
    WORKBOOK_SCHEMA_AMBIGUOUS = "workbook_schema_ambiguous"
    ROADMAP_ROW_AMBIGUOUS = "roadmap_row_ambiguous"
    ROADMAP_ROW_NOT_FOUND = "roadmap_row_not_found"
    TOOL_NOT_FOUND = "tool_not_found"
    CAPABILITY_DISABLED = "capability_disabled"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_INVALID = "approval_invalid"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class Diagnostic(FrozenModel):
    code: ErrorCode | str
    message: str
    component: str
    retryable: bool = False
    correlation_id: str | None = None
    suggested_action: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("details")
    @classmethod
    def reject_secretish_details(cls, value: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"api_key", "secret", "password", "authorization", "token"}
        for key in value:
            if key.lower() in forbidden:
                raise ValueError(f"secret-like field is forbidden in diagnostics: {key}")
        return value


class RuntimeEvent(FrozenModel):
    id: str = Field(default_factory=lambda: new_id("evt"))
    version: int = 1
    sequence: int | None = None
    session_id: str
    meeting_session_id: str | None = None
    event_type: str
    occurred_at: datetime = Field(default_factory=utcnow)
    correlation_id: str = Field(default_factory=lambda: new_id("corr"))
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("payload")
    @classmethod
    def reject_raw_secrets(cls, value: dict[str, Any]) -> dict[str, Any]:
        def walk(obj: Any, path: str = "payload") -> None:
            if isinstance(obj, dict):
                for key, nested in obj.items():
                    if any(marker in key.lower() for marker in ("api_key", "password", "authorization")):
                        raise ValueError(f"secret-like field forbidden at {path}.{key}")
                    walk(nested, f"{path}.{key}")
            elif isinstance(obj, list):
                for idx, nested in enumerate(obj):
                    walk(nested, f"{path}[{idx}]")
        walk(value)
        return value


class AgentSession(FrozenModel):
    id: str = Field(default_factory=lambda: new_id("agent"))
    created_at: datetime = Field(default_factory=utcnow)
    current_state: AgentState = AgentState.MIC_OFF
    previous_safe_state: AgentState = AgentState.MIC_OFF
    active_profile_id: str | None = None
    meeting_session_id: str | None = None
    selected_model_config_id: str | None = None
    event_cursor: int = 0


class MeetingSession(FrozenModel):
    id: str = Field(default_factory=lambda: new_id("meeting"))
    title: str | None = None
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None
    status: Literal["active", "ended", "deleted"] = "active"
    participant_hints: tuple[str, ...] = ()
    summary_status: Literal["not_started", "running", "completed", "failed"] = "not_started"


class AudioFrame(FrozenModel):
    sequence: int
    timestamp_ms: int
    sample_rate: int = 16000
    channels: int = 1
    pcm16_b64: str
    level: float = Field(ge=0.0, le=1.0)


class TranscriptSegment(FrozenModel):
    id: str = Field(default_factory=lambda: new_id("seg"))
    meeting_session_id: str
    start_ms: int = 0
    end_ms: int = 0
    text: str
    is_final: bool
    speaker_cluster_id: str | None = None
    person_id: str | None = None
    language: str | None = "fr"
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_adapter: str
    revision_of: str | None = None


class SpeakerCluster(FrozenModel):
    id: str = Field(default_factory=lambda: new_id("speaker"))
    meeting_session_id: str
    display_label: str
    person_id: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    embedding_ref: str | None = None


class MeetingFact(FrozenModel):
    id: str = Field(default_factory=lambda: new_id("fact"))
    meeting_session_id: str
    fact_type: FactType
    text: str
    source_segment_ids: tuple[str, ...] = ()
    speaker_cluster_ids: tuple[str, ...] = ()
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: str = "open"
    created_at: datetime = Field(default_factory=utcnow)
    description: str | None = None
    owner_person_id: str | None = None
    owner_speaker_cluster_id: str | None = None
    due_date: str | None = None
    roadmap_row_ref: str | None = None
    execution_status: str | None = None


class ProviderConfig(FrozenModel):
    id: str = Field(default_factory=lambda: new_id("provider"))
    provider_type: str
    display_name: str
    secret_reference: str
    base_url: str | None = None
    project_or_org_ref: str | None = None
    enabled: bool = True


class ModelAssignment(FrozenModel):
    role: ModelRole
    provider_config_id: str
    model_id: str
    capabilities: tuple[str, ...] = ()
    parameters: dict[str, Any] = Field(default_factory=dict)


class ProviderDiagnosticStage(FrozenModel):
    stage: str
    ok: bool
    code: str | None = None
    message: str
    latency_ms: int | None = None


class ProviderDiagnosticReport(FrozenModel):
    provider_config_id: str
    role: ModelRole | None = None
    model_id: str | None = None
    stages: tuple[ProviderDiagnosticStage, ...]
    checked_at: datetime = Field(default_factory=utcnow)


class ConnectorHealth(FrozenModel):
    connector_id: str
    status: Literal["healthy", "degraded", "unavailable"]
    message: str
    checked_at: datetime = Field(default_factory=utcnow)
    permissions: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(FrozenModel):
    id: str
    version: str = "1.0"
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    mutates_external_state: bool
    connector_id: str
    permission_scope: str
    timeout_seconds: float = 15.0
    idempotency: str = "best_effort"
    redacted_fields: tuple[str, ...] = ()


class ToolCall(FrozenModel):
    id: str = Field(default_factory=lambda: new_id("call"))
    plan_id: str
    tool_id: str
    arguments_redacted: dict[str, Any]
    started_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
    status: ExecutionStatus = ExecutionStatus.RUNNING
    result_ref: str | None = None
    error: Diagnostic | None = None
    correlation_id: str = Field(default_factory=lambda: new_id("corr"))


class Artifact(FrozenModel):
    id: str = Field(default_factory=lambda: new_id("artifact"))
    artifact_type: str
    display_name: str
    uri_or_local_ref: str
    mime_type: str
    preview_ref: str | None = None
    version: str
    created_by_tool_call_id: str | None = None


class ArtifactDiff(FrozenModel):
    id: str = Field(default_factory=lambda: new_id("diff"))
    artifact_id: str
    before_version: str
    after_version: str
    changes: tuple[dict[str, Any], ...]
    visual_highlights: tuple[dict[str, Any], ...] = ()


class ToolResult(FrozenModel):
    status: ResultStatus
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: tuple[str, ...] = ()
    diff_refs: tuple[str, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    rollback_ref: str | None = None


class PlanStep(FrozenModel):
    index: int
    tool_id: str
    description: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    mutates_external_state: bool = False


class ExecutionPlan(FrozenModel):
    id: str = Field(default_factory=lambda: new_id("plan"))
    session_id: str
    capability_id: str
    steps: tuple[PlanStep, ...]
    reason: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    status: ExecutionStatus = ExecutionStatus.PROPOSED
    approval_request_id: str | None = None
    correlation_id: str = Field(default_factory=lambda: new_id("corr"))


class CapabilityDefinition(FrozenModel):
    id: str
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    workflow_id: str
    mutates_external_state: bool
    default_policy: PolicyMode = PolicyMode.MANUAL
    required_connector_ids: tuple[str, ...] = ()


class CapabilityPolicy(FrozenModel):
    capability_id: str
    mode: PolicyMode = PolicyMode.MANUAL
    scope_constraints: dict[str, Any] = Field(default_factory=dict)
    confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    updated_at: datetime = Field(default_factory=utcnow)


class ApprovalRequest(FrozenModel):
    id: str = Field(default_factory=lambda: new_id("approval"))
    plan_id: str
    capability_id: str
    token_hash: str
    preview: dict[str, Any]
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    status: Literal["pending", "approved", "rejected", "expired", "used"] = "pending"


class RoadmapItem(FrozenModel):
    row_id: str
    action_text: str
    owner: str | None = None
    month: str | None = None
    status: RoadmapStatus
    status_cell: str
    display_color: str
    source_sheet: str
    source_row_number: int


class RoadmapUpdateInput(FrozenModel):
    action_text: str
    desired_status: RoadmapStatus
    workbook_path: str | None = None
    sheet_hint: str | None = None
    owner: str | None = None
    month: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class CommandResult(FrozenModel):
    status: ResultStatus
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    diagnostics: tuple[Diagnostic, ...] = ()
