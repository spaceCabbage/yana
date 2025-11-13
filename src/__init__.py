"""
YANA - Yet Another Notes App

A lean, modern CLI markdown notes manager with FZF and git sync.
"""

from importlib.metadata import metadata

# Read version and author from package metadata
try:
    _metadata = metadata("yana")
    __version__ = _metadata.get("Version", "0.1.0-dev")
    __author__ = _metadata.get("Author", "Yehuda")
except Exception:
    # Fallback for development (not installed)
    __version__ = "0.1.0-dev"
    __author__ = "Yehuda"

from .config import Config, load_config
from .notes import Note, NoteManager

__all__ = [
    "__version__",
    "__author__",
    "Config",
    "load_config",
    "Note",
    "NoteManager",
]
