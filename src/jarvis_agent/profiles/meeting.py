from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from jarvis_agent.domain.models import FactType, MeetingFact, TranscriptSegment


@dataclass(slots=True, frozen=True)
class AgentProfile:
    id: str
    version: str
    display_name: str
    instructions: str
    enabled_capabilities: tuple[str, ...]
    extraction_schema_version: str


MEETING_PROFILE = AgentProfile(
    id="meeting",
    version="1.0",
    display_name="Réunion",
    instructions=(
        "Transcrire silencieusement par défaut, extraire les décisions, actions, responsables, "
        "questions et risques. Ne jamais contourner la politique des capacités."
    ),
    enabled_capabilities=("update_roadmap",),
    extraction_schema_version="1.0",
)


class MeetingExtractor:
    """Deterministic baseline extractor; an analysis model adapter can replace/augment it."""

    DECISION_PATTERNS = (
        re.compile(r"\b(?:décision|decision)\s*[:\-]\s*(.+)", re.I),
        re.compile(r"\bon (?:décide|decide|valide)\s+(?:de\s+)?(.+)", re.I),
    )
    ACTION_PATTERNS = (
        re.compile(r"\baction\s*[:\-]\s*(.+)", re.I),
        re.compile(r"\b([\wÀ-ÿ' -]{2,40})\s+(?:doit|va devoir)\s+(.+)", re.I),
    )
    RISK_PATTERNS = (
        re.compile(r"\b(?:risque|blocage|bloquant)\s*[:\-]\s*(.+)", re.I),
    )

    def extract(self, segment: TranscriptSegment) -> list[MeetingFact]:
        if not segment.is_final:
            return []
        text = segment.text.strip()
        facts: list[MeetingFact] = []
        for pattern in self.DECISION_PATTERNS:
            if match := pattern.search(text):
                facts.append(self._fact(segment, FactType.DECISION, match.group(1).strip(), 0.82))
                break
        for pattern in self.ACTION_PATTERNS:
            if match := pattern.search(text):
                if len(match.groups()) == 2:
                    owner, description = match.group(1).strip(), match.group(2).strip()
                    fact = self._fact(segment, FactType.ACTION_ITEM, description, 0.78)
                    facts.append(
                        fact.model_copy(
                            update={
                                "description": description,
                                "owner_speaker_cluster_id": segment.speaker_cluster_id,
                                "status": "open",
                                "execution_status": "not_started",
                                "roadmap_row_ref": None,
                            }
                        )
                    )
                else:
                    description = match.group(1).strip()
                    facts.append(
                        self._fact(segment, FactType.ACTION_ITEM, description, 0.72).model_copy(
                            update={"description": description, "execution_status": "not_started"}
                        )
                    )
                break
        if text.endswith("?"):
            facts.append(self._fact(segment, FactType.QUESTION, text, 0.95))
        for pattern in self.RISK_PATTERNS:
            if match := pattern.search(text):
                facts.append(self._fact(segment, FactType.RISK, match.group(1).strip(), 0.8))
                break
        return facts

    def summarize(self, facts: Iterable[MeetingFact], transcript: Iterable[TranscriptSegment]) -> dict:
        fact_list = list(facts)
        segments = [segment for segment in transcript if segment.is_final]
        grouped: dict[str, list[str]] = {item.value: [] for item in FactType}
        for fact in fact_list:
            grouped[fact.fact_type.value].append(fact.text)
        return {
            "title": "Synthèse de réunion",
            "segment_count": len(segments),
            "speaker_count": len({s.speaker_cluster_id for s in segments if s.speaker_cluster_id}),
            "decisions": grouped[FactType.DECISION.value],
            "actions": grouped[FactType.ACTION_ITEM.value],
            "questions": grouped[FactType.QUESTION.value],
            "risks": grouped[FactType.RISK.value],
            "open_points": grouped[FactType.OPEN_POINT.value],
        }

    @staticmethod
    def _fact(
        segment: TranscriptSegment, fact_type: FactType, text: str, confidence: float
    ) -> MeetingFact:
        return MeetingFact(
            meeting_session_id=segment.meeting_session_id,
            fact_type=fact_type,
            text=text,
            source_segment_ids=(segment.id,),
            speaker_cluster_ids=(segment.speaker_cluster_id,) if segment.speaker_cluster_id else (),
            confidence=confidence,
        )
