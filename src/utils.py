"""
Utility functions and custom exceptions.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

# Singleton Rich console
console = Console()


# ============================================================================
# Custom Exceptions
# ============================================================================


class YanaError(Exception):
    """Base exception for all YANA errors."""

    pass


class ConfigError(YanaError):
    """Configuration-related errors."""

    pass


class NoteError(YanaError):
    """Note operation errors."""

    pass


class GitError(YanaError):
    """Git operation errors."""

    pass


class EditorError(YanaError):
    """Editor-related errors."""

    pass


class FzfError(YanaError):
    """FZF-related errors."""

    pass


# ============================================================================
# Date/Time Helpers
# ============================================================================


def format_timestamp(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse ISO format timestamp.

    Returns None if parsing fails.
    """
    try:
        return datetime.fromisoformat(timestamp_str)
    except Exception:
        return None


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()


# ============================================================================
# Path Validation
# ============================================================================


def validate_path(path: Path, must_exist: bool = False) -> Path:
    """
    Validate and expand a path.

    Args:
        path: Path to validate
        must_exist: Raise error if path doesn't exist

    Returns:
        Resolved absolute path

    Raises:
        YanaError: If path is invalid or doesn't exist (when must_exist=True)
    """
    try:
        resolved = path.expanduser().resolve()

        if must_exist and not resolved.exists():
            raise YanaError(f"Path does not exist: {resolved}")

        return resolved

    except Exception as e:
        raise YanaError(f"Invalid path: {path} ({e})")


def ensure_directory(path: Path) -> Path:
    """
    Ensure directory exists, creating it if necessary.

    Args:
        path: Directory path

    Returns:
        Resolved directory path

    Raises:
        YanaError: If path exists but is not a directory
    """
    resolved = path.expanduser().resolve()

    if resolved.exists() and not resolved.is_dir():
        raise YanaError(f"Path exists but is not a directory: {resolved}")

    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


# ============================================================================
# String Helpers
# ============================================================================


def slugify(text: str) -> str:
    """
    Convert text to a URL-friendly slug.

    Args:
        text: Text to slugify

    Returns:
        Slugified text (lowercase, spaces to hyphens)
    """
    return text.lower().strip().replace(" ", "-")


def truncate(text: str, max_length: int = 50) -> str:
    """
    Truncate text to max length with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
