from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "jarvis_agent"
RULES = {
    "domain": {"fastapi", "openpyxl", "httpx", "websockets", "jarvis_agent.web", "jarvis_agent.connectors"},
    "connectors": {"fastapi", "jarvis_agent.profiles", "jarvis_agent.application.runtime"},
    "profiles": {"fastapi", "openpyxl", "jarvis_agent.connectors"},
}
FORBIDDEN_ANYWHERE = {"symphonia"}


def imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def main() -> None:
    failures: list[str] = []
    for path in ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT)
        package = relative.parts[0]
        imports = imported_names(path)
        for imported in imports:
            lower = imported.lower()
            if any(name in lower for name in FORBIDDEN_ANYWHERE):
                failures.append(f"{relative}: forbidden global dependency {imported}")
            for forbidden in RULES.get(package, set()):
                if imported == forbidden or imported.startswith(forbidden + "."):
                    failures.append(f"{relative}: {package} cannot import {imported}")
    if failures:
        raise SystemExit("Architecture violations:\n" + "\n".join(f"- {item}" for item in failures))
    print(f"Architecture gates passed for {sum(1 for _ in ROOT.rglob('*.py'))} Python files")


if __name__ == "__main__":
    main()
