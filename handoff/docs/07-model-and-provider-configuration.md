# 07 — Model and Provider Configuration

## Problem to solve

The earlier prototype stored an API key and a model string in environment variables. Text calls worked, while realtime access failed with an authentication/access/credit-style error. The V1 must distinguish configuration failures precisely rather than reporting “bad key” for every cause.

## Configuration rules

- Environment variables or an external secret store contain only secrets and secret references.
- Non-secret configuration is persisted through the application.
- Model assignments are role-based.
- Vendor SDK model objects never enter domain code.
- A provider adapter declares supported roles and transports.

## Model roles

- `realtime` — bidirectional low-latency conversation/audio session.
- `transcription` — streaming or batch speech-to-text.
- `diarization` — speaker segmentation, often local and separate from the LLM.
- `analysis` — meeting reasoning, summaries, and capability planning.
- `classification` — lightweight intent/event classification.
- `embedding` — document or future speaker/context embeddings.
- `local_router` — optional local wake/intention routing.

The same provider/model may fill multiple roles, but this is configuration, not an architectural assumption.

## Provider capability inventory

A provider adapter should expose:

- provider identity;
- available/known model IDs where the API permits listing;
- supported input/output modalities;
- supported transports: REST, streaming, websocket, WebRTC, local process;
- supported roles;
- project/account context;
- rate and quota metadata when available;
- diagnostic probes.

## Test configuration workflow

The UI action must execute staged probes and return independent results:

1. **Secret present** — reference resolves without exposing value.
2. **Authentication** — credentials accepted.
3. **Project/account resolution** — correct project or organization selected.
4. **Billing/quota** — request not blocked by exhausted or absent quota where detectable.
5. **Model access** — selected model exists and is enabled for the account/project.
6. **Role compatibility** — model supports required modality and transport.
7. **Session transport** — realtime handshake/session creation succeeds.
8. **Minimal inference** — tiny no-op or echo-style request succeeds.

## Error taxonomy

- `secret_missing`
- `authentication_failed`
- `project_not_found`
- `billing_or_quota_blocked`
- `model_not_found`
- `model_access_denied`
- `role_not_supported`
- `transport_not_supported`
- `session_handshake_failed`
- `rate_limited`
- `provider_unavailable`
- `unknown_provider_error`

Raw vendor responses are stored only in redacted diagnostics.

## Selection UX

- Prefer a provider-backed model list when available.
- Allow manual model ID entry for providers without inventory APIs.
- Display capability badges such as audio-in, audio-out, streaming, tool use, and context size only when verified by the adapter.
- Warn on stale saved model IDs.
- Never label a model “GPT Live” based on a string substring; verify role/transport support.

## Open implementation decision

The exact provider and model IDs must be verified at implementation time against current official provider documentation and the user's actual project access. This handoff intentionally does not freeze a possibly obsolete realtime model identifier.
