from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import TypeAdapter, ValidationError

from jarvis_agent.application.event_store import EventStore
from jarvis_agent.application.redaction import redact
from jarvis_agent.domain.models import (
    Diagnostic,
    ErrorCode,
    ExecutionStatus,
    RuntimeEvent,
    ToolDefinition,
    ToolResult,
    new_id,
)

ToolHandler = Callable[[dict[str, Any]], ToolResult | Awaitable[ToolResult]]


class ToolRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        existing = self._definitions.get(definition.id)
        if existing and existing.version == definition.version:
            raise ValueError(f"Tool already registered: {definition.id}@{definition.version}")
        self._definitions[definition.id] = definition
        self._handlers[definition.id] = handler

    def get(self, tool_id: str) -> tuple[ToolDefinition, ToolHandler]:
        if tool_id not in self._definitions:
            raise KeyError(tool_id)
        return self._definitions[tool_id], self._handlers[tool_id]

    def list(self) -> list[ToolDefinition]:
        return sorted(self._definitions.values(), key=lambda item: item.id)


class ToolRunner:
    def __init__(self, registry: ToolRegistry, event_store: EventStore) -> None:
        self.registry = registry
        self.event_store = event_store

    async def invoke(
        self,
        *,
        session_id: str,
        meeting_session_id: str | None,
        plan_id: str,
        tool_id: str,
        arguments: dict[str, Any],
        correlation_id: str | None = None,
    ) -> ToolResult:
        correlation_id = correlation_id or new_id("corr")
        try:
            definition, handler = self.registry.get(tool_id)
        except KeyError:
            return ToolResult(
                status="failure",
                summary=f"Unknown tool: {tool_id}",
                diagnostics=(
                    Diagnostic(
                        code=ErrorCode.TOOL_NOT_FOUND,
                        message=f"Tool {tool_id} is not registered",
                        component="tool_runner",
                        correlation_id=correlation_id,
                    ),
                ),
            )
        try:
            TypeAdapter(dict[str, Any]).validate_python(arguments)
        except ValidationError as exc:
            return ToolResult(
                status="failure",
                summary="Invalid tool arguments",
                diagnostics=(
                    Diagnostic(
                        code=ErrorCode.VALIDATION_FAILED,
                        message=str(exc),
                        component="tool_runner",
                        correlation_id=correlation_id,
                    ),
                ),
            )
        await self.event_store.append(
            RuntimeEvent(
                session_id=session_id,
                meeting_session_id=meeting_session_id,
                event_type="tool.started",
                correlation_id=correlation_id,
                source="tool_runner",
                payload={
                    "plan_id": plan_id,
                    "tool_id": tool_id,
                    "arguments": redact(arguments, definition.redacted_fields),
                    "connector_id": definition.connector_id,
                    "mutates_external_state": definition.mutates_external_state,
                },
            )
        )
        try:
            value = handler(arguments)
            if inspect.isawaitable(value):
                value = await asyncio.wait_for(value, timeout=definition.timeout_seconds)
            result = value
            if not isinstance(result, ToolResult):
                raise TypeError("Tool handler must return ToolResult")
        except TimeoutError:
            result = ToolResult(
                status="failure",
                summary=f"Tool {tool_id} timed out",
                diagnostics=(
                    Diagnostic(
                        code=ErrorCode.TIMEOUT,
                        message=f"Tool exceeded {definition.timeout_seconds}s timeout",
                        component=tool_id,
                        retryable=True,
                        correlation_id=correlation_id,
                    ),
                ),
            )
        except asyncio.CancelledError:
            result = ToolResult(
                status="cancelled",
                summary=f"Tool {tool_id} was cancelled",
                diagnostics=(
                    Diagnostic(
                        code=ErrorCode.CANCELLED,
                        message="Invocation cancelled",
                        component=tool_id,
                        retryable=True,
                        correlation_id=correlation_id,
                    ),
                ),
            )
        except Exception as exc:  # noqa: BLE001 - boundary normalizes opaque connector failures
            result = ToolResult(
                status="failure",
                summary=f"Tool {tool_id} failed",
                diagnostics=(
                    Diagnostic(
                        code=ErrorCode.UNKNOWN,
                        message=f"{type(exc).__name__}: {exc}",
                        component=tool_id,
                        retryable=False,
                        correlation_id=correlation_id,
                    ),
                ),
            )
        await self.event_store.append(
            RuntimeEvent(
                session_id=session_id,
                meeting_session_id=meeting_session_id,
                event_type=(
                    "tool.completed"
                    if result.status.value == "success"
                    else "tool.failed"
                ),
                correlation_id=correlation_id,
                source="tool_runner",
                payload={
                    "plan_id": plan_id,
                    "tool_id": tool_id,
                    "status": result.status.value,
                    "summary": result.summary,
                    "data": result.data,
                    "artifact_refs": list(result.artifact_refs),
                    "diff_refs": list(result.diff_refs),
                    "diagnostics": [item.model_dump(mode="json") for item in result.diagnostics],
                },
            )
        )
        return result
