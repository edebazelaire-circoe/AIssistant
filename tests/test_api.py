from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from jarvis_agent.application.config import AppConfig
from jarvis_agent.web.api import create_app


def test_api_and_static_inspector_smoke(tmp_path: Path) -> None:
    app = create_app(AppConfig(tmp_path / "data", tmp_path / "workspace", "127.0.0.1", 0))
    with TestClient(app) as client:
        root = client.get("/")
        assert root.status_code == 200
        assert "Agent Inspector" in root.text
        status = client.get("/api/status")
        assert status.status_code == 200
        assert status.json()["state"] == "MIC_OFF"
        transition = client.post("/api/state", json={"state": "STANDBY", "reason": "test"})
        assert transition.json()["status"] == "success"
        meeting = client.post("/api/meetings/start", json={"title": "API test"})
        assert meeting.json()["status"] == "success"
        injected = client.post(
            "/api/transcript/inject",
            json={"text": "Décision : tester l'API.", "speaker_hint": "Alice", "auto_route": False},
        )
        assert injected.json()["status"] == "success"
        events = client.get("/api/events?after=0").json()
        assert any(event["event_type"] == "transcript.final" for event in events)
