"""
Pytest configuration and fixtures.
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_notes_dir():
    """Create a temporary directory for test notes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_note_content():
    """Sample note content with frontmatter."""
    return """---
category: test-category
tags: [test, sample]
created: "2025-01-13T10:00:00"
modified: "2025-01-13T10:00:00"
---

# Test Note

This is a test note with some content.

## Section 1

Some text here.
"""


@pytest.fixture
def config_data(temp_notes_dir):
    """Sample configuration data."""
    return {
        "notes_dir": str(temp_notes_dir),
        "editor": "vim",
        "git_enabled": True,
        "git_commit_interval": 300,
        "watch_enabled": False,
        "fzf_preview": True,
        "fzf_preview_command": "bat --style=plain --color=always {}",
    }
