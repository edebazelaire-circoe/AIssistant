from __future__ import annotations

import base64
import math
from collections import deque
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from jarvis_agent.domain.models import AudioFrame


@dataclass(slots=True)
class BufferStats:
    frame_count: int
    duration_ms: int
    capacity_ms: int
    dropped_frames: int


class AudioRingBuffer:
    """Bounded PCM16 frame buffer independent from speech providers."""

    def __init__(self, capacity_ms: int = 5000) -> None:
        if capacity_ms <= 0:
            raise ValueError("capacity_ms must be positive")
        self.capacity_ms = capacity_ms
        self._frames: deque[AudioFrame] = deque()
        self._duration_ms = 0
        self._dropped_frames = 0

    @staticmethod
    def frame_duration_ms(frame: AudioFrame) -> int:
        byte_count = len(base64.b64decode(frame.pcm16_b64))
        samples = byte_count // 2 // max(frame.channels, 1)
        return max(1, round(samples / frame.sample_rate * 1000))

    def append(self, frame: AudioFrame) -> None:
        duration = self.frame_duration_ms(frame)
        self._frames.append(frame)
        self._duration_ms += duration
        while self._duration_ms > self.capacity_ms and self._frames:
            removed = self._frames.popleft()
            self._duration_ms -= self.frame_duration_ms(removed)
            self._dropped_frames += 1

    def clear(self) -> None:
        self._frames.clear()
        self._duration_ms = 0

    def snapshot(self, last_ms: int | None = None) -> list[AudioFrame]:
        if last_ms is None or last_ms >= self._duration_ms:
            return list(self._frames)
        selected: deque[AudioFrame] = deque()
        total = 0
        for frame in reversed(self._frames):
            selected.appendleft(frame)
            total += self.frame_duration_ms(frame)
            if total >= last_ms:
                break
        return list(selected)

    @property
    def stats(self) -> BufferStats:
        return BufferStats(
            frame_count=len(self._frames),
            duration_ms=max(0, self._duration_ms),
            capacity_ms=self.capacity_ms,
            dropped_frames=self._dropped_frames,
        )


def decode_pcm16(frames: Iterable[AudioFrame]) -> np.ndarray:
    chunks: list[np.ndarray] = []
    for frame in frames:
        raw = base64.b64decode(frame.pcm16_b64)
        chunks.append(np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0)
    if not chunks:
        return np.empty(0, dtype=np.float32)
    return np.concatenate(chunks)


def calculate_level(pcm: np.ndarray) -> float:
    if pcm.size == 0:
        return 0.0
    rms = float(np.sqrt(np.mean(np.square(pcm))))
    if rms <= 1e-7:
        return 0.0
    db = 20.0 * math.log10(rms)
    return max(0.0, min(1.0, (db + 60.0) / 60.0))
