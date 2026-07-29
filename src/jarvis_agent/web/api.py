from __future__ import annotations

import asyncio
import base64
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from jarvis_agent.application.config import AppConfig
from jarvis_agent.application.runtime import JarvisRuntime
from jarvis_agent.domain.models import (
    AgentState,
    AudioFrame,
    ModelAssignment,
    ModelRole,
    PolicyMode,
    ProviderConfig,
)


class StateRequest(BaseModel):
    state: AgentState
    reason: str = "ui_command"


class MeetingStartRequest(BaseModel):
    title: str | None = None


class TranscriptRequest(BaseModel):
    text: str = Field(min_length=1)
    speaker_hint: str | None = None
    overlap: bool = False
    auto_route: bool = True


class AskRequest(BaseModel):
    text: str = Field(min_length=1)


class SettingsRequest(BaseModel):
    values: dict[str, Any]


class PolicyRequest(BaseModel):
    mode: PolicyMode
    confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class CapabilityRequest(BaseModel):
    payload: dict[str, Any]
    reason: str = "Inspector request"


class ApprovalRequestBody(BaseModel):
    token: str


class WakeEnrollmentRequest(BaseModel):
    label: str
    phrase_type: str
    frames: list[dict[str, Any]]


class DiagnosticRequest(BaseModel):
    role: ModelRole | None = None
    model_id: str | None = None


class ProviderUpsertRequest(BaseModel):
    provider: ProviderConfig


class AssignmentRequest(BaseModel):
    assignment: ModelAssignment


def create_app(config: AppConfig | None = None) -> FastAPI:
    config = config or AppConfig.from_env()
    runtime = JarvisRuntime(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await runtime.initialize()
        app.state.runtime = runtime
        yield

    app = FastAPI(
        title="Jarvis Agent Inspector",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.runtime = runtime

    @app.get("/api/status")
    async def status() -> dict[str, Any]:
        return runtime.status()

    @app.get("/api/sessions")
    async def sessions() -> list[dict[str, Any]]:
        return runtime.store.list_sessions()

    @app.get("/api/events")
    async def events(after: int = 0, limit: int = Query(default=1000, le=5000)) -> list[dict]:
        return [
            event.model_dump(mode="json")
            for event in runtime.store.list_events(runtime.session_id, after=after, limit=limit)
        ]

    @app.post("/api/state")
    async def set_state(request: StateRequest) -> dict:
        return (await runtime.set_state(request.state, request.reason)).model_dump(mode="json")

    @app.post("/api/emergency-stop")
    async def emergency_stop() -> dict:
        return (await runtime.emergency_stop()).model_dump(mode="json")

    @app.post("/api/meetings/start")
    async def start_meeting(request: MeetingStartRequest) -> dict:
        return (await runtime.start_meeting(request.title)).model_dump(mode="json")

    @app.post("/api/meetings/end")
    async def end_meeting() -> dict:
        return (await runtime.end_meeting()).model_dump(mode="json")

    @app.post("/api/meetings/analyze")
    async def analyze_meeting() -> dict:
        return (await runtime.analyze_now()).model_dump(mode="json")

    @app.post("/api/transcript/inject")
    async def inject_transcript(request: TranscriptRequest) -> dict:
        return (
            await runtime.inject_transcript(
                request.text,
                speaker_hint=request.speaker_hint,
                overlap=request.overlap,
                auto_route=request.auto_route,
            )
        ).model_dump(mode="json")

    @app.post("/api/ask")
    async def ask(request: AskRequest) -> dict:
        return (await runtime.ask(request.text)).model_dump(mode="json")

    @app.get("/api/settings")
    async def get_settings() -> dict[str, Any]:
        return runtime.settings()

    @app.patch("/api/settings")
    async def patch_settings(request: SettingsRequest) -> dict[str, Any]:
        settings = runtime.update_settings(request.values)
        await runtime.emit(
            "settings.changed",
            {"keys": sorted(request.values)},
            source="settings_service",
        )
        return settings

    @app.get("/api/wake/samples")
    async def wake_samples() -> list[dict[str, Any]]:
        from dataclasses import asdict

        return [asdict(sample) for sample in runtime.wake_store.list()]

    @app.post("/api/wake/enroll")
    async def enroll_wake(request: WakeEnrollmentRequest) -> dict:
        try:
            result = await runtime.enroll_wake(request.label, request.phrase_type, request.frames)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return result.model_dump(mode="json")

    @app.delete("/api/wake/samples/{sample_id}")
    async def delete_wake_sample(sample_id: str) -> dict:
        return (await runtime.delete_wake_sample(sample_id)).model_dump(mode="json")

    @app.get("/api/providers")
    async def providers() -> list[dict[str, Any]]:
        return runtime.provider_manager.provider_summary()

    @app.post("/api/providers")
    async def save_provider(request: ProviderUpsertRequest) -> dict:
        runtime.provider_manager.save_provider(request.provider)
        await runtime.emit(
            "provider.config_changed",
            {
                "provider_id": request.provider.id,
                "provider_type": request.provider.provider_type,
                "secret_reference": request.provider.secret_reference,
            },
            source="provider_manager",
        )
        return request.provider.model_dump(mode="json")

    @app.post("/api/providers/assign")
    async def assign_model(request: AssignmentRequest) -> dict:
        if runtime.provider_manager.get_provider(request.assignment.provider_config_id) is None:
            raise HTTPException(status_code=404, detail="Provider not found")
        runtime.provider_manager.assign_model(request.assignment)
        await runtime.emit(
            "provider.model_assignment_changed",
            request.assignment.model_dump(mode="json"),
            source="provider_manager",
        )
        return request.assignment.model_dump(mode="json")

    @app.post("/api/providers/{provider_id}/diagnose")
    async def diagnose_provider(provider_id: str, request: DiagnosticRequest) -> dict:
        provider = runtime.provider_manager.get_provider(provider_id)
        if provider is None:
            raise HTTPException(status_code=404, detail="Provider not found")
        report = await runtime.provider_manager.diagnose(
            provider, role=request.role, model_id=request.model_id
        )
        await runtime.emit(
            "provider.diagnostic_completed",
            report.model_dump(mode="json"),
            source="provider_manager",
        )
        return report.model_dump(mode="json")

    @app.get("/api/connectors")
    async def connectors() -> list[dict[str, Any]]:
        return [runtime.excel_connector.health()]

    @app.get("/api/tools")
    async def tools() -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in runtime.tool_registry.list()]

    @app.get("/api/capabilities")
    async def capabilities() -> list[dict[str, Any]]:
        return runtime.status()["capabilities"]

    @app.put("/api/capabilities/{capability_id}/policy")
    async def set_policy(capability_id: str, request: PolicyRequest) -> dict:
        try:
            policy = await runtime.set_capability_policy(
                capability_id, request.mode, request.confidence_threshold
            )
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Capability not found") from exc
        return policy.model_dump(mode="json")

    @app.post("/api/capabilities/{capability_id}/execute")
    async def execute_capability(capability_id: str, request: CapabilityRequest) -> dict:
        result = await runtime.capability_engine.request(
            session_id=runtime.session_id,
            meeting_session_id=runtime.meeting.id if runtime.meeting else None,
            capability_id=capability_id,
            payload=request.payload,
            reason=request.reason,
        )
        return result.model_dump(mode="json")

    @app.post("/api/approvals/{approval_id}/approve")
    async def approve(approval_id: str, request: ApprovalRequestBody) -> dict:
        return (await runtime.capability_engine.approve(approval_id, request.token)).model_dump(
            mode="json"
        )

    @app.post("/api/approvals/{approval_id}/reject")
    async def reject(approval_id: str) -> dict:
        return (await runtime.capability_engine.reject(approval_id)).model_dump(mode="json")

    @app.post("/api/workbooks/rollback")
    async def rollback(payload: dict[str, str]) -> dict:
        result = runtime.excel_connector.rollback(payload["backup_path"], payload["target_path"])
        await runtime.emit(
            "artifact.rollback_completed",
            result.model_dump(mode="json"),
            source="excel_connector",
        )
        return result.model_dump(mode="json")

    @app.get("/api/workbooks/download")
    async def download_workbook(path: str) -> FileResponse:
        try:
            resolved = runtime.excel_connector.resolve_allowed(path)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        if not resolved.exists() or resolved.suffix.lower() != ".xlsx":
            raise HTTPException(status_code=404, detail="Workbook not found")
        return FileResponse(
            resolved,
            filename=resolved.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @app.websocket("/ws/events")
    async def event_socket(websocket: WebSocket, after: int = 0) -> None:
        await websocket.accept()
        try:
            async for event in runtime.store.subscribe(runtime.session_id, after=after):
                await websocket.send_json(event.model_dump(mode="json"))
        except WebSocketDisconnect:
            return

    @app.websocket("/ws/audio")
    async def audio_socket(websocket: WebSocket) -> None:
        await websocket.accept()
        sequence = 0
        try:
            while True:
                payload = await websocket.receive_json()
                if payload.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue
                raw_b64 = payload.get("pcm16_b64")
                if not isinstance(raw_b64, str):
                    await websocket.send_json({"ok": False, "error": "pcm16_b64 missing"})
                    continue
                # Validate base64 before it reaches the local ring buffer.
                try:
                    raw = base64.b64decode(raw_b64, validate=True)
                except ValueError:
                    await websocket.send_json({"ok": False, "error": "invalid base64"})
                    continue
                if len(raw) > 512_000:
                    await websocket.send_json({"ok": False, "error": "audio frame too large"})
                    continue
                sequence += 1
                frame = AudioFrame(
                    sequence=sequence,
                    timestamp_ms=int(payload.get("timestamp_ms", time.monotonic() * 1000)),
                    sample_rate=int(payload.get("sample_rate", 16000)),
                    channels=1,
                    pcm16_b64=raw_b64,
                    level=float(payload.get("level", 0.0)),
                )
                result = await runtime.ingest_audio(frame)
                await websocket.send_json(
                    {"ok": result.status.value in {"success", "cancelled"}, "status": result.status.value}
                )
        except WebSocketDisconnect:
            return

    static_dir = Path(__file__).parent / "static"
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return app


app = create_app()


def main() -> None:
    import uvicorn

    config = AppConfig.from_env()
    uvicorn.run("jarvis_agent.web.api:app", host=config.host, port=config.port, reload=False)


if __name__ == "__main__":
    main()
