# 10 — Security and Data Handling

## Scope

The user stated that legal/consent handling is managed through their professional context. This document covers technical safeguards, not legal advice.

## Local-first defaults

- `MIC_OFF` captures nothing.
- `STANDBY` keeps audio local and bounded in a circular buffer.
- Remote processing begins only in states/configurations that permit it.
- The UI displays whether each active adapter is local or remote.

## Secrets

- Store API keys in environment variables, OS keychain, or a secret manager.
- Persist only secret references.
- Redact secrets from tool arguments, logs, events, screenshots, and reports.
- Test fixtures use fake keys.

## Audio and transcript retention

Retention is configurable per environment:

- raw audio off by default after processing unless explicitly required for test evidence;
- transcript and structured facts can be retained per meeting;
- wake enrollment recordings are stored separately with clear delete controls;
- future speaker embeddings require an explicit feature flag and separate data class.

## File access

- Connectors operate only inside configured allowed roots.
- Plans display the target file before mutation in manual mode.
- Automatic mode still enforces allowlists and path normalization.
- Symlink/path traversal defenses are mandatory.

## Workbook mutation safety

- Read version/fingerprint before write.
- Write to a temporary copy.
- Verify the saved copy.
- Atomically replace when supported.
- Keep a backup or rollback reference for test environments.
- Never overwrite on schema ambiguity.

## Audit

Record:

- who/what initiated the capability;
- policy mode;
- model/planner version;
- plan;
- approval evidence when required;
- tool calls;
- before/after artifact fingerprints;
- diagnostics and failure state.

Audit records must remain useful without storing raw secrets or unnecessary audio.
