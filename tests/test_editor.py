"""Tests for editor module."""

import time
from unittest.mock import MagicMock, patch

import pytest

from src.editor import get_editor, get_editor_command, needs_wait_flag, open_in_editor
from src.utils import EditorError


def test_get_editor_from_config_editor(monkeypatch):
    """Test get_editor prioritizes config_editor parameter."""
    monkeypatch.setenv("YANA_EDITOR", "emacs")
    monkeypatch.setenv("VISUAL", "vim")
    monkeypatch.setenv("EDITOR", "nano")

    editor = get_editor("code")

    # Config editor should win
    assert editor == "code"


def test_get_editor_from_yana_editor_env(monkeypatch):
    """Test get_editor uses YANA_EDITOR when no config."""
    monkeypatch.setenv("YANA_EDITOR", "emacs")
    monkeypatch.setenv("VISUAL", "vim")

    editor = get_editor()

    assert editor == "emacs"


def test_get_editor_from_visual_env(monkeypatch):
    """Test get_editor falls back to VISUAL."""
    monkeypatch.delenv("YANA_EDITOR", raising=False)
    monkeypatch.setenv("VISUAL", "sublime")

    editor = get_editor()

    assert editor == "sublime"


def test_get_editor_from_editor_env(monkeypatch):
    """Test get_editor falls back to EDITOR."""
    monkeypatch.delenv("YANA_EDITOR", raising=False)
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.setenv("EDITOR", "nano")

    editor = get_editor()

    assert editor == "nano"


def test_get_editor_none(monkeypatch):
    """Test get_editor raises error when no editor configured."""
    monkeypatch.delenv("YANA_EDITOR", raising=False)
    monkeypatch.delenv("VISUAL", raising=False)
    monkeypatch.delenv("EDITOR", raising=False)

    with pytest.raises(EditorError, match="No editor configured"):
        get_editor()


def test_needs_wait_flag():
    """Test needs_wait_flag detection."""
    # Editors that need wait flag
    assert needs_wait_flag("code") is True
    assert needs_wait_flag("Code") is True
    assert needs_wait_flag("subl") is True
    assert needs_wait_flag("sublime") is True

    # Editors that don't need wait flag
    assert needs_wait_flag("vim") is False
    assert needs_wait_flag("nvim") is False
    assert needs_wait_flag("nano") is False
    assert needs_wait_flag("emacs") is False


def test_get_editor_command_with_wait_flag(temp_notes_dir):
    """Test get_editor_command adds wait flag for VS Code and Sublime."""
    file_path = temp_notes_dir / "test.md"

    # VS Code should get -w flag
    cmd = get_editor_command("code", file_path)
    assert cmd == ["code", "-w", str(file_path)]

    # Sublime should get -w flag
    cmd = get_editor_command("subl", file_path)
    assert cmd == ["subl", "-w", str(file_path)]


def test_get_editor_command_without_wait_flag(temp_notes_dir):
    """Test get_editor_command without wait flag for other editors."""
    file_path = temp_notes_dir / "test.md"

    # Vim should have no special flags
    cmd = get_editor_command("vim", file_path)
    assert cmd == ["vim", str(file_path)]

    # Nvim should have no special flags
    cmd = get_editor_command("nvim", file_path)
    assert cmd == ["nvim", str(file_path)]


@patch("subprocess.run")
def test_open_in_editor_success(mock_run, temp_notes_dir):
    """Test opening file in editor successfully."""
    note_path = temp_notes_dir / "test.md"
    note_path.write_text("# Test")

    def modify_file(*args, **kwargs):
        """Simulate editor modifying file."""
        time.sleep(0.01)
        note_path.write_text("# Modified")
        return MagicMock(returncode=0)

    mock_run.side_effect = modify_file

    was_modified = open_in_editor(note_path, "vim")

    assert was_modified is True
    mock_run.assert_called_once()


@patch("subprocess.run")
def test_open_in_editor_file_not_found(mock_run, temp_notes_dir):
    """Test opening non-existent file."""
    note_path = temp_notes_dir / "missing.md"

    with pytest.raises(EditorError, match="not exist"):
        open_in_editor(note_path, "vim")


@patch("subprocess.run")
def test_open_in_editor_editor_not_found(mock_run, temp_notes_dir):
    """Test with editor not found."""
    note_path = temp_notes_dir / "test.md"
    note_path.write_text("# Test")

    # Mock FileNotFoundError
    mock_run.side_effect = FileNotFoundError()

    with pytest.raises(EditorError, match="Editor not found"):
        open_in_editor(note_path, "nonexistent-editor")
