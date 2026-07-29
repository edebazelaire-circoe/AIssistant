from __future__ import annotations

import asyncio
import json
from pathlib import Path

from jarvis_agent.application.config import AppConfig
from jarvis_agent.application.runtime import JarvisRuntime
from jarvis_agent.domain.models import AgentState, PolicyMode
from create_demo_workbook import create


async def run() -> None:
    root = Path(__file__).resolve().parents[1]
    workbook = create(root / "workspace" / "roadmap_demo.xlsx")
    runtime = JarvisRuntime(
        AppConfig(root / "data", root / "workspace", "127.0.0.1", 8765)
    )
    await runtime.initialize()
    await runtime.set_state(AgentState.STANDBY, "reference_scenario")
    await runtime.start_meeting("Scénario de référence")
    await runtime.inject_transcript("Décision : lancer le pilote Jarvis en septembre.", "Alice", auto_route=False)
    await runtime.inject_transcript("Bob doit préparer le guide opérateur.", "Bob", auto_route=False)
    result = await runtime.ask(
        "Marque l'action Sécuriser le portail client comme terminée"
    )
    if result.status.value == "needs_approval":
        data = result.data
        result = await runtime.capability_engine.approve(
            data["approval_id"], data["approval_token"]
        )
    summary = await runtime.end_meeting()
    print(json.dumps({"workbook": str(workbook), "result": result.model_dump(mode="json"), "summary": summary.data}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(run())
