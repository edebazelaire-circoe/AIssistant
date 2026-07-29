from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from jarvis_agent.application.event_store import EventStore
from jarvis_agent.application.tools import ToolRegistry, ToolRunner
from jarvis_agent.connectors.excel_roadmap import ExcelRoadmapConnector
from jarvis_agent.domain.models import (
    CapabilityDefinition,
    CapabilityPolicy,
    CommandResult,
    Diagnostic,
    ErrorCode,
    ExecutionPlan,
    ExecutionStatus,
    PlanStep,
    PolicyMode,
    ResultStatus,
    RoadmapStatus,
    RoadmapUpdateInput,
    RuntimeEvent,
    ToolDefinition,
    ToolResult,
    new_id,
)


class Workflow(Protocol):
    id: str

    async def plan(
        self,
        *,
        session_id: str,
        meeting_session_id: str | None,
        payload: dict[str, Any],
        correlation_id: str,
    ) -> tuple[ExecutionPlan, dict[str, Any] | None, ToolResult | None]: ...

    async def execute(
        self,
        *,
        session_id: str,
        meeting_session_id: str | None,
        plan: ExecutionPlan,
        prepared: dict[str, Any],
    ) -> ToolResult: ...


@dataclass(slots=True)
class PendingApproval:
    approval_id: str
    token_hash: str
    expires_at: datetime
    session_id: str
    meeting_session_id: str | None
    plan: ExecutionPlan
    workflow_id: str
    prepared: dict[str, Any]
    used: bool = False


class CapabilityRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, CapabilityDefinition] = {}
        self._workflows: dict[str, Workflow] = {}

    def register(self, definition: CapabilityDefinition, workflow: Workflow) -> None:
        if definition.id in self._definitions:
            raise ValueError(f"Capability already registered: {definition.id}")
        if definition.workflow_id != workflow.id:
            raise ValueError("Capability workflow_id does not match workflow.id")
        self._definitions[definition.id] = definition
        self._workflows[workflow.id] = workflow

    def get(self, capability_id: str) -> tuple[CapabilityDefinition, Workflow]:
        definition = self._definitions[capability_id]
        return definition, self._workflows[definition.workflow_id]

    def list(self) -> list[CapabilityDefinition]:
        return sorted(self._definitions.values(), key=lambda item: item.id)


class CapabilityEngine:
    def __init__(self, registry: CapabilityRegistry, store: EventStore) -> None:
        self.registry = registry
        self.store = store
        self._pending: dict[str, PendingApproval] = {}

    def get_policy(self, capability_id: str) -> CapabilityPolicy:
        raw = self.store.get_setting(f"capability_policy:{capability_id}")
        if raw is None:
            definition, _ = self.registry.get(capability_id)
            return CapabilityPolicy(capability_id=capability_id, mode=definition.default_policy)
        return CapabilityPolicy.model_validate(raw)

    async def set_policy(self, policy: CapabilityPolicy, session_id: str) -> CapabilityPolicy:
        self.store.set_setting(
            f"capability_policy:{policy.capability_id}", policy.model_dump(mode="json")
        )
        await self.store.append(
            RuntimeEvent(
                session_id=session_id,
                event_type="capability.policy_changed",
                source="capability_engine",
                payload=policy.model_dump(mode="json"),
            )
        )
        return policy

    async def request(
        self,
        *,
        session_id: str,
        meeting_session_id: str | None,
        capability_id: str,
        payload: dict[str, Any],
        reason: str,
    ) -> CommandResult:
        try:
            definition, workflow = self.registry.get(capability_id)
        except KeyError:
            return CommandResult(
                status=ResultStatus.FAILURE,
                summary=f"Unknown capability: {capability_id}",
                diagnostics=(
                    Diagnostic(
                        code=ErrorCode.VALIDATION_FAILED,
                        message=f"Capability {capability_id} is not registered",
                        component="capability_engine",
                    ),
                ),
            )
        correlation_id = new_id("corr")
        plan, prepared, planning_result = await workflow.plan(
            session_id=session_id,
            meeting_session_id=meeting_session_id,
            payload=payload,
            correlation_id=correlation_id,
        )
        plan = plan.model_copy(update={"reason": reason})
        await self.store.append(
            RuntimeEvent(
                session_id=session_id,
                meeting_session_id=meeting_session_id,
                event_type="plan.created",
                correlation_id=correlation_id,
                source="capability_engine",
                payload=plan.model_dump(mode="json"),
            )
        )
        if planning_result is not None and planning_result.status != ResultStatus.SUCCESS:
            await self._emit_result(session_id, meeting_session_id, plan, planning_result)
            return CommandResult(
                status=planning_result.status,
                summary=planning_result.summary,
                data={"plan": plan.model_dump(mode="json")},
                diagnostics=planning_result.diagnostics,
            )
        if prepared is None:
            return CommandResult(status=ResultStatus.FAILURE, summary="Workflow did not prepare execution")
        policy = self.get_policy(capability_id)
        await self.store.append(
            RuntimeEvent(
                session_id=session_id,
                meeting_session_id=meeting_session_id,
                event_type="policy.evaluated",
                correlation_id=correlation_id,
                source="capability_engine",
                payload={
                    "capability_id": capability_id,
                    "mode": policy.mode.value,
                    "confidence": payload.get("confidence"),
                },
            )
        )
        if policy.mode == PolicyMode.DISABLED:
            diagnostic = Diagnostic(
                code=ErrorCode.CAPABILITY_DISABLED,
                message=f"Capability {capability_id} is disabled",
                component="capability_engine",
                correlation_id=correlation_id,
            )
            return CommandResult(
                status=ResultStatus.FAILURE,
                summary=diagnostic.message,
                data={"plan": plan.model_dump(mode="json")},
                diagnostics=(diagnostic,),
            )
        if (
            policy.confidence_threshold is not None
            and float(payload.get("confidence", 0.0)) < policy.confidence_threshold
        ):
            diagnostic = Diagnostic(
                code=ErrorCode.APPROVAL_REQUIRED,
                message="Confidence is below the automatic threshold",
                component="capability_engine",
                correlation_id=correlation_id,
                suggested_action="Review the proposed row and approve manually.",
            )
            return await self._create_approval(
                session_id, meeting_session_id, plan, workflow.id, prepared, diagnostic
            )
        if policy.mode == PolicyMode.MANUAL:
            return await self._create_approval(
                session_id, meeting_session_id, plan, workflow.id, prepared, None
            )
        result = await workflow.execute(
            session_id=session_id,
            meeting_session_id=meeting_session_id,
            plan=plan,
            prepared=prepared,
        )
        final_plan = plan.model_copy(
            update={
                "status": ExecutionStatus.COMPLETED
                if result.status == ResultStatus.SUCCESS
                else ExecutionStatus.FAILED
            }
        )
        await self._emit_result(session_id, meeting_session_id, final_plan, result)
        return CommandResult(
            status=result.status,
            summary=result.summary,
            data={
                "plan": final_plan.model_dump(mode="json"),
                "result": result.model_dump(mode="json"),
            },
            diagnostics=result.diagnostics,
        )

    async def approve(self, approval_id: str, token: str) -> CommandResult:
        pending = self._pending.get(approval_id)
        if pending is None or pending.used:
            return self._approval_error("Unknown or already used approval")
        if datetime.now(UTC) >= pending.expires_at:
            pending.used = True
            return self._approval_error("Approval expired")
        if not secrets.compare_digest(pending.token_hash, _token_hash(token)):
            return self._approval_error("Approval token is invalid")
        pending.used = True
        _, workflow = self.registry.get(pending.plan.capability_id)
        approved_plan = pending.plan.model_copy(update={"status": ExecutionStatus.RUNNING})
        await self.store.append(
            RuntimeEvent(
                session_id=pending.session_id,
                meeting_session_id=pending.meeting_session_id,
                event_type="approval.granted",
                correlation_id=pending.plan.correlation_id,
                source="capability_engine",
                payload={"approval_id": approval_id, "plan_id": pending.plan.id},
            )
        )
        result = await workflow.execute(
            session_id=pending.session_id,
            meeting_session_id=pending.meeting_session_id,
            plan=approved_plan,
            prepared=pending.prepared,
        )
        final_plan = approved_plan.model_copy(
            update={
                "status": ExecutionStatus.COMPLETED
                if result.status == ResultStatus.SUCCESS
                else ExecutionStatus.FAILED
            }
        )
        await self._emit_result(
            pending.session_id, pending.meeting_session_id, final_plan, result
        )
        return CommandResult(
            status=result.status,
            summary=result.summary,
            data={
                "plan": final_plan.model_dump(mode="json"),
                "result": result.model_dump(mode="json"),
            },
            diagnostics=result.diagnostics,
        )

    async def reject(self, approval_id: str) -> CommandResult:
        pending = self._pending.get(approval_id)
        if pending is None or pending.used:
            return self._approval_error("Unknown or already used approval")
        pending.used = True
        await self.store.append(
            RuntimeEvent(
                session_id=pending.session_id,
                meeting_session_id=pending.meeting_session_id,
                event_type="approval.rejected",
                correlation_id=pending.plan.correlation_id,
                source="capability_engine",
                payload={"approval_id": approval_id, "plan_id": pending.plan.id},
            )
        )
        return CommandResult(status=ResultStatus.CANCELLED, summary="Execution rejected")

    async def _create_approval(
        self,
        session_id: str,
        meeting_session_id: str | None,
        plan: ExecutionPlan,
        workflow_id: str,
        prepared: dict[str, Any],
        diagnostic: Diagnostic | None,
    ) -> CommandResult:
        approval_id = new_id("approval")
        token = secrets.token_urlsafe(24)
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        pending = PendingApproval(
            approval_id=approval_id,
            token_hash=_token_hash(token),
            expires_at=expires_at,
            session_id=session_id,
            meeting_session_id=meeting_session_id,
            plan=plan.model_copy(
                update={
                    "status": ExecutionStatus.WAITING_APPROVAL,
                    "approval_request_id": approval_id,
                }
            ),
            workflow_id=workflow_id,
            prepared=prepared,
        )
        self._pending[approval_id] = pending
        preview = prepared.get("proposal", prepared)
        await self.store.append(
            RuntimeEvent(
                session_id=session_id,
                meeting_session_id=meeting_session_id,
                event_type="approval.requested",
                correlation_id=plan.correlation_id,
                source="capability_engine",
                payload={
                    "approval_id": approval_id,
                    "plan_id": plan.id,
                    "capability_id": plan.capability_id,
                    "expires_at": expires_at.isoformat(),
                    "preview": preview,
                },
            )
        )
        diagnostics = () if diagnostic is None else (diagnostic,)
        return CommandResult(
            status=ResultStatus.NEEDS_APPROVAL,
            summary="Manual approval required before workbook mutation",
            data={
                "approval_id": approval_id,
                "approval_token": token,
                "expires_at": expires_at.isoformat(),
                "plan": pending.plan.model_dump(mode="json"),
                "preview": preview,
            },
            diagnostics=diagnostics,
        )

    async def _emit_result(
        self,
        session_id: str,
        meeting_session_id: str | None,
        plan: ExecutionPlan,
        result: ToolResult,
    ) -> None:
        await self.store.append(
            RuntimeEvent(
                session_id=session_id,
                meeting_session_id=meeting_session_id,
                event_type=(
                    "plan.completed" if result.status == ResultStatus.SUCCESS else "plan.failed"
                ),
                correlation_id=plan.correlation_id,
                source="capability_engine",
                payload={
                    "plan_id": plan.id,
                    "plan": plan.model_dump(mode="json"),
                    "status": result.status.value,
                    "summary": result.summary,
                    "result": result.model_dump(mode="json"),
                },
            )
        )
        if result.status == ResultStatus.SUCCESS and result.data.get("artifact"):
            await self.store.append(
                RuntimeEvent(
                    session_id=session_id,
                    meeting_session_id=meeting_session_id,
                    event_type="artifact.created",
                    correlation_id=plan.correlation_id,
                    source="capability_engine",
                    payload={
                        "artifact": result.data["artifact"],
                        "diff": result.data.get("diff"),
                        "preview": result.data.get("preview"),
                        "rollback_ref": result.rollback_ref,
                    },
                )
            )

    @staticmethod
    def _approval_error(message: str) -> CommandResult:
        return CommandResult(
            status=ResultStatus.FAILURE,
            summary=message,
            diagnostics=(
                Diagnostic(
                    code=ErrorCode.APPROVAL_INVALID,
                    message=message,
                    component="capability_engine",
                ),
            ),
        )


class UpdateRoadmapWorkflow:
    id = "workflow.update_roadmap.v1"

    def __init__(
        self,
        connector: ExcelRoadmapConnector,
        tool_runner: ToolRunner,
    ) -> None:
        self.connector = connector
        self.tool_runner = tool_runner

    async def plan(
        self,
        *,
        session_id: str,
        meeting_session_id: str | None,
        payload: dict[str, Any],
        correlation_id: str,
    ) -> tuple[ExecutionPlan, dict[str, Any] | None, ToolResult | None]:
        try:
            update = RoadmapUpdateInput.model_validate(payload)
        except Exception as exc:
            plan = self._plan(session_id, correlation_id, payload)
            result = ToolResult(
                status=ResultStatus.FAILURE,
                summary="Invalid roadmap update input",
                diagnostics=(
                    Diagnostic(
                        code=ErrorCode.VALIDATION_FAILED,
                        message=str(exc),
                        component="update_roadmap",
                        correlation_id=correlation_id,
                    ),
                ),
            )
            return plan, None, result
        workbook_path = update.workbook_path
        if not workbook_path:
            candidates = self.connector.discover()
            if len(candidates) != 1:
                plan = self._plan(session_id, correlation_id, payload)
                result = ToolResult(
                    status=ResultStatus.NEEDS_RESOLUTION,
                    summary=(
                        "Select a workbook" if candidates else "No workbook found in allowed root"
                    ),
                    data={"candidates": [str(path) for path in candidates]},
                    diagnostics=(
                        Diagnostic(
                            code=ErrorCode.WORKBOOK_SCHEMA_AMBIGUOUS,
                            message=f"Found {len(candidates)} workbook candidates",
                            component="update_roadmap",
                            correlation_id=correlation_id,
                            suggested_action="Choose an explicit workbook path in the Inspector.",
                        ),
                    ),
                )
                return plan, None, result
            workbook_path = str(candidates[0])
        proposal_result = await self.tool_runner.invoke(
            session_id=session_id,
            meeting_session_id=meeting_session_id,
            plan_id="planning",
            tool_id="excel.propose_roadmap_update",
            arguments={
                "workbook_path": workbook_path,
                "action_text": update.action_text,
                "desired_status": update.desired_status.value,
                "owner": update.owner,
                "month": update.month,
                "sheet_hint": update.sheet_hint,
            },
            correlation_id=correlation_id,
        )
        plan = self._plan(session_id, correlation_id, {**payload, "workbook_path": workbook_path})
        if proposal_result.status != ResultStatus.SUCCESS:
            return plan, None, proposal_result
        return plan, {"proposal": proposal_result.data["proposal"]}, None

    async def execute(
        self,
        *,
        session_id: str,
        meeting_session_id: str | None,
        plan: ExecutionPlan,
        prepared: dict[str, Any],
    ) -> ToolResult:
        return await self.tool_runner.invoke(
            session_id=session_id,
            meeting_session_id=meeting_session_id,
            plan_id=plan.id,
            tool_id="excel.apply_roadmap_update",
            arguments={"proposal": prepared["proposal"]},
            correlation_id=plan.correlation_id,
        )

    @staticmethod
    def _plan(
        session_id: str, correlation_id: str, payload: dict[str, Any]
    ) -> ExecutionPlan:
        return ExecutionPlan(
            session_id=session_id,
            capability_id="update_roadmap",
            reason="Structured roadmap status update",
            confidence=float(payload.get("confidence", 1.0)),
            correlation_id=correlation_id,
            steps=(
                PlanStep(
                    index=1,
                    tool_id="excel.propose_roadmap_update",
                    description="Open the workbook read-only, detect schema and locate the action row",
                    arguments={key: value for key, value in payload.items() if value is not None},
                    mutates_external_state=False,
                ),
                PlanStep(
                    index=2,
                    tool_id="excel.apply_roadmap_update",
                    description="Write a safe copy, verify it, atomically replace and publish a diff",
                    arguments={},
                    mutates_external_state=True,
                ),
            ),
        )


def register_excel_tools(registry: ToolRegistry, connector: ExcelRoadmapConnector) -> None:
    registry.register(
        ToolDefinition(
            id="excel.propose_roadmap_update",
            description="Locate a roadmap row and return a non-mutating proposed cell change",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            mutates_external_state=False,
            connector_id="excel",
            permission_scope="workbook.read",
        ),
        lambda arguments: _propose_tool(connector, arguments),
    )
    registry.register(
        ToolDefinition(
            id="excel.apply_roadmap_update",
            description="Safely apply and verify a previously fingerprinted roadmap proposal",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            mutates_external_state=True,
            connector_id="excel",
            permission_scope="workbook.write",
            timeout_seconds=30.0,
        ),
        lambda arguments: connector.apply(arguments["proposal"]),
    )
    registry.register(
        ToolDefinition(
            id="excel.rollback",
            description="Restore a workbook from a safe backup",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            mutates_external_state=True,
            connector_id="excel",
            permission_scope="workbook.write",
        ),
        lambda arguments: connector.rollback(arguments["backup_path"], arguments["target_path"]),
    )


def register_update_roadmap_capability(
    registry: CapabilityRegistry, workflow: UpdateRoadmapWorkflow
) -> None:
    registry.register(
        CapabilityDefinition(
            id="update_roadmap",
            name="Mettre à jour la roadmap",
            description="Trouve une action dans un classeur Excel et met à jour son statut avec un diff visible.",
            input_schema=RoadmapUpdateInput.model_json_schema(),
            output_schema=ToolResult.model_json_schema(),
            workflow_id=workflow.id,
            mutates_external_state=True,
            default_policy=PolicyMode.MANUAL,
            required_connector_ids=("excel",),
        ),
        workflow,
    )


def _propose_tool(connector: ExcelRoadmapConnector, arguments: dict[str, Any]) -> ToolResult:
    try:
        path = connector.resolve_allowed(arguments["workbook_path"])
        proposal = connector.propose(
            path=path,
            action_text=arguments["action_text"],
            desired_status=RoadmapStatus(arguments["desired_status"]),
            owner=arguments.get("owner"),
            month=arguments.get("month"),
            sheet_hint=arguments.get("sheet_hint"),
        )
        return ToolResult(
            status=ResultStatus.SUCCESS,
            summary="Roadmap change proposal prepared",
            data={"proposal": proposal},
        )
    except PermissionError as exc:
        code = ErrorCode.PATH_NOT_ALLOWED
    except LookupError as exc:
        code = ErrorCode.ROADMAP_ROW_NOT_FOUND
    except RuntimeError as exc:
        code = ErrorCode.ROADMAP_ROW_AMBIGUOUS
    except ValueError as exc:
        code = ErrorCode.WORKBOOK_SCHEMA_AMBIGUOUS
    except Exception as exc:  # noqa: BLE001
        code = ErrorCode.UNKNOWN
    return ToolResult(
        status=ResultStatus.NEEDS_RESOLUTION,
        summary=str(exc),
        diagnostics=(
            Diagnostic(
                code=code,
                message=str(exc),
                component="excel.propose_roadmap_update",
                suggested_action="Review workbook, sheet and action matching in the Inspector.",
            ),
        ),
    )


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
