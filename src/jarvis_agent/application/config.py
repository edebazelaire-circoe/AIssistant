from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class AppConfig:
    data_dir: Path
    allowed_root: Path
    host: str
    port: int

    @classmethod
    def from_env(cls) -> "AppConfig":
        data_dir = Path(os.getenv("JARVIS_DATA_DIR", "./data")).expanduser().resolve()
        allowed_root = Path(os.getenv("JARVIS_ALLOWED_ROOT", "./workspace")).expanduser().resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        allowed_root.mkdir(parents=True, exist_ok=True)
        return cls(
            data_dir=data_dir,
            allowed_root=allowed_root,
            host=os.getenv("JARVIS_HOST", "127.0.0.1"),
            port=int(os.getenv("JARVIS_PORT", "8765")),
        )
