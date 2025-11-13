"""Tests for FZF module."""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.fzf import NoteFuzzyFinder
from src.notes import Note
from src.utils import FzfError


@pytest.fixture
def sample_notes(temp_notes_dir):
    """Create sample notes for testing."""
    notes = []

    # Create notes with different categories and tags
    for i in range(3):
        note = Note(
            path=temp_notes_dir / f"note{i}.md",
            title=f"Note {i}",
            category="work" if i < 2 else "personal",
            tags=["python", "coding"] if i == 0 else ["general"],
            created_at=datetime(2025, 1, 13, 10, 0, 0),
            modified_at=datetime(2025, 1, 13, 10, 0, 0),
            content=f"# Note {i}\n\nContent here.",
        )
        notes.append(note)

    return notes


def test_note_fuzzy_finder_init(sample_notes):
    """Test NoteFuzzyFinder initialization."""
    finder = NoteFuzzyFinder(
        notes=sample_notes,
        preview_enabled=True,
        preview_command="bat {}",
    )

    assert finder.notes == sample_notes
    assert finder.preview_enabled is True
    assert finder.preview_command == "bat {}"


def test_format_note_for_fzf(sample_notes):
    """Test formatting note for FZF display."""
    finder = NoteFuzzyFinder(sample_notes)

    note = sample_notes[0]
    formatted = finder.format_note_for_fzf(note)

    # Check format: [category] Title | #tags | path
    assert "[work]" in formatted
    assert "Note 0" in formatted
    assert "#python" in formatted
    assert "#coding" in formatted
    assert str(note.path) in formatted


def test_format_note_for_fzf_no_tags(temp_notes_dir):
    """Test formatting note without tags."""
    note = Note(
        path=temp_notes_dir / "note.md",
        title="Simple Note",
        category="general",
        tags=[],
        created_at=datetime(2025, 1, 13, 10, 0, 0),
        modified_at=datetime(2025, 1, 13, 10, 0, 0),
        content="Content",
    )

    finder = NoteFuzzyFinder([note])
    formatted = finder.format_note_for_fzf(note)

    assert "[general]" in formatted
    assert "Simple Note" in formatted
    # Should have empty tags section
    assert " |  | " in formatted


def test_parse_selection(sample_notes):
    """Test parsing FZF selection back to Note."""
    finder = NoteFuzzyFinder(sample_notes)

    note = sample_notes[0]
    formatted = finder.format_note_for_fzf(note)

    parsed_note = finder.parse_selection(formatted)

    assert parsed_note is not None
    assert parsed_note.path == note.path
    assert parsed_note.title == note.title


def test_parse_selection_invalid():
    """Test parsing invalid selection."""
    finder = NoteFuzzyFinder([])

    parsed_note = finder.parse_selection("invalid | format | string")

    assert parsed_note is None


def test_get_preview_command_enabled():
    """Test get_preview_command when enabled."""
    finder = NoteFuzzyFinder([], preview_enabled=True, preview_command="cat {}")

    preview_cmd = finder._get_preview_command()

    assert preview_cmd == "cat {}"


def test_get_preview_command_disabled():
    """Test get_preview_command when disabled."""
    finder = NoteFuzzyFinder([], preview_enabled=False)

    preview_cmd = finder._get_preview_command()

    assert preview_cmd is None


@patch("shutil.which")
def test_get_preview_command_bat_fallback(mock_which):
    """Test preview command falls back to cat when bat not available."""
    # Mock bat not being available
    mock_which.return_value = None

    finder = NoteFuzzyFinder(
        [],
        preview_enabled=True,
        preview_command="bat --style=plain {}",
    )

    preview_cmd = finder._get_preview_command()

    # Should fallback to cat
    assert preview_cmd == "cat {}"


@patch("shutil.which")
def test_get_preview_command_bat_available(mock_which):
    """Test preview command uses bat when available."""
    # Mock bat being available
    mock_which.return_value = "/usr/bin/bat"

    finder = NoteFuzzyFinder(
        [],
        preview_enabled=True,
        preview_command="bat --style=plain {}",
    )

    preview_cmd = finder._get_preview_command()

    # Should use bat
    assert "bat" in preview_cmd


@patch("src.fzf.iterfzf")
def test_select_note(mock_iterfzf, sample_notes):
    """Test selecting a note with FZF."""
    finder = NoteFuzzyFinder(sample_notes, preview_enabled=False)

    # Mock FZF returning first note
    note = sample_notes[0]
    formatted = finder.format_note_for_fzf(note)
    mock_iterfzf.return_value = formatted

    selected = finder.select()

    assert selected is not None
    assert selected.path == note.path
    mock_iterfzf.assert_called_once()


@patch("src.fzf.iterfzf")
def test_select_note_cancelled(mock_iterfzf, sample_notes):
    """Test FZF selection cancellation."""
    finder = NoteFuzzyFinder(sample_notes, preview_enabled=False)

    # Mock FZF cancellation (returns None)
    mock_iterfzf.return_value = None

    selected = finder.select()

    assert selected is None


@patch("src.fzf.iterfzf")
def test_select_with_category_filter(mock_iterfzf, sample_notes):
    """Test selecting note with category filter."""
    finder = NoteFuzzyFinder(sample_notes, preview_enabled=False)

    # Mock FZF selection
    work_note = sample_notes[0]  # work category
    formatted = finder.format_note_for_fzf(work_note)
    mock_iterfzf.return_value = formatted

    selected = finder.select(category_filter="work")

    assert selected is not None
    assert selected.category == "work"

    # Check that iterfzf was called with only work notes
    call_args = mock_iterfzf.call_args[0][0]
    assert len(call_args) == 2  # Only 2 work notes


def test_select_no_notes_in_category(sample_notes):
    """Test selecting from category with no notes."""
    finder = NoteFuzzyFinder(sample_notes, preview_enabled=False)

    with pytest.raises(FzfError, match="No notes found"):
        finder.select(category_filter="nonexistent")


def test_select_empty_notes_list():
    """Test selecting from empty notes list."""
    finder = NoteFuzzyFinder([], preview_enabled=False)

    with pytest.raises(FzfError, match="No notes found"):
        finder.select()


@patch("src.fzf.iterfzf")
def test_select_multiple(mock_iterfzf, sample_notes):
    """Test selecting multiple notes."""
    finder = NoteFuzzyFinder(sample_notes, preview_enabled=False)

    # Mock FZF returning multiple selections
    note1 = sample_notes[0]
    note2 = sample_notes[1]
    formatted1 = finder.format_note_for_fzf(note1)
    formatted2 = finder.format_note_for_fzf(note2)
    mock_iterfzf.return_value = [formatted1, formatted2]

    selected = finder.select_multiple()

    assert len(selected) == 2
    assert selected[0].path == note1.path
    assert selected[1].path == note2.path


@patch("src.fzf.iterfzf")
def test_select_multiple_cancelled(mock_iterfzf, sample_notes):
    """Test multiple selection cancellation."""
    finder = NoteFuzzyFinder(sample_notes, preview_enabled=False)

    # Mock cancellation
    mock_iterfzf.return_value = None

    selected = finder.select_multiple()

    assert selected == []


@patch("src.fzf.iterfzf")
def test_select_with_preview(mock_iterfzf, sample_notes):
    """Test that preview options are passed to FZF."""
    finder = NoteFuzzyFinder(
        sample_notes,
        preview_enabled=True,
        preview_command="cat {}",
    )

    note = sample_notes[0]
    formatted = finder.format_note_for_fzf(note)
    mock_iterfzf.return_value = formatted

    finder.select()

    # Check that preview options were passed
    call_kwargs = mock_iterfzf.call_args[1]
    assert "preview" in call_kwargs
    assert "preview_window" in call_kwargs


@patch("src.fzf.iterfzf")
def test_select_fzf_error(mock_iterfzf, sample_notes):
    """Test handling FZF errors."""
    finder = NoteFuzzyFinder(sample_notes, preview_enabled=False)

    # Mock FZF error
    mock_iterfzf.side_effect = Exception("FZF crashed")

    with pytest.raises(FzfError, match="FZF error"):
        finder.select()


def test_format_multiple_notes(sample_notes):
    """Test formatting all notes."""
    finder = NoteFuzzyFinder(sample_notes)

    formatted_list = [finder.format_note_for_fzf(note) for note in sample_notes]

    assert len(formatted_list) == 3
    # Each should have the proper format
    for formatted in formatted_list:
        assert "[" in formatted  # category
        assert "|" in formatted  # separators
        assert "#" in formatted or " |  | " in formatted  # tags or empty


def test_parse_selection_path_extraction(sample_notes):
    """Test that parse_selection correctly extracts path."""
    finder = NoteFuzzyFinder(sample_notes)

    # Create a formatted string
    note = sample_notes[0]
    formatted = f"[work] Note 0 | #python #coding | {note.path}"

    parsed = finder.parse_selection(formatted)

    assert parsed is not None
    assert parsed.path == note.path
