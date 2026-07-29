# 09 — Open Questions

These questions were not resolved in the session. Task 00 owns the decision queue; Task 01 records architecture decisions before broad implementation.

## High priority

1. **Primary stack:** TypeScript/Node desktop service, Python application, or split runtime?
2. **UI shell:** local web app, Electron/Tauri desktop app, or another host?
3. **Audio capture API:** browser/WebRTC path, native desktop capture, or service-side capture?
4. **Wake-word engine:** custom enrollment classifier, embedded wake-word library, or a simple V1 keyword detector?
5. **Speech provider:** local model, remote streaming provider, or pluggable dual path?
6. **Diarization engine:** local library/model choice and streaming versus post-processing strategy?
7. **Excel mechanism:** direct workbook library, desktop automation, or both?
8. **Persistence:** SQLite/event store, embedded document store, or simple files for first slice?
9. **Realtime transport:** websocket, server-sent events, local IPC, or framework-specific channel?
10. **Provider access:** which account/project should own realtime usage, and what model IDs are actually enabled now?

## Product behavior

11. Default wake phrase and deactivation phrase.
12. Whether wake detection remains active during transcription mode.
13. Whether the assistant can speak over an ongoing meeting or should display silently by default.
14. How long interactive mode remains active without further input.
15. Whether a meeting begins from explicit command only or can be inferred later.
16. Minimum confidence/rules for automatic roadmap row selection.
17. Exact workbook schema, sheet names, status column, and action key.
18. Whether manual approval is per workflow, per changed row, or batched.
19. Whether rollback is one-click file restore or a new compensating update.

## Deferred research

20. Consensual speaker enrollment and voice embeddings.
21. Watch/phone interface.
22. Calendar and Bluetooth context enrichment.
23. Symphonia MCP integration.
24. Long-term memory graph.
