# ADR 0001 — Python local service and browser Inspector

## Status
Accepted on 2026-07-29.

## Decision
Use one Python process for the V1 runtime and a dependency-free browser UI served by FastAPI.

- Python owns the domain, state machine, event store, provider adapters, audio buffer,
  capability engine, and Excel connector.
- SQLite is the append-only local event/config store.
- Browser microphone capture sends local PCM frames to the service over a local WebSocket.
- A separate event WebSocket supports live updates and cursor-based replay.
- The first diarization and wake adapters are deliberately modest local baselines.
- OpenAI Realtime is an optional adapter behind role-based provider configuration.

## Why
This is the smallest architecture that can exercise microphone input, Python audio/ML libraries,
Excel mutation, persistence, and a rich Inspector without operating a second runtime. The ports
preserve a future sidecar split if heavier ML adapters require it.

## Consequences
The UI is not a packaged desktop shell yet. It runs on localhost and requires a browser. Browser
microphone permissions and native audio device selection remain browser-managed.
