from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, find_dotenv


_LOADED_ENV_FILE: Path | None = None
_DOTENV_MANAGED_KEYS: set[str] = set()


def _resolve_env_file() -> Path | None:
    explicit = os.getenv("JARVIS_ENV_FILE")
    if explicit:
        candidate = Path(explicit).expanduser().resolve()
        return candidate if candidate.is_file() else None

    discovered = find_dotenv(filename=".env", usecwd=True)
    if discovered:
        return Path(discovered).resolve()

    project_candidate = Path(__file__).resolve().parents[3] / ".env"
    return project_candidate if project_candidate.is_file() else None


def load_environment() -> Path | None:
    """Load a local .env without overriding genuine process environment variables."""

    global _LOADED_ENV_FILE

    env_file = _resolve_env_file()
    if env_file is None:
        _LOADED_ENV_FILE = None
        return None

    values = dotenv_values(env_file)
    for name, value in values.items():
        if not name or value is None:
            continue
        if name in os.environ and name not in _DOTENV_MANAGED_KEYS:
            continue
        os.environ[name] = value
        _DOTENV_MANAGED_KEYS.add(name)

    _LOADED_ENV_FILE = env_file
    return env_file


def loaded_env_file() -> Path | None:
    return _LOADED_ENV_FILE


def secret_source(name: str) -> str | None:
    if not os.getenv(name):
        return None
    return "dotenv" if name in _DOTENV_MANAGED_KEYS else "process_environment"


@dataclass(slots=True, frozen=True)
class AppConfig:
    data_dir: Path
    allowed_root: Path
    host: str
    port: int
    env_file: Path | None = None

    @classmethod
    def from_env(cls) -> "AppConfig":
        env_file = load_environment()
        data_dir = Path(os.getenv("JARVIS_DATA_DIR", "./data")).expanduser().resolve()
        allowed_root = Path(os.getenv("JARVIS_ALLOWED_ROOT", "./workspace")).expanduser().resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        allowed_root.mkdir(parents=True, exist_ok=True)
        return cls(
            data_dir=data_dir,
            allowed_root=allowed_root,
            host=os.getenv("JARVIS_HOST", "127.0.0.1"),
            port=int(os.getenv("JARVIS_PORT", "8765")),
            env_file=env_file,
        )
