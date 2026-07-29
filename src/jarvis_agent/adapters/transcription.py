from __future__ import annotations

import asyncio
import base64
import json
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

import websockets

from jarvis_agent.domain.models import AudioFrame, Diagnostic, ErrorCode


@dataclass(slots=True, frozen=True)
class SpeechChunk:
    text: str
    is_final: bool
    start_ms: int
    end_ms: int
    confidence: float | None = None
    revision_key: str | None = None


class StreamingSpeechAdapter(Protocol):
    id: str

    async def transcribe(self, frames: AsyncIterator[AudioFrame]) -> AsyncIterator[SpeechChunk]: ...


class FixtureSpeechAdapter:
    id = "fixture_speech"

    async def transcribe_text(self, text: str, start_ms: int = 0) -> AsyncIterator[SpeechChunk]:
        words = text.split()
        if not words:
            return
        partial = " ".join(words[: max(1, len(words) // 2)])
        yield SpeechChunk(partial, False, start_ms, start_ms + 300, 0.8, "fixture")
        await asyncio.sleep(0)
        yield SpeechChunk(text, True, start_ms, start_ms + max(600, len(words) * 160), 0.99, "fixture")


class OpenAIRealtimeTranscriptionAdapter:
    """Optional adapter isolated from the domain.

    Event names are intentionally accepted through a tolerant parser because the Realtime API
    evolves. The endpoint/model are configuration, not architecture assumptions.
    """

    id = "openai_realtime_transcription"

    def __init__(
        self,
        model_id: str,
        secret_reference: str = "OPENAI_API_KEY",
        endpoint: str = "wss://api.openai.com/v1/realtime",
        language: str = "fr",
    ) -> None:
        self.model_id = model_id
        self.secret_reference = secret_reference
        self.endpoint = endpoint
        self.language = language

    async def transcribe(self, frames: AsyncIterator[AudioFrame]) -> AsyncIterator[SpeechChunk]:
        key = os.getenv(self.secret_reference)
        if not key:
            raise RuntimeError(
                Diagnostic(
                    code=ErrorCode.SECRET_MISSING,
                    message=f"Environment variable {self.secret_reference} is missing",
                    component=self.id,
                    suggested_action="Configure the secret reference in the environment.",
                ).model_dump_json()
            )
        uri = f"{self.endpoint}?model={self.model_id}"
        headers = {"Authorization": f"Bearer {key}"}
        async with websockets.connect(uri, additional_headers=headers, max_size=8_000_000) as ws:
            await ws.send(
                json.dumps(
                    {
                        "type": "session.update",
                        "session": {
                            "input_audio_format": "pcm16",
                            "input_audio_transcription": {
                                "model": self.model_id,
                                "language": self.language,
                            },
                            "turn_detection": {"type": "server_vad"},
                        },
                    }
                )
            )

            async def sender() -> None:
                async for frame in frames:
                    await ws.send(
                        json.dumps(
                            {
                                "type": "input_audio_buffer.append",
                                "audio": frame.pcm16_b64,
                            }
                        )
                    )
                await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))

            send_task = asyncio.create_task(sender())
            try:
                async for raw in ws:
                    event = json.loads(raw)
                    event_type = str(event.get("type", ""))
                    if event_type == "error":
                        raise RuntimeError(json.dumps(event.get("error", {})))
                    text = (
                        event.get("transcript")
                        or event.get("delta")
                        or event.get("text")
                        or event.get("item", {}).get("content", [{}])[0].get("transcript")
                    )
                    if not text:
                        if send_task.done():
                            break
                        continue
                    is_final = any(marker in event_type for marker in ("completed", "done", "final"))
                    yield SpeechChunk(
                        text=str(text),
                        is_final=is_final,
                        start_ms=int(event.get("audio_start_ms", 0)),
                        end_ms=int(event.get("audio_end_ms", 0)),
                        confidence=None,
                        revision_key=str(event.get("item_id") or event.get("id") or "openai"),
                    )
                    if is_final and send_task.done():
                        break
            finally:
                send_task.cancel()
