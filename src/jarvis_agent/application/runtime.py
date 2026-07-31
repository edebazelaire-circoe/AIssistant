from __future__ import annotations

import asyncio
import base64
import re
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jarvis_agent.adapters.transcription import FixtureSpeechAdapter
from jarvis_agent.application.audio import AudioRingBuffer, decode_pcm16
from jarvis_agent.application.capabilities import (
    CapabilityEngine,
    CapabilityRegistry,
    UpdateRoadmapWorkflow,
    register_excel_tools,
    register_update_roadmap_capability,
)
from jarvis_agent.application.config import AppConfig
from jarvis_agent.application.diarization import SimpleOnlineDiarizer
from jarvis_agent.application.event_store import EventStore
from jarvis_agent.application.providers import ProviderManager
from jarvis_agent.application.tools import ToolRegistry, ToolRunner
from jarvis_agent.application.wake import SpectralWakeDetector, WakeEnrollmentStore
from jarvis_agent.connectors.excel_roadmap import ExcelRoadmapConnector
from jarvis_agent.domain.models import (
    AgentSession,
    AgentState,
    AudioFrame,
    CapabilityPolicy,
    CommandResult,
    MeetingFact,
    MeetingSession,
    PolicyMode,
    ResultStatus,
    RoadmapStatus,
    RuntimeEvent,
    TranscriptSegment,
    new_id,
)
from jarvis_agent.domain.state_machine import AgentStateMachine, InvalidTransition
from jarvis_agent.profiles.meeting import MEETING_PROFILE, MeetingExtractor


class JarvisRuntime:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.store = EventStore(config.data_dir / "jarvis.sqlite3")
        saved_session_id = self.store.get_setting("active_agent_session_id")
        self.session_id = saved_session_id or new_id("agent")
        self.store.set_setting("active_agent_session_id", self.session_id)
        saved_state = self.store.get_setting("agent_state", AgentState.MIC_OFF.value)
        self.state_machine = AgentStateMachine(AgentState(saved_state))
        self.agent_session = AgentSession(
            id=self.session_id,
            current_state=self.state_machine.state,
            previous_safe_state=self.state_machine.previous_safe_state,
        )
        self.audio_buffer = AudioRingBuffer(
            capacity_ms=int(self.store.get_setting("audio.buffer_ms", 5000))
        )
        self.wake_store = WakeEnrollmentStore(self.store.db_path)
        self.wake_detector = SpectralWakeDetector(
            self.wake_store, threshold=float(self.store.get_setting("wake.threshold", 0.89))
        )
        self.diarizer = SimpleOnlineDiarizer()
        self.fixture_speech = FixtureSpeechAdapter()
        self.provider_manager = ProviderManager(self.store)
        self.excel_connector = ExcelRoadmapConnector(
            Path(self.store.get_setting("connector.excel.allowed_root", str(config.allowed_root)))
        )
        self.tool_registry = ToolRegistry()
        register_excel_tools(self.tool_registry, self.excel_connector)
        self.tool_runner = ToolRunner(self.tool_registry, self.store)
        self.capability_registry = CapabilityRegistry()
        roadmap_workflow = UpdateRoadmapWorkflow(self.excel_connector, self.tool_runner)
        register_update_roadmap_capability(self.capability_registry, roadmap_workflow)
        self.capability_engine = CapabilityEngine(self.capability_registry, self.store)
        self.meeting_extractor = MeetingExtractor()
        self.meeting: MeetingSession | None = None
        self.transcript: list[TranscriptSegment] = []
        self.facts: list[MeetingFact] = []
        self._last_wake_check_ms = 0
        self._wake_cooldown_until = 0.0
        self._rebuild_projection()

    async def initialize(self) -> None:
        if self.store.latest_sequence(self.session_id) == 0:
            await self.emit(
                "agent.session_started",
                {
                    "session": self.agent_session.model_dump(mode="json"),
                    "stack": "python-fastapi-browser",
                    "profile_available": asdict(MEETING_PROFILE),
                },
                source="runtime",
            )
        if not self.store.list_settings("provider:"):
            from jarvis_agent.domain.models import ProviderConfig

            self.provider_manager.save_provider(
                ProviderConfig(
                    id="provider_fake",
                    provider_type="fake",
                    display_name="Fournisseur de démonstration",
                    secret_reference="JARVIS_FAKE_PROVIDER_SECRET",
                    enabled=True,
                )
            )
            self.provider_manager.save_provider(
                ProviderConfig(
                    id="provider_openai",
                    provider_type="openai",
                    display_name="OpenAI",
                    secret_reference="OPENAI_API_KEY",
                    base_url="https://api.openai.com/v1",
                    enabled=True,
                )
            )

    async def emit(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        source: str,
        correlation_id: str | None = None,
        meeting_session_id: str | None = None,
    ) -> RuntimeEvent:
        return await self.store.append(
            RuntimeEvent(
                session_id=self.session_id,
                meeting_session_id=meeting_session_id
                if meeting_session_id is not None
                else (self.meeting.id if self.meeting else None),
                event_type=event_type,
                correlation_id=correlation_id or new_id("corr"),
                source=source,
                payload=payload,
            )
        )

    async def set_state(self, requested: AgentState, reason: str = "ui_command") -> CommandResult:
        try:
            transition = self.state_machine.transition(requested, reason)
        except InvalidTransition as exc:
            await self.emit(
                "agent.state_transition_rejected",
                {"diagnostic": exc.diagnostic.model_dump(mode="json")},
                source="state_machine",
            )
            return CommandResult(
                status=ResultStatus.FAILURE,
                summary=str(exc),
                diagnostics=(exc.diagnostic,),
            )
        if requested == AgentState.MIC_OFF:
            self.audio_buffer.clear()
        self.store.set_setting("agent_state", requested.value)
        self.agent_session = self.agent_session.model_copy(
            update={
                "current_state": requested,
                "previous_safe_state": self.state_machine.previous_safe_state,
            }
        )
        await self.emit(
            "agent.state_changed",
            {
                "previous": transition.previous.value,
                "current": transition.current.value,
                "reason": reason,
                "mic_capturing": requested != AgentState.MIC_OFF,
                "remote_processing_allowed": requested
                in {AgentState.TRANSCRIBING, AgentState.INTERACTIVE},
            },
            source="state_machine",
        )
        return CommandResult(
            status=ResultStatus.SUCCESS,
            summary=f"State changed to {requested.value}",
            data={"state": requested.value},
        )

    async def emergency_stop(self) -> CommandResult:
        return await self.set_state(AgentState.MIC_OFF, reason="emergency_stop")

    async def start_meeting(self, title: str | None = None) -> CommandResult:
        if self.meeting and self.meeting.status == "active":
            return CommandResult(
                status=ResultStatus.SUCCESS,
                summary="Meeting is already active",
                data={"meeting": self.meeting.model_dump(mode="json")},
            )
        self.meeting = MeetingSession(title=title)
        self.transcript = []
        self.facts = []
        self.agent_session = self.agent_session.model_copy(
            update={"meeting_session_id": self.meeting.id, "active_profile_id": MEETING_PROFILE.id}
        )
        await self.emit(
            "meeting.started",
            {
                "meeting": self.meeting.model_dump(mode="json"),
                "profile": {
                    "id": MEETING_PROFILE.id,
                    "version": MEETING_PROFILE.version,
                    "display_name": MEETING_PROFILE.display_name,
                    "instructions": MEETING_PROFILE.instructions,
                    "enabled_capabilities": list(MEETING_PROFILE.enabled_capabilities),
                    "extraction_schema_version": MEETING_PROFILE.extraction_schema_version,
                },
            },
            source="meeting_service",
            meeting_session_id=self.meeting.id,
        )
        if self.state_machine.state == AgentState.STANDBY:
            await self.set_state(AgentState.TRANSCRIBING, reason="meeting_started")
        return CommandResult(
            status=ResultStatus.SUCCESS,
            summary="Meeting started",
            data={"meeting": self.meeting.model_dump(mode="json")},
        )

    async def end_meeting(self) -> CommandResult:
        if not self.meeting:
            return CommandResult(status=ResultStatus.FAILURE, summary="No active meeting")
        summary = self.meeting_extractor.summarize(self.facts, self.transcript)
        ended = self.meeting.model_copy(
            update={"ended_at": datetime.now(UTC), "status": "ended", "summary_status": "completed"}
        )
        await self.emit(
            "meeting.summary_created",
            {"summary": summary},
            source="meeting_profile",
            meeting_session_id=self.meeting.id,
        )
        await self.emit(
            "meeting.ended",
            {"meeting": ended.model_dump(mode="json")},
            source="meeting_service",
            meeting_session_id=self.meeting.id,
        )
        self.meeting = ended
        if self.state_machine.state in {AgentState.TRANSCRIBING, AgentState.INTERACTIVE}:
            await self.set_state(AgentState.STANDBY, reason="meeting_ended")
        return CommandResult(
            status=ResultStatus.SUCCESS,
            summary="Meeting ended",
            data={"summary": summary, "meeting": ended.model_dump(mode="json")},
        )

    async def ingest_audio(self, frame: AudioFrame) -> CommandResult:
        if self.state_machine.state == AgentState.MIC_OFF:
            return CommandResult(status=ResultStatus.CANCELLED, summary="Microphone is hard off")
        self.audio_buffer.append(frame)
        stats = self.audio_buffer.stats
        await self.emit(
            "audio.level",
            {
                "level": frame.level,
                "sample_rate": frame.sample_rate,
                "sequence": frame.sequence,
                "buffer_duration_ms": stats.duration_ms,
                "buffer_capacity_ms": stats.capacity_ms,
                "dropped_frames": stats.dropped_frames,
                "local_only": self.state_machine.state == AgentState.STANDBY,
            },
            source="audio_capture",
        )
        now_ms = frame.timestamp_ms
        if (
            time.monotonic() >= self._wake_cooldown_until
            and stats.duration_ms >= 900
            and now_ms - self._last_wake_check_ms >= 400
        ):
            self._last_wake_check_ms = now_ms
            phrase_type = (
                "deactivation"
                if self.state_machine.state == AgentState.INTERACTIVE
                else "activation"
            )
            detection = self.wake_detector.detect(
                self.audio_buffer.snapshot(last_ms=1400), phrase_type=phrase_type
            )
            await self.emit(
                "wake.score",
                {
                    "phrase_type": phrase_type,
                    "score": detection.score,
                    "threshold": self.wake_detector.threshold,
                    "detected": detection.detected,
                },
                source="wake_detector",
            )
            if detection.detected:
                self._wake_cooldown_until = time.monotonic() + 2.0
                await self.emit(
                    "wake.detected",
                    {"phrase_type": phrase_type, "score": detection.score},
                    source="wake_detector",
                )
                if phrase_type == "activation":
                    await self.set_state(AgentState.INTERACTIVE, reason="wake_activation")
                else:
                    await self.set_state(AgentState.STANDBY, reason="wake_deactivation")
        return CommandResult(status=ResultStatus.SUCCESS, summary="Audio frame accepted")

    async def enroll_wake(
        self,
        label: str,
        phrase_type: str,
        frames_payload: list[dict[str, Any]],
    ) -> CommandResult:
        frames = [AudioFrame.model_validate(item) for item in frames_payload]
        sample = self.wake_store.add(label, phrase_type, frames)
        await self.emit(
            "wake.enrollment_added",
            {"sample": asdict(sample)},
            source="wake_enrollment",
        )
        return CommandResult(
            status=ResultStatus.SUCCESS,
            summary="Wake sample stored locally",
            data={"sample": asdict(sample)},
        )

    async def delete_wake_sample(self, sample_id: str) -> CommandResult:
        deleted = self.wake_store.delete(sample_id)
        if deleted:
            await self.emit(
                "wake.enrollment_deleted", {"sample_id": sample_id}, source="wake_enrollment"
            )
        return CommandResult(
            status=ResultStatus.SUCCESS if deleted else ResultStatus.FAILURE,
            summary="Sample deleted" if deleted else "Sample not found",
        )

    async def inject_transcript(
        self,
        text: str,
        speaker_hint: str | None = None,
        overlap: bool = False,
        auto_route: bool = True,
    ) -> CommandResult:
        if not self.meeting or self.meeting.status != "active":
            await self.start_meeting("Réunion de démonstration")
        assert self.meeting is not None
        start_ms = self.transcript[-1].end_ms + 50 if self.transcript else 0
        revision_id: str | None = None
        final_segment: TranscriptSegment | None = None
        async for chunk in self.fixture_speech.transcribe_text(text, start_ms=start_ms):
            assignment = self.diarizer.assign(speaker_hint=speaker_hint, overlap=overlap)
            segment = TranscriptSegment(
                meeting_session_id=self.meeting.id,
                start_ms=chunk.start_ms,
                end_ms=chunk.end_ms,
                text=chunk.text,
                is_final=chunk.is_final,
                speaker_cluster_id=assignment.cluster_id,
                confidence=chunk.confidence,
                source_adapter=self.fixture_speech.id,
                revision_of=revision_id if chunk.is_final else None,
            )
            if not chunk.is_final:
                revision_id = segment.id
            else:
                final_segment = segment
                self.transcript.append(segment)
            await self.emit(
                "transcript.final" if chunk.is_final else "transcript.partial",
                {
                    "segment": segment.model_dump(mode="json"),
                    "speaker": {
                        "cluster_id": assignment.cluster_id,
                        "display_label": assignment.display_label,
                        "confidence": assignment.confidence,
                        "overlap": assignment.overlap,
                    },
                },
                source="transcription_service",
                meeting_session_id=self.meeting.id,
            )
        if final_segment is None:
            return CommandResult(status=ResultStatus.FAILURE, summary="No transcript produced")
        extracted = self.meeting_extractor.extract(final_segment)
        for fact in extracted:
            self.facts.append(fact)
            await self.emit(
                "meeting.fact_extracted",
                {"fact": fact.model_dump(mode="json")},
                source="meeting_profile",
                meeting_session_id=self.meeting.id,
            )
        phrase = str(self.store.get_setting("wake.activation_phrase", "hey jarvis")).lower()
        deactivation = str(self.store.get_setting("wake.deactivation_phrase", "merci jarvis")).lower()
        lowered = text.lower()
        if phrase and phrase in lowered and self.state_machine.state == AgentState.STANDBY:
            await self.set_state(AgentState.INTERACTIVE, reason="text_fixture_wake")
        if deactivation and deactivation in lowered and self.state_machine.state == AgentState.INTERACTIVE:
            await self.set_state(AgentState.STANDBY, reason="text_fixture_deactivation")
        routed: CommandResult | None = None
        if auto_route:
            parsed = parse_roadmap_update(text)
            if parsed:
                routed = await self.capability_engine.request(
                    session_id=self.session_id,
                    meeting_session_id=self.meeting.id,
                    capability_id="update_roadmap",
                    payload=parsed,
                    reason=f"Detected a roadmap status statement in segment {final_segment.id}",
                )
        return CommandResult(
            status=ResultStatus.SUCCESS,
            summary="Transcript injected",
            data={
                "segment": final_segment.model_dump(mode="json"),
                "facts": [fact.model_dump(mode="json") for fact in extracted],
                "routed_result": routed.model_dump(mode="json") if routed else None,
            },
        )

    async def ask(self, text: str) -> CommandResult:
        parsed = parse_roadmap_update(text)
        if parsed:
            result = await self.capability_engine.request(
                session_id=self.session_id,
                meeting_session_id=self.meeting.id if self.meeting else None,
                capability_id="update_roadmap",
                payload=parsed,
                reason=f"Explicit user request: {text}",
            )
            await self.emit(
                "assistant.message",
                {"text": result.summary, "kind": "capability_result"},
                source="agent_orchestrator",
            )
            return result
        answer = self._answer_from_context(text)
        await self.emit(
            "assistant.message",
            {"text": answer, "kind": "read_only_answer"},
            source="agent_orchestrator",
        )
        return CommandResult(status=ResultStatus.SUCCESS, summary=answer, data={"answer": answer})

    async def analyze_now(self) -> CommandResult:
        summary = self.meeting_extractor.summarize(self.facts, self.transcript)
        await self.emit(
            "meeting.analysis_completed",
            {"summary": summary},
            source="meeting_profile",
        )
        return CommandResult(status=ResultStatus.SUCCESS, summary="Analysis completed", data=summary)

    async def set_capability_policy(
        self, capability_id: str, mode: PolicyMode, confidence_threshold: float | None = None
    ) -> CapabilityPolicy:
        policy = CapabilityPolicy(
            capability_id=capability_id,
            mode=mode,
            confidence_threshold=confidence_threshold,
        )
        return await self.capability_engine.set_policy(policy, self.session_id)

    def update_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        allowed_keys = {
            "wake.activation_phrase",
            "wake.deactivation_phrase",
            "wake.threshold",
            "audio.buffer_ms",
            "connector.excel.allowed_root",
            "prompt.realtime",
            "prompt.transcription",
            "prompt.analysis",
            "prompt.classification",
            "meeting.auto_analyze",
        }
        for key, value in values.items():
            if key not in allowed_keys:
                continue
            self.store.set_setting(key, value)
            if key == "wake.threshold":
                self.wake_detector.threshold = float(value)
            elif key == "audio.buffer_ms":
                self.audio_buffer = AudioRingBuffer(int(value))
            elif key == "connector.excel.allowed_root":
                self.excel_connector.allowed_root = Path(value).expanduser().resolve()
                self.excel_connector.allowed_root.mkdir(parents=True, exist_ok=True)
        return self.settings()

    def settings(self) -> dict[str, Any]:
        return {
            "wake.activation_phrase": self.store.get_setting(
                "wake.activation_phrase", "hey jarvis"
            ),
            "wake.deactivation_phrase": self.store.get_setting(
                "wake.deactivation_phrase", "merci jarvis"
            ),
            "wake.threshold": self.wake_detector.threshold,
            "audio.buffer_ms": self.audio_buffer.capacity_ms,
            "connector.excel.allowed_root": str(self.excel_connector.allowed_root),
            "prompt.realtime": self.store.get_setting(
                "prompt.realtime",
                "Tu es Jarvis, un assistant de réunion concis. Signale clairement ce que tu fais.",
            ),
            "prompt.transcription": self.store.get_setting(
                "prompt.transcription",
                "Transcris fidèlement en français et conserve les noms propres.",
            ),
            "prompt.analysis": self.store.get_setting(
                "prompt.analysis",
                "Extrais les décisions, actions, responsables, échéances, risques et points ouverts.",
            ),
            "prompt.classification": self.store.get_setting(
                "prompt.classification",
                "Classe les intentions sans déclencher d'action irréversible sans validation.",
            ),
            "meeting.auto_analyze": bool(
                self.store.get_setting("meeting.auto_analyze", False)
            ),
        }

    def status(self) -> dict[str, Any]:
        stats = self.audio_buffer.stats
        return {
            "session_id": self.session_id,
            "state": self.state_machine.state.value,
            "meeting": self.meeting.model_dump(mode="json") if self.meeting else None,
            "active_profile": MEETING_PROFILE.id if self.meeting and self.meeting.status == "active" else None,
            "audio": {
                "buffer_duration_ms": stats.duration_ms,
                "buffer_capacity_ms": stats.capacity_ms,
                "dropped_frames": stats.dropped_frames,
                "local_only": self.state_machine.state == AgentState.STANDBY,
            },
            "wake_samples": [asdict(sample) for sample in self.wake_store.list()],
            "settings": self.settings(),
            "providers": self.provider_manager.provider_summary(),
            "connectors": [self.excel_connector.health()],
            "tools": [item.model_dump(mode="json") for item in self.tool_registry.list()],
            "capabilities": [
                {
                    **item.model_dump(mode="json"),
                    "policy": self.capability_engine.get_policy(item.id).model_dump(mode="json"),
                }
                for item in self.capability_registry.list()
            ],
            "event_cursor": self.store.latest_sequence(self.session_id),
            "transcript_count": len(self.transcript),
            "fact_count": len(self.facts),
        }

    def _answer_from_context(self, question: str) -> str:
        lowered = question.lower()
        if "décision" in lowered or "decision" in lowered:
            decisions = [fact.text for fact in self.facts if fact.fact_type.value == "decision"]
            return "Décisions : " + ("; ".join(decisions) if decisions else "aucune détectée.")
        if "action" in lowered:
            actions = [fact.text for fact in self.facts if fact.fact_type.value == "action_item"]
            return "Actions : " + ("; ".join(actions) if actions else "aucune détectée.")
        if "résum" in lowered or "summa" in lowered:
            summary = self.meeting_extractor.summarize(self.facts, self.transcript)
            return (
                f"{summary['segment_count']} segments, {len(summary['decisions'])} décisions, "
                f"{len(summary['actions'])} actions et {len(summary['risks'])} risques détectés."
            )
        recent = " ".join(segment.text for segment in self.transcript[-4:])
        return (
            "Je n’ai pas de modèle d’analyse distant configuré dans ce mode local. "
            + (f"Contexte récent : {recent}" if recent else "Aucun contexte de réunion n’est disponible.")
        )

    def _rebuild_projection(self) -> None:
        events = self.store.list_events(self.session_id, after=0, limit=10000)
        for event in events:
            if event.event_type == "meeting.started":
                self.meeting = MeetingSession.model_validate(event.payload["meeting"])
                self.transcript = []
                self.facts = []
            elif event.event_type == "meeting.ended" and self.meeting:
                self.meeting = MeetingSession.model_validate(event.payload["meeting"])
            elif event.event_type == "transcript.final":
                self.transcript.append(TranscriptSegment.model_validate(event.payload["segment"]))
            elif event.event_type == "meeting.fact_extracted":
                self.facts.append(MeetingFact.model_validate(event.payload["fact"]))


def parse_roadmap_update(text: str) -> dict[str, Any] | None:
    lowered = text.lower().strip()
    status_patterns: list[tuple[re.Pattern[str], RoadmapStatus]] = [
        (re.compile(r"\b(?:termin[ée]e?|fait|done|completed?)\b", re.I), RoadmapStatus.DONE),
        (re.compile(r"\b(?:en cours|in progress|doing)\b", re.I), RoadmapStatus.IN_PROGRESS),
        (re.compile(r"\b(?:à faire|a faire|non fait|not done|todo)\b", re.I), RoadmapStatus.NOT_DONE),
    ]
    desired_status: RoadmapStatus | None = None
    status_match: re.Match[str] | None = None
    for pattern, status in status_patterns:
        match = pattern.search(lowered)
        if match:
            desired_status = status
            status_match = match
            break
    if desired_status is None or status_match is None:
        return None
    patterns = [
        re.compile(
            r"(?:l['’]action|la t[âa]che|action|t[âa]che)\s+(.+?)\s+(?:est|passe|devient|comme|au statut)\s+",
            re.I,
        ),
        re.compile(r"(?:marque|mets|mettre|passe|passer)\s+(.+?)\s+(?:comme|en|au statut)\s+", re.I),
        re.compile(r"(.+?)\s+(?:est|passe|devient)\s+", re.I),
    ]
    action = None
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            action = match.group(1).strip(" .,:;-\"")
            break
    if not action:
        prefix = text[: status_match.start()].strip(" .,:;-\"")
        prefix = re.sub(r"^(hey jarvis|jarvis)[, ]*", "", prefix, flags=re.I)
        action = prefix
    if len(action) < 2:
        return None
    return {
        "action_text": action,
        "desired_status": desired_status.value,
        "confidence": 0.86,
    }
