from __future__ import annotations

import shutil
import tempfile
from pathlib import Path


root = Path(__file__).resolve().parents[1]
dist = root / "dist"
dist.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="jarvis_release_") as temp:
    staging = Path(temp) / "jarvis-agent-inspector-v0.1.0"
    ignore = shutil.ignore_patterns(
        ".git",
        ".venv",
        ".pytest_cache",
        "__pycache__",
        "*.pyc",
        ".env",
        "data",
        "dist",
        "*.bak",
        "*.tmp",
        "~$*",
    )
    shutil.copytree(root, staging, ignore=ignore)
    archive = shutil.make_archive(str(dist / staging.name), "zip", root_dir=staging.parent, base_dir=staging.name)
print(archive)
