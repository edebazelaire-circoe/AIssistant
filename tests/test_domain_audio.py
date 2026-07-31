from __future__ import annotations

import base64
from pathlib import Path

import numpy as np
import pytest

from jarvis_agent.application.audio import AudioRingBuffer
from jarvis_agent.application.wake import SpectralWakeDetector, WakeEnrollmentStore
from jarvis_agent.application.event_store import EventStore
from jarvis_agent.domain.models import AgentState, AudioFrame, RuntimeEvent
from jarvis_agent.domain.state_machine import AgentStateMachine, InvalidTransition


def make_frame(sequence: int, samples: np.ndarray, timestamp_ms: int | None = None) -> AudioFrame:
    raw = (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()
    return AudioFrame(
        sequence=sequence,
        timestamp_ms=timestamp_ms if timestamp_ms is not None else sequence * 100,
        sample_rate=16000,
        channels=1,
        pcm16_b64=base64.b64encode(raw).decode(),
        level=0.5,
    )


def test_state_machine_legal_transitions_and_hard_stop() -> None:
    machine = AgentStateMachine()
    machine.transition(AgentState.STANDBY, "test")
    machine.transition(AgentState.TRANSCRIBING, "wake")
    machine.transition(AgentState.INTERACTIVE, "wake")
    machine.transition(AgentState.MIC_OFF, "hard_stop")
    assert machine.state == AgentState.MIC_OFF


def test_state_machine_rejects_illegal_transition() -> None:
    machine = AgentStateMachine()
    with pytest.raises(InvalidTransition) as exc:
        machine.transition(AgentState.ERROR_RECOVERABLE, "skip")
    assert exc.value.diagnostic.code.value == "invalid_transition"


def test_ring_buffer_wraparound_preserves_order() -> None:
    buffer = AudioRingBuffer(capacity_ms=250)
    samples = np.zeros(1600, dtype=np.float32)  # 100 ms
    for index in range(5):
        buffer.append(make_frame(index, samples))
    snapshot = buffer.snapshot()
    assert [frame.sequence for frame in snapshot] == [3, 4]
    assert buffer.stats.dropped_frames == 3
    assert buffer.stats.duration_ms <= 250


def test_runtime_event_rejects_secret_fields() -> None:
    with pytest.raises(ValueError):
        RuntimeEvent(
            session_id="s",
            event_type="bad",
            source="test",
            payload={"api_key": "should-not-serialize"},
        )


def test_event_store_append_replay_and_settings(tmp_path: Path) -> None:
    import asyncio

    store = EventStore(tmp_path / "events.sqlite3")

    async def scenario() -> None:
        first = await store.append(
            RuntimeEvent(session_id="s1", event_type="one", source="test", payload={"x": 1})
        )
        second = await store.append(
            RuntimeEvent(session_id="s1", event_type="two", source="test", payload={"x": 2})
        )
        assert first.sequence == 1
        assert second.sequence == 2

    asyncio.run(scenario())
    replay = store.list_events("s1", after=1)
    assert [event.event_type for event in replay] == ["two"]
    store.set_setting("alpha", {"value": 3})
    assert store.get_setting("alpha") == {"value": 3}


def test_wake_enrollment_and_positive_detection(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "wake.sqlite3")
    enrollment = WakeEnrollmentStore(store.db_path)
    detector = SpectralWakeDetector(enrollment, threshold=0.98)
    t = np.arange(0, 1.0, 1 / 16000, dtype=np.float32)
    signal = 0.6 * np.sin(2 * np.pi * 440 * t) + 0.2 * np.sin(2 * np.pi * 660 * t)
    frames = [make_frame(1, signal)]
    sample = enrollment.add("hey jarvis", "activation", frames)
    assert sample.duration_ms == 1000
    detected = detector.detect(frames, "activation")
    assert detected.detected
    assert detected.score > 0.99
    negative = 0.6 * np.sin(2 * np.pi * 1200 * t)
    other = detector.detect([make_frame(2, negative)], "activation")
    assert other.score < detected.score
    assert enrollment.delete(sample.id)
