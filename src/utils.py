"""
Utility functions and custom exceptions.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

# Singleton Rich console
console = Console()

# Logger instance
logger = logging.getLogger("yana")


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


# ============================================================================
# Logging Setup
# ============================================================================


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Set up logging for YANA with file and console handlers.

    Logs are written to ~/.config/yana/yana.log

    Args:
        log_level: Override log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                  If None, uses YANA_LOG_LEVEL env var, defaults to INFO
    """
    # Get log level
    if log_level is None:
        log_level = os.getenv("YANA_LOG_LEVEL", "INFO").upper()

    # Convert to logging level
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Clear any existing handlers
    logger.handlers.clear()

    # Set logger level
    logger.setLevel(numeric_level)

    # Create log directory
    log_dir = Path.home() / ".config" / "yana"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "yana.log"

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_formatter = logging.Formatter("%(levelname)s: %(message)s")

    # File handler (always logs DEBUG and above)
    try:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # If we can't write to log file, continue without file logging
        print(f"Warning: Could not create log file {log_file}: {e}")

    # Console handler (uses configured level)
    # Only show WARNING and above on console by default
    console_handler = logging.StreamHandler()
    console_handler.setLevel(max(numeric_level, logging.WARNING))
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logger.debug(f"Logging initialized at level {log_level}")
    logger.debug(f"Log file: {log_file}")
