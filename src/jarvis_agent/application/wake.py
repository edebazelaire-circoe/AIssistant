from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np

from jarvis_agent.application.audio import decode_pcm16
from jarvis_agent.domain.models import AudioFrame


@dataclass(slots=True, frozen=True)
class WakeSample:
    id: str
    label: str
    phrase_type: str
    created_at: str
    duration_ms: int
    false_wake: bool


@dataclass(slots=True, frozen=True)
class WakeDetection:
    phrase_type: str
    score: float
    detected: bool


def _resample_linear(samples: np.ndarray, source_rate: int, target_rate: int = 16000) -> np.ndarray:
    if source_rate == target_rate or samples.size == 0:
        return samples
    duration = samples.size / source_rate
    target_size = max(1, round(duration * target_rate))
    old_x = np.linspace(0.0, 1.0, samples.size, endpoint=False)
    new_x = np.linspace(0.0, 1.0, target_size, endpoint=False)
    return np.interp(new_x, old_x, samples).astype(np.float32)


def spectral_feature(samples: np.ndarray, sample_rate: int = 16000, bins: int = 64) -> np.ndarray:
    """Small local baseline. It is intentionally replaceable, not production wake recognition."""
    if samples.size < 320:
        return np.zeros(bins + 4, dtype=np.float32)
    samples = samples - float(np.mean(samples))
    peak = float(np.max(np.abs(samples)))
    if peak > 1e-6:
        samples = samples / peak
    target_len = 16000
    if samples.size < target_len:
        samples = np.pad(samples, (0, target_len - samples.size))
    elif samples.size > target_len:
        indices = np.linspace(0, samples.size - 1, target_len).astype(int)
        samples = samples[indices]
    window = np.hanning(samples.size)
    spectrum = np.abs(np.fft.rfft(samples * window))
    spectrum = np.log1p(spectrum)
    edges = np.linspace(0, spectrum.size, bins + 1, dtype=int)
    pooled = np.array(
        [float(np.mean(spectrum[edges[i] : max(edges[i + 1], edges[i] + 1)])) for i in range(bins)],
        dtype=np.float32,
    )
    zcr = float(np.mean(np.abs(np.diff(np.signbit(samples)))))
    rms = float(np.sqrt(np.mean(samples**2)))
    centroid = float(np.sum(np.arange(spectrum.size) * spectrum) / max(np.sum(spectrum), 1e-6))
    centroid /= max(spectrum.size, 1)
    spread = float(np.std(spectrum) / max(float(np.mean(spectrum)), 1e-6))
    feature = np.concatenate([pooled, np.array([zcr, rms, centroid, spread], dtype=np.float32)])
    norm = float(np.linalg.norm(feature))
    return feature / norm if norm > 1e-6 else feature


class WakeEnrollmentStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def add(self, label: str, phrase_type: str, frames: list[AudioFrame]) -> WakeSample:
        if phrase_type not in {"activation", "deactivation"}:
            raise ValueError("phrase_type must be activation or deactivation")
        if not frames:
            raise ValueError("At least one audio frame is required")
        samples = decode_pcm16(frames)
        source_rate = frames[0].sample_rate
        samples = _resample_linear(samples, source_rate)
        feature = spectral_feature(samples)
        duration_ms = round(samples.size / 16000 * 1000)
        if duration_ms < 250:
            raise ValueError("Enrollment sample is too short")
        sample_id = f"wake_{uuid4().hex}"
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as con:
            con.execute(
                """
                INSERT INTO wake_samples(id, label, phrase_type, created_at, feature_json, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (sample_id, label, phrase_type, created_at, json.dumps(feature.tolist()), duration_ms),
            )
        return WakeSample(sample_id, label, phrase_type, created_at, duration_ms, False)

    def list(self) -> list[WakeSample]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT id, label, phrase_type, created_at, duration_ms, false_wake FROM wake_samples ORDER BY created_at"
            ).fetchall()
        return [
            WakeSample(
                id=row["id"],
                label=row["label"],
                phrase_type=row["phrase_type"],
                created_at=row["created_at"],
                duration_ms=row["duration_ms"],
                false_wake=bool(row["false_wake"]),
            )
            for row in rows
        ]

    def features(self, phrase_type: str) -> list[np.ndarray]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT feature_json FROM wake_samples WHERE phrase_type = ? AND false_wake = 0",
                (phrase_type,),
            ).fetchall()
        return [np.asarray(json.loads(row["feature_json"]), dtype=np.float32) for row in rows]

    def delete(self, sample_id: str) -> bool:
        with self._connect() as con:
            cursor = con.execute("DELETE FROM wake_samples WHERE id = ?", (sample_id,))
        return cursor.rowcount > 0

    def mark_false_wake(self, sample_id: str) -> bool:
        with self._connect() as con:
            cursor = con.execute("UPDATE wake_samples SET false_wake = 1 WHERE id = ?", (sample_id,))
        return cursor.rowcount > 0


class SpectralWakeDetector:
    def __init__(self, store: WakeEnrollmentStore, threshold: float = 0.89) -> None:
        self.store = store
        self.threshold = threshold

    def detect(self, frames: list[AudioFrame], phrase_type: str = "activation") -> WakeDetection:
        enrolled = self.store.features(phrase_type)
        if not enrolled or not frames:
            return WakeDetection(phrase_type=phrase_type, score=0.0, detected=False)
        samples = _resample_linear(decode_pcm16(frames), frames[0].sample_rate)
        feature = spectral_feature(samples)
        scores = [float(np.dot(feature, known)) for known in enrolled if known.shape == feature.shape]
        score = max(scores, default=0.0)
        return WakeDetection(phrase_type=phrase_type, score=score, detected=score >= self.threshold)
