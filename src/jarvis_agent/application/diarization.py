from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True, frozen=True)
class SpeakerAssignment:
    cluster_id: str
    display_label: str
    confidence: float
    overlap: bool = False


class SimpleOnlineDiarizer:
    """Transparent online feature clustering baseline for the prototype.

    Explicit speaker hints win. Otherwise a tiny online k-means over audio descriptors is used.
    This is useful for diagnostics and fixtures, not identity recognition.
    """

    def __init__(self, max_speakers: int = 4, new_cluster_distance: float = 0.35) -> None:
        self.max_speakers = max_speakers
        self.new_cluster_distance = new_cluster_distance
        self._centroids: list[np.ndarray] = []
        self._counts: list[int] = []
        self._hint_map: dict[str, int] = {}

    def assign(
        self,
        feature: np.ndarray | None = None,
        speaker_hint: str | None = None,
        overlap: bool = False,
    ) -> SpeakerAssignment:
        if speaker_hint:
            if speaker_hint not in self._hint_map:
                self._hint_map[speaker_hint] = len(self._hint_map)
            index = self._hint_map[speaker_hint]
            return self._assignment(index, 1.0, overlap)
        if feature is None or feature.size == 0:
            index = 0 if not self._centroids else min(len(self._centroids) - 1, 0)
            if not self._centroids:
                self._centroids.append(np.zeros(3, dtype=np.float32))
                self._counts.append(1)
            return self._assignment(index, 0.35, overlap)
        feature = np.asarray(feature, dtype=np.float32)
        if not self._centroids:
            self._centroids.append(feature.copy())
            self._counts.append(1)
            return self._assignment(0, 0.8, overlap)
        distances = [float(np.linalg.norm(feature - centroid)) for centroid in self._centroids]
        index = int(np.argmin(distances))
        distance = distances[index]
        if distance > self.new_cluster_distance and len(self._centroids) < self.max_speakers:
            self._centroids.append(feature.copy())
            self._counts.append(1)
            index = len(self._centroids) - 1
            distance = 0.0
        else:
            count = self._counts[index]
            self._centroids[index] = (self._centroids[index] * count + feature) / (count + 1)
            self._counts[index] = count + 1
        confidence = max(0.2, min(0.95, 1.0 - distance))
        return self._assignment(index, confidence, overlap)

    def merge(self, source_index: int, target_index: int) -> None:
        if source_index == target_index:
            return
        source = self._centroids[source_index]
        target = self._centroids[target_index]
        source_count = self._counts[source_index]
        target_count = self._counts[target_index]
        self._centroids[target_index] = (
            source * source_count + target * target_count
        ) / (source_count + target_count)
        self._counts[target_index] = source_count + target_count
        del self._centroids[source_index]
        del self._counts[source_index]

    @staticmethod
    def audio_feature(samples: np.ndarray) -> np.ndarray:
        if samples.size == 0:
            return np.zeros(3, dtype=np.float32)
        rms = float(np.sqrt(np.mean(samples**2)))
        zcr = float(np.mean(np.abs(np.diff(np.signbit(samples)))))
        spectrum = np.abs(np.fft.rfft(samples[: min(samples.size, 16000)]))
        centroid = float(np.sum(np.arange(spectrum.size) * spectrum) / max(np.sum(spectrum), 1e-6))
        centroid /= max(spectrum.size, 1)
        return np.asarray([rms * 5, zcr, centroid], dtype=np.float32)

    @staticmethod
    def _assignment(index: int, confidence: float, overlap: bool) -> SpeakerAssignment:
        return SpeakerAssignment(
            cluster_id=f"speaker_{index + 1}",
            display_label=f"Speaker {index + 1}",
            confidence=confidence,
            overlap=overlap,
        )
