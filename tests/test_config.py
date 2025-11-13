"""Tests for config module."""

import json
import os
from pathlib import Path

import pytest

from src.config import (
    Config,
    create_default_config,
    find_config_file,
    get_env_overrides,
    load_config,
    load_config_from_file,
)
from src.utils import ConfigError


def test_config_dataclass(temp_notes_dir):
    """Test Config dataclass creation."""
    config = Config(
        notes_dir=temp_notes_dir,
        editor="nvim",
        git_enabled=True,
        git_commit_interval=300,
        watch_enabled=False,
        fzf_preview=True,
        fzf_preview_command="bat --style=plain --color=always {}",
    )

    assert config.notes_dir == temp_notes_dir
    assert config.editor == "nvim"
    assert config.git_enabled is True
    assert config.git_commit_interval == 300
    assert config.watch_enabled is False
    assert config.fzf_preview is True


def test_config_defaults(temp_notes_dir):
    """Test Config with default values."""
    config = Config(notes_dir=temp_notes_dir)

    assert config.editor == "vim"
    assert config.git_enabled is True
    assert config.git_commit_interval == 300
    assert config.watch_enabled is False
    assert config.fzf_preview is True


def test_create_default_config(temp_notes_dir):
    """Test creating default config file."""
    config_path = temp_notes_dir / "config.json"
    create_default_config(config_path)

    assert config_path.exists()

    with open(config_path) as f:
        data = json.load(f)

    assert "notes_dir" in data
    assert "editor" in data
    assert "git_enabled" in data
    assert data["git_enabled"] is True


def test_load_config_from_file(temp_notes_dir, config_data):
    """Test loading config from JSON file."""
    config_path = temp_notes_dir / "config.json"

    with open(config_path, "w") as f:
        json.dump(config_data, f)

    loaded_data = load_config_from_file(config_path)

    assert loaded_data["notes_dir"] == config_data["notes_dir"]
    assert loaded_data["editor"] == config_data["editor"]


def test_load_config_from_file_invalid_json(temp_notes_dir):
    """Test loading config with invalid JSON."""
    config_path = temp_notes_dir / "config.json"

    with open(config_path, "w") as f:
        f.write("{invalid json")

    with pytest.raises(ConfigError, match="Invalid JSON"):
        load_config_from_file(config_path)


def test_get_env_overrides(monkeypatch):
    """Test environment variable overrides."""
    monkeypatch.setenv("YANA_EDITOR", "code")
    monkeypatch.setenv("YANA_GIT_ENABLED", "false")
    monkeypatch.setenv("YANA_GIT_COMMIT_INTERVAL", "600")

    overrides = get_env_overrides()

    assert overrides["editor"] == "code"
    assert overrides["git_enabled"] is False
    assert overrides["git_commit_interval"] == 600


def test_get_env_overrides_boolean_values(monkeypatch):
    """Test boolean environment variable parsing."""
    # Test various truthy values
    for value in ["true", "True", "TRUE", "1", "yes"]:
        monkeypatch.setenv("YANA_GIT_ENABLED", value)
        overrides = get_env_overrides()
        assert overrides["git_enabled"] is True

    # Test falsy values
    for value in ["false", "False", "FALSE", "0", "no"]:
        monkeypatch.setenv("YANA_GIT_ENABLED", value)
        overrides = get_env_overrides()
        assert overrides["git_enabled"] is False


def test_find_config_file_env_var(temp_notes_dir, monkeypatch):
    """Test finding config via YANA_CONFIG env var."""
    config_path = temp_notes_dir / "custom-config.json"
    config_path.touch()

    monkeypatch.setenv("YANA_CONFIG", str(config_path))

    found_path = find_config_file()
    assert found_path == config_path


def test_find_config_file_project_local(tmp_path, monkeypatch):
    """Test finding config in .yana directory."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Create project-local config
    project_config_dir = tmp_path / ".yana"
    project_config_dir.mkdir()
    config_path = project_config_dir / "config.json"
    config_path.touch()

    found_path = find_config_file()
    assert found_path == config_path


def test_find_config_file_user_config(tmp_path, monkeypatch):
    """Test finding config in user's .config directory."""
    # Mock home directory
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Change to a directory without local config
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)

    # Create user config
    user_config_dir = fake_home / ".config" / "yana"
    user_config_dir.mkdir(parents=True)
    config_path = user_config_dir / "config.json"
    config_path.touch()

    found_path = find_config_file()
    assert found_path == config_path


def test_find_config_file_none(tmp_path, monkeypatch):
    """Test when no config file exists."""
    # Change to temp directory with no config
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)

    # Mock home to avoid finding real config
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    found_path = find_config_file()
    assert found_path is None


def test_load_config_creates_default(tmp_path, monkeypatch):
    """Test that load_config creates default config if none exists."""
    # Mock home directory
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Change to directory without config
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)

    # Create notes directory
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()

    # Mock the default config to point to our temp notes dir
    monkeypatch.setenv("YANA_NOTES_DIR", str(notes_dir))

    config = load_config()

    # Should create default config
    default_config_path = fake_home / ".config" / "yana" / "config.json"
    assert default_config_path.exists()

    assert config.notes_dir == notes_dir
    assert config.editor in ["vim", os.getenv("EDITOR", "vim")]


def test_load_config_missing_notes_dir(tmp_path, monkeypatch):
    """Test load_config with non-existent notes directory."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    monkeypatch.chdir(work_dir)

    # Set notes dir to non-existent path
    monkeypatch.setenv("YANA_NOTES_DIR", str(tmp_path / "nonexistent"))

    with pytest.raises(ConfigError, match="Notes directory does not exist"):
        load_config()


def test_load_config_env_override(tmp_path, monkeypatch, config_data):
    """Test that environment variables override config file."""
    import src.config

    # Clear singleton
    src.config._config = None

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    # Create notes directory
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()

    # Create config file
    config_dir = fake_home / ".config" / "yana"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"

    config_data["notes_dir"] = str(notes_dir)
    with open(config_path, "w") as f:
        json.dump(config_data, f)

    # Point to config file
    monkeypatch.setenv("YANA_CONFIG", str(config_path))
    # Override editor with env var
    monkeypatch.setenv("YANA_EDITOR", "emacs")

    config = load_config()

    # Editor should be overridden
    assert config.editor == "emacs"
    # But notes_dir should be from config file
    assert config.notes_dir == notes_dir
