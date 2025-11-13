"""
Configuration management using JSON files and environment variables.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.utils import ConfigError


@dataclass(slots=True, frozen=True)
class Config:
    """YANA configuration settings."""

    notes_dir: Path
    editor: str = "vim"
    git_enabled: bool = True
    git_commit_interval: int = 300
    watch_enabled: bool = False
    fzf_preview: bool = True
    fzf_preview_command: str = "bat --style=plain --color=always {}"


def find_config_file() -> Optional[Path]:
    """
    Find config file in order of priority:
    1. YANA_CONFIG environment variable
    2. ./.yana/config.json (project-local)
    3. ~/.config/yana/config.json (user default)

    Returns None if no config file found.
    """
    # 1. Check environment variable
    if env_config := os.getenv("YANA_CONFIG"):
        config_path = Path(env_config).expanduser()
        if config_path.exists():
            return config_path

    # 2. Check project-local config
    project_config = Path.cwd() / ".yana" / "config.json"
    if project_config.exists():
        return project_config

    # 3. Check user config
    user_config = Path.home() / ".config" / "yana" / "config.json"
    if user_config.exists():
        return user_config

    return None


def load_config_from_file(config_path: Path) -> dict:
    """Load and parse JSON config file."""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config file {config_path}: {e}")
    except Exception as e:
        raise ConfigError(f"Failed to read config file {config_path}: {e}")


def get_env_overrides() -> dict:
    """Get configuration overrides from environment variables."""
    overrides = {}

    # Map environment variables to config keys
    env_mapping = {
        "YANA_NOTES_DIR": ("notes_dir", Path),
        "YANA_EDITOR": ("editor", str),
        "YANA_GIT_ENABLED": (
            "git_enabled",
            lambda x: x.lower() in ("true", "1", "yes"),
        ),
        "YANA_GIT_COMMIT_INTERVAL": ("git_commit_interval", int),
        "YANA_WATCH_ENABLED": (
            "watch_enabled",
            lambda x: x.lower() in ("true", "1", "yes"),
        ),
        "YANA_FZF_PREVIEW": (
            "fzf_preview",
            lambda x: x.lower() in ("true", "1", "yes"),
        ),
        "YANA_FZF_PREVIEW_COMMAND": ("fzf_preview_command", str),
    }

    for env_var, (config_key, converter) in env_mapping.items():
        if value := os.getenv(env_var):
            try:
                overrides[config_key] = converter(value)
            except Exception as e:
                raise ConfigError(f"Invalid value for {env_var}: {value} ({e})")

    return overrides


def create_default_config(config_path: Path) -> None:
    """Create a default configuration file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)

    default_config = {
        "notes_dir": str(Path.home() / "notes"),
        "editor": os.getenv("EDITOR", "vim"),
        "git_enabled": True,
        "git_commit_interval": 300,
        "watch_enabled": False,
        "fzf_preview": True,
        "fzf_preview_command": "bat --style=plain --color=always {}",
    }

    with open(config_path, "w") as f:
        json.dump(default_config, f, indent=2)


def load_config() -> Config:
    """
    Load configuration from file and environment variables.

    Raises ConfigError if required settings are missing.
    """
    # Start with empty config
    config_data = {}

    # Load from file if exists
    config_file = find_config_file()
    if config_file:
        config_data = load_config_from_file(config_file)
    else:
        # Create default config
        default_path = Path.home() / ".config" / "yana" / "config.json"
        create_default_config(default_path)
        config_data = load_config_from_file(default_path)

    # Apply environment variable overrides
    env_overrides = get_env_overrides()
    config_data.update(env_overrides)

    # Validate required fields
    if "notes_dir" not in config_data:
        raise ConfigError(
            "notes_dir is required in config. "
            "Set it in config.json or via YANA_NOTES_DIR environment variable."
        )

    # Convert notes_dir to Path
    notes_dir = Path(config_data["notes_dir"]).expanduser().resolve()
    if not notes_dir.exists():
        raise ConfigError(
            f"Notes directory does not exist: {notes_dir}\n"
            f"Create it with: mkdir -p {notes_dir}"
        )

    config_data["notes_dir"] = notes_dir

    # Create Config object
    try:
        return Config(**config_data)
    except TypeError as e:
        raise ConfigError(f"Invalid configuration: {e}")


# Singleton config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the singleton config instance (loads on first call)."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
