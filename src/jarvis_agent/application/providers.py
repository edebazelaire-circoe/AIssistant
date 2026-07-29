from __future__ import annotations

import os
import time
from typing import Any

import httpx

from jarvis_agent.application.event_store import EventStore
from jarvis_agent.domain.models import (
    ModelAssignment,
    ModelRole,
    ProviderConfig,
    ProviderDiagnosticReport,
    ProviderDiagnosticStage,
)


class ProviderManager:
    def __init__(self, store: EventStore) -> None:
        self.store = store

    def save_provider(self, config: ProviderConfig) -> None:
        self.store.set_setting(f"provider:{config.id}", config.model_dump(mode="json"))

    def list_providers(self) -> list[ProviderConfig]:
        return [
            ProviderConfig.model_validate(value)
            for value in self.store.list_settings("provider:").values()
        ]

    def get_provider(self, provider_id: str) -> ProviderConfig | None:
        raw = self.store.get_setting(f"provider:{provider_id}")
        return None if raw is None else ProviderConfig.model_validate(raw)

    def assign_model(self, assignment: ModelAssignment) -> None:
        self.store.set_setting(
            f"model_assignment:{assignment.role.value}", assignment.model_dump(mode="json")
        )

    def list_assignments(self) -> list[ModelAssignment]:
        return [
            ModelAssignment.model_validate(value)
            for value in self.store.list_settings("model_assignment:").values()
        ]

    def get_assignment(self, role: ModelRole) -> ModelAssignment | None:
        raw = self.store.get_setting(f"model_assignment:{role.value}")
        return None if raw is None else ModelAssignment.model_validate(raw)

    async def diagnose(
        self,
        config: ProviderConfig,
        role: ModelRole | None = None,
        model_id: str | None = None,
    ) -> ProviderDiagnosticReport:
        if config.provider_type == "fake":
            return self._diagnose_fake(config, role, model_id)
        if config.provider_type != "openai":
            return ProviderDiagnosticReport(
                provider_config_id=config.id,
                role=role,
                model_id=model_id,
                stages=(
                    ProviderDiagnosticStage(
                        stage="provider_adapter",
                        ok=False,
                        code="provider_unavailable",
                        message=f"No diagnostic adapter for {config.provider_type}",
                    ),
                ),
            )
        return await self._diagnose_openai(config, role, model_id)

    def _diagnose_fake(
        self, config: ProviderConfig, role: ModelRole | None, model_id: str | None
    ) -> ProviderDiagnosticReport:
        scenario = self.store.get_setting(f"fake_provider_scenario:{config.id}", "success")
        stages: list[ProviderDiagnosticStage] = []
        ordered = [
            ("secret_present", "secret_missing"),
            ("authentication", "authentication_failed"),
            ("project_account", "project_not_found"),
            ("billing_quota", "billing_or_quota_blocked"),
            ("model_access", "model_access_denied"),
            ("role_compatibility", "role_not_supported"),
            ("session_transport", "session_handshake_failed"),
            ("minimal_inference", "provider_unavailable"),
        ]
        failed = False
        for stage, code in ordered:
            ok = not failed and scenario not in {stage, code}
            stages.append(
                ProviderDiagnosticStage(
                    stage=stage,
                    ok=ok,
                    code=None if ok else code,
                    message="OK" if ok else f"Injected fake failure at {stage}",
                    latency_ms=1,
                )
            )
            failed = failed or not ok
        return ProviderDiagnosticReport(
            provider_config_id=config.id, role=role, model_id=model_id, stages=tuple(stages)
        )

    async def _diagnose_openai(
        self, config: ProviderConfig, role: ModelRole | None, model_id: str | None
    ) -> ProviderDiagnosticReport:
        stages: list[ProviderDiagnosticStage] = []
        secret = os.getenv(config.secret_reference)
        stages.append(
            ProviderDiagnosticStage(
                stage="secret_present",
                ok=bool(secret),
                code=None if secret else "secret_missing",
                message=(
                    f"Secret reference {config.secret_reference} resolved"
                    if secret
                    else f"Environment variable {config.secret_reference} is missing"
                ),
            )
        )
        if not secret:
            return ProviderDiagnosticReport(
                provider_config_id=config.id, role=role, model_id=model_id, stages=tuple(stages)
            )
        base_url = (config.base_url or "https://api.openai.com/v1").rstrip("/")
        headers = {"Authorization": f"Bearer {secret}"}
        if config.project_or_org_ref:
            headers["OpenAI-Project"] = config.project_or_org_ref
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{base_url}/models", headers=headers)
            latency = round((time.perf_counter() - started) * 1000)
            if response.status_code == 401:
                stages.append(
                    ProviderDiagnosticStage(
                        stage="authentication",
                        ok=False,
                        code="authentication_failed",
                        message="Credentials were rejected",
                        latency_ms=latency,
                    )
                )
                return ProviderDiagnosticReport(
                    provider_config_id=config.id, role=role, model_id=model_id, stages=tuple(stages)
                )
            if response.status_code == 429:
                stages.append(
                    ProviderDiagnosticStage(
                        stage="authentication",
                        ok=True,
                        message="Credentials accepted",
                        latency_ms=latency,
                    )
                )
                stages.append(
                    ProviderDiagnosticStage(
                        stage="billing_quota",
                        ok=False,
                        code="billing_or_quota_blocked",
                        message="The provider returned HTTP 429; inspect quota/rate details in provider console",
                    )
                )
                return ProviderDiagnosticReport(
                    provider_config_id=config.id, role=role, model_id=model_id, stages=tuple(stages)
                )
            response.raise_for_status()
            payload = response.json()
            models = {item.get("id") for item in payload.get("data", [])}
            stages.extend(
                [
                    ProviderDiagnosticStage(
                        stage="authentication", ok=True, message="Credentials accepted", latency_ms=latency
                    ),
                    ProviderDiagnosticStage(
                        stage="project_account",
                        ok=True,
                        message="Project/account context accepted",
                    ),
                    ProviderDiagnosticStage(
                        stage="billing_quota",
                        ok=True,
                        message="No quota block detected by the inventory probe",
                    ),
                ]
            )
            if model_id:
                found = model_id in models
                stages.append(
                    ProviderDiagnosticStage(
                        stage="model_access",
                        ok=found,
                        code=None if found else "model_not_found",
                        message=(
                            f"Model {model_id} appears in provider inventory"
                            if found
                            else f"Model {model_id} was not returned by provider inventory"
                        ),
                    )
                )
            else:
                stages.append(
                    ProviderDiagnosticStage(
                        stage="model_access",
                        ok=True,
                        message=f"Inventory returned {len(models)} model identifiers",
                    )
                )
            # Role compatibility remains explicit configuration until a live adapter probe verifies it.
            role_ok = role is None or bool(model_id)
            stages.append(
                ProviderDiagnosticStage(
                    stage="role_compatibility",
                    ok=role_ok,
                    code=None if role_ok else "role_not_supported",
                    message=(
                        "Role assignment has an explicit model ID"
                        if role_ok
                        else "Select a model before testing role compatibility"
                    ),
                )
            )
            if role in {ModelRole.REALTIME, ModelRole.TRANSCRIPTION}:
                stages.append(
                    ProviderDiagnosticStage(
                        stage="session_transport",
                        ok=False,
                        code="session_handshake_not_run",
                        message="Inventory succeeded. Run a live audio session from the Inspector to verify Realtime transport and account entitlement.",
                    )
                )
            else:
                stages.append(
                    ProviderDiagnosticStage(
                        stage="session_transport",
                        ok=True,
                        message="No Realtime transport required for this role",
                    )
                )
        except httpx.HTTPStatusError as exc:
            stages.append(
                ProviderDiagnosticStage(
                    stage="authentication",
                    ok=False,
                    code="provider_unavailable",
                    message=f"Provider returned HTTP {exc.response.status_code}",
                )
            )
        except (httpx.RequestError, ValueError) as exc:
            stages.append(
                ProviderDiagnosticStage(
                    stage="authentication",
                    ok=False,
                    code="provider_unavailable",
                    message=f"Provider probe failed: {type(exc).__name__}",
                )
            )
        return ProviderDiagnosticReport(
            provider_config_id=config.id, role=role, model_id=model_id, stages=tuple(stages)
        )

    def provider_summary(self) -> list[dict[str, Any]]:
        assignments = {item.role.value: item.model_dump(mode="json") for item in self.list_assignments()}
        return [
            {
                **provider.model_dump(mode="json"),
                "secret_present": bool(os.getenv(provider.secret_reference)),
                "assignments": {
                    role: value
                    for role, value in assignments.items()
                    if value["provider_config_id"] == provider.id
                },
            }
            for provider in self.list_providers()
        ]
