from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from jarvis_agent.application.event_store import EventStore
from jarvis_agent.application.providers import ProviderManager
from jarvis_agent.application.tools import ToolRegistry, ToolRunner
from jarvis_agent.domain.models import ProviderConfig, ResultStatus, ToolDefinition, ToolResult


def test_fake_provider_diagnostic_matrix(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "provider.sqlite3")
    manager = ProviderManager(store)
    config = ProviderConfig(
        id="fake",
        provider_type="fake",
        display_name="Fake",
        secret_reference="NOT_NEEDED",
    )
    manager.save_provider(config)
    report = asyncio.run(manager.diagnose(config, model_id="fake-model"))
    assert all(stage.ok for stage in report.stages)
    store.set_setting("fake_provider_scenario:fake", "authentication_failed")
    report = asyncio.run(manager.diagnose(config, model_id="fake-model"))
    assert report.stages[1].code == "authentication_failed"
    assert not report.stages[-1].ok


def test_tool_registry_rejects_duplicate_version() -> None:
    registry = ToolRegistry()
    definition = ToolDefinition(
        id="fake.echo",
        description="Echo",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        mutates_external_state=False,
        connector_id="fake",
        permission_scope="read",
    )
    registry.register(definition, lambda args: ToolResult(status="success", summary="ok", data=args))
    with pytest.raises(ValueError):
        registry.register(definition, lambda args: ToolResult(status="success", summary="ok"))


def test_tool_runner_emits_redacted_lifecycle(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "tools.sqlite3")
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            id="fake.echo",
            description="Echo",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            mutates_external_state=False,
            connector_id="fake",
            permission_scope="read",
            redacted_fields=("credential",),
        ),
        lambda args: ToolResult(status=ResultStatus.SUCCESS, summary="ok", data={"seen": True}),
    )
    runner = ToolRunner(registry, store)
    result = asyncio.run(
        runner.invoke(
            session_id="s",
            meeting_session_id=None,
            plan_id="p",
            tool_id="fake.echo",
            arguments={"credential": "secret-value", "visible": 1},
        )
    )
    assert result.status == ResultStatus.SUCCESS
    events = store.list_events("s")
    assert [event.event_type for event in events] == ["tool.started", "tool.completed"]
    assert events[0].payload["arguments"]["credential"] == "***REDACTED***"
    assert "secret-value" not in events[0].model_dump_json()
