from __future__ import annotations

from pathlib import Path

import jarvis_agent.application.config as config_module
from jarvis_agent.application.config import AppConfig, load_environment, secret_source


def reset_dotenv_tracking() -> None:
    config_module._DOTENV_MANAGED_KEYS.clear()
    config_module._LOADED_ENV_FILE = None


def test_from_env_loads_explicit_dotenv(monkeypatch, tmp_path: Path) -> None:
    reset_dotenv_tracking()
    env_file = tmp_path / "jarvis.env"
    env_file.write_text(
        "OPENAI_API_KEY=test-dotenv-key\n"
        f"JARVIS_DATA_DIR={tmp_path / 'custom-data'}\n"
        f"JARVIS_ALLOWED_ROOT={tmp_path / 'custom-workspace'}\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("JARVIS_DATA_DIR", raising=False)
    monkeypatch.delenv("JARVIS_ALLOWED_ROOT", raising=False)
    monkeypatch.setenv("JARVIS_ENV_FILE", str(env_file))

    app_config = AppConfig.from_env()

    assert app_config.env_file == env_file.resolve()
    assert app_config.data_dir == (tmp_path / "custom-data").resolve()
    assert app_config.allowed_root == (tmp_path / "custom-workspace").resolve()
    assert secret_source("OPENAI_API_KEY") == "dotenv"


def test_process_environment_has_priority_over_dotenv(monkeypatch, tmp_path: Path) -> None:
    reset_dotenv_tracking()
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=dotenv-key\n", encoding="utf-8")
    monkeypatch.setenv("JARVIS_ENV_FILE", str(env_file))
    monkeypatch.setenv("OPENAI_API_KEY", "process-key")

    loaded = load_environment()

    assert loaded == env_file.resolve()
    assert config_module.os.environ["OPENAI_API_KEY"] == "process-key"
    assert secret_source("OPENAI_API_KEY") == "process_environment"


def test_reload_refreshes_value_managed_by_dotenv(monkeypatch, tmp_path: Path) -> None:
    reset_dotenv_tracking()
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=first-key\n", encoding="utf-8")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("JARVIS_ENV_FILE", str(env_file))

    load_environment()
    assert config_module.os.environ["OPENAI_API_KEY"] == "first-key"

    env_file.write_text("OPENAI_API_KEY=second-key\n", encoding="utf-8")
    load_environment()

    assert config_module.os.environ["OPENAI_API_KEY"] == "second-key"
    assert secret_source("OPENAI_API_KEY") == "dotenv"
