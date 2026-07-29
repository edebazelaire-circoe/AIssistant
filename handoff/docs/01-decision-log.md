# 01 — Decision Log

## Decision 01 — Isolated prototype

**Status:** locked

**Decision:** Build the V1 outside Symphonia. Symphonia is a future connector/client, not the host architecture.

**Rationale:** The user wants to validate capabilities internally and reuse the process with Excel, files, document bases, or other systems.

**Implications:** No direct dependency on Symphonia domain code in the core runtime.

**Tests / enforcement:** Architecture tests reject imports from Symphonia-specific modules into core packages.

## Decision 02 — Agent Inspector as the primary V1 surface

**Status:** locked

**Decision:** Optimize the first UI for observability and experimentation, not polished end-user simplicity.

**Rationale:** The user needs to verify audio state, transcription, understanding, model selection, plans, tool calls, outputs, and failures.

**Implications:** Runtime events must be typed and streamable to the UI.

**Tests / enforcement:** Every state transition and tool execution emits an inspectable event.

## Decision 03 — Explicit operating modes

**Status:** locked

**Decision:** Support microphone off, standby, transcription, and interactive modes.

**Rationale:** The user wants complete control during testing and clear separation between silent capture and reactive behavior.

**Implications:** Modes are first-class domain state, not scattered booleans.

**Tests / enforcement:** State-machine tests cover legal transitions, audio behavior, and tool permissions per mode.

## Decision 04 — Local wake-word path with circular buffer

**Status:** locked direction; implementation provisional

**Decision:** Keep wake detection and the short pre-roll buffer local. Do not stream standby audio to remote providers.

**Rationale:** Lower latency, lower cost, and a privacy-preserving default.

**Implications:** Audio capture must support a bounded ring buffer and wake event timestamps.

**Tests / enforcement:** Standby integration tests assert no remote transcription/model call.

## Decision 05 — Diarization before speaker identification

**Status:** locked

**Decision:** V1 outputs anonymous speaker labels. Identity mapping is later.

**Rationale:** Speaker attribution materially improves meeting analysis, while identity enrollment adds complexity and biometric handling.

**Implications:** Data models separate `speaker_cluster_id` from `person_id`.

**Tests / enforcement:** Transcript segments remain valid without known identities.

## Decision 06 — Meeting mode as a lightweight loadable profile

**Status:** locked

**Decision:** Implement meeting mode as a runtime-loaded prompt/capability/configuration bundle, accessible from UI and voice.

**Rationale:** It proves dynamic behavior without building a generalized skill platform that belongs more naturally in Symphonia.

**Implications:** Define a narrow `AgentProfile` contract.

**Tests / enforcement:** Profile loading changes allowed capabilities and extraction behavior without restarting the process.

## Decision 07 — Capability abstraction above tools

**Status:** locked

**Decision:** User-facing actions are capabilities such as `update_roadmap`, implemented by workflows composed of low-level tools.

**Rationale:** The product should reason in business actions, while remaining connector-agnostic.

**Implications:** Capabilities, workflows, tools, and connectors are distinct registries/contracts.

**Tests / enforcement:** Capability tests use fake tools; connector tests do not depend on the agent.

## Decision 08 — Three policy levels per capability

**Status:** locked

**Decision:** Every capability can be disabled, manual, or automatic. Manual is the default.

**Rationale:** The user wants a progressive route to full automation and the freedom to enable it selectively.

**Implications:** Policy evaluation happens before mutating tool calls and is visible in the UI.

**Tests / enforcement:** Mutation cannot execute when disabled; manual mode requires an approval token; automatic mode records rationale and confidence.

## Decision 09 — Results must be visible

**Status:** locked

**Decision:** Tool execution must expose the produced artifact or preview, not only a success message.

**Rationale:** The V1 is a validation instrument. Silent edits prevent trust and diagnosis.

**Implications:** Tool results include artifact references, diffs, preview metadata, and diagnostics.

**Tests / enforcement:** The roadmap scenario fails acceptance if changed cells cannot be displayed.

## Decision 10 — Excel roadmap as first write scenario

**Status:** locked

**Decision:** Implement a roadmap workbook with one action per row and status colors: yellow in progress, red not done, green done.

**Rationale:** It is concrete, visually verifiable, and representative of multi-step tool execution.

**Implications:** The Excel adapter must read, map, style, save, and generate a before/after diff.

**Tests / enforcement:** Fixture workbook scenario verifies values, fills, preservation of unrelated cells, and idempotency.

## Decision 11 — Secrets only in environment variables

**Status:** locked

**Decision:** API keys and secrets remain in environment or a secret store. Model selection belongs in application configuration.

**Rationale:** Hardcoded model IDs made the earlier experiment opaque and brittle.

**Implications:** Build a provider/model manager and config validation endpoint.

**Tests / enforcement:** Serialized settings and logs must not contain raw secrets.

## Decision 12 — Role-based model selection

**Status:** locked direction; provider specifics unresolved

**Decision:** Allow different models/adapters for realtime dialogue, transcription, analysis, classification, embeddings, and local routing.

**Rationale:** One model is unlikely to optimize latency, cost, audio support, and reasoning simultaneously.

**Implications:** Core orchestration depends on role interfaces, not vendor model names.

**Tests / enforcement:** Provider contract tests use fakes and incompatible-role validation.

## Decision 13 — Exact implementation stack

**Status:** unresolved

**Decision:** No language/framework/runtime stack was locked in the session.

**Rationale:** The session focused on product and architecture capabilities.

**Implications:** Task 01 must record an ADR before implementation spreads.

**Tests / enforcement:** Repository skeleton and architecture tests must reflect the chosen ADR.

## Decision 14 — Wearable interface

**Status:** deferred

**Decision:** Do not include the connected-watch interface in V1.

**Rationale:** The immediate goal is capability validation on a local computer.

**Implications:** Preserve transport-neutral APIs, but do not build watch-specific UI or audio code.

**Tests / enforcement:** None in V1.
