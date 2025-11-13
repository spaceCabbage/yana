"""
Editor integration for opening notes.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

from src.utils import EditorError


def get_editor(config_editor: Optional[str] = None) -> str:
    """
    Get editor command with priority chain:
    1. config_editor parameter
    2. YANA_EDITOR environment variable
    3. VISUAL environment variable
    4. EDITOR environment variable
    5. Error (no editor configured)

    Args:
        config_editor: Editor from config file

    Returns:
        Editor command string

    Raises:
        EditorError: If no editor is configured
    """
    editor = (
        config_editor
        or os.getenv("YANA_EDITOR")
        or os.getenv("VISUAL")
        or os.getenv("EDITOR")
    )

    if not editor:
        raise EditorError(
            "No editor configured. Set YANA_EDITOR, VISUAL, or EDITOR environment variable, "
            "or configure editor in config.json"
        )

    return editor


def needs_wait_flag(editor: str) -> bool:
    """
    Check if editor needs a wait flag to block until file is closed.

    Some editors (VS Code, Sublime) launch in the background by default
    and need a special flag to wait for the file to close.

    Args:
        editor: Editor command

    Returns:
        True if editor needs wait flag
    """
    editor_lower = editor.lower()
    return any(name in editor_lower for name in ["code", "subl", "sublime"])


def get_editor_command(editor: str, file_path: Path) -> list[str]:
    """
    Build editor command with appropriate flags.

    Args:
        editor: Editor command
        file_path: Path to file to open

    Returns:
        List of command arguments
    """
    if needs_wait_flag(editor):
        # VS Code: code -w file.md
        # Sublime: subl -w file.md
        return [editor, "-w", str(file_path)]
    else:
        # vim, nvim, nano, emacs, etc.
        return [editor, str(file_path)]


def open_in_editor(file_path: Path, config_editor: Optional[str] = None) -> bool:
    """
    Open file in configured editor (blocking call).

    Args:
        file_path: Path to file to edit
        config_editor: Editor from config (optional)

    Returns:
        True if file was modified, False otherwise

    Raises:
        EditorError: If editor fails or is not configured
    """
    if not file_path.exists():
        raise EditorError(f"File does not exist: {file_path}")

    # Get editor
    editor = get_editor(config_editor)

    # Get file modification time before editing
    initial_mtime = file_path.stat().st_mtime

    # Build command
    command = get_editor_command(editor, file_path)

    # Open editor (blocking)
    try:
        result = subprocess.run(command, check=False)

        if result.returncode != 0:
            raise EditorError(f"Editor exited with code {result.returncode}: {editor}")

    except FileNotFoundError:
        raise EditorError(f"Editor not found: {editor}")
    except Exception as e:
        raise EditorError(f"Failed to open editor: {e}")

    # Check if file was modified
    final_mtime = file_path.stat().st_mtime
    return final_mtime > initial_mtime
