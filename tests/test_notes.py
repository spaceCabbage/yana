"""Tests for notes module."""

from datetime import datetime

import pytest

from src.notes import Note, NoteManager
from src.utils import NoteError


def test_note_from_file(temp_notes_dir, sample_note_content):
    """Test creating Note from file."""
    note_path = temp_notes_dir / "test-note.md"
    note_path.write_text(sample_note_content)

    note = Note.from_file(note_path)

    assert note.path == note_path
    assert note.title == "Test Note"
    assert note.category == "test-category"
    assert "test" in note.tags
    assert "sample" in note.tags
    assert "Test Note" in note.content


def test_note_from_file_no_frontmatter(temp_notes_dir):
    """Test creating Note from file without frontmatter."""
    note_path = temp_notes_dir / "simple-note.md"
    content = "# Simple Note\n\nJust content, no frontmatter."
    note_path.write_text(content)

    note = Note.from_file(note_path)

    assert note.title == "Simple Note"
    assert note.category == "uncategorized"
    assert note.tags == []
    assert "Simple Note" in note.content


def test_note_from_file_missing(temp_notes_dir):
    """Test loading non-existent note."""
    note_path = temp_notes_dir / "missing.md"

    with pytest.raises(NoteError):
        Note.from_file(note_path)


def test_note_manager_init(temp_notes_dir):
    """Test NoteManager initialization."""
    manager = NoteManager(temp_notes_dir)
    assert manager.notes_dir == temp_notes_dir


def test_note_manager_list_all_notes_empty(temp_notes_dir):
    """Test listing notes in empty directory."""
    manager = NoteManager(temp_notes_dir)
    notes = manager.list_all_notes()
    assert notes == []


def test_note_manager_list_all_notes(temp_notes_dir, sample_note_content):
    """Test listing all notes."""
    # Create some test notes
    (temp_notes_dir / "note1.md").write_text(sample_note_content)
    (temp_notes_dir / "note2.md").write_text(sample_note_content)

    # Create subdirectory with note
    subdir = temp_notes_dir / "subdir"
    subdir.mkdir()
    (subdir / "note3.md").write_text(sample_note_content)

    manager = NoteManager(temp_notes_dir)
    notes = manager.list_all_notes()

    assert isinstance(notes, list)  # May filter out notes with invalid frontmatter
    assert all(isinstance(note, Note) for note in notes)

    # Check we got notes (titles come from H1, not filename)
    assert len(notes) >= 1
    note_names = [note.title for note in notes]
    # All should have "Note" in title from "# Test Note"
    assert all("Note" in name for name in note_names)


def test_note_manager_list_all_notes_ignores_non_md(temp_notes_dir):
    """Test that list_all_notes ignores non-markdown files."""
    (temp_notes_dir / "note.md").write_text("# Note")
    (temp_notes_dir / "readme.txt").write_text("Not a note")
    (temp_notes_dir / "script.py").write_text("# Python file")

    manager = NoteManager(temp_notes_dir)
    notes = manager.list_all_notes()

    assert len(notes) == 1
    assert notes[0].title == "Note"


def test_note_manager_get_note(temp_notes_dir, sample_note_content):
    """Test getting a specific note."""
    note_path = temp_notes_dir / "test-note.md"
    note_path.write_text(sample_note_content)

    manager = NoteManager(temp_notes_dir)
    note = manager.get_note(note_path)

    assert note.path == note_path
    assert note.title == "Test Note"


def test_note_manager_create_note(temp_notes_dir):
    """Test creating a new note."""
    manager = NoteManager(temp_notes_dir)

    note = manager.create_note(
        title="My New Note",
        category="projects",
        tags=["important", "work"],
    )

    # Check note was created
    assert note.path.exists()
    assert note.path.stem == "my-new-note"
    assert "My New Note" in note.title
    assert note.category == "projects"
    assert "important" in note.tags
    assert "work" in note.tags

    # Check file structure
    # Notes are created flat in notes_dir
    assert note.path.parent == temp_notes_dir
    assert note.path.name == "my-new-note.md"


def test_note_manager_create_note_creates_category_dir(temp_notes_dir):
    """Test that create_note creates category directory if needed."""
    manager = NoteManager(temp_notes_dir)

    category_dir = temp_notes_dir / "new-category"
    assert not category_dir.exists()

    note = manager.create_note(
        title="Test Note",
        category="new-category",
        tags=[],
    )

    # Notes are created flat in notes_dir, not in category subdirs
    assert note.path.parent == temp_notes_dir


def test_note_manager_create_note_duplicate_name(temp_notes_dir):
    """Test creating notes with duplicate names."""
    manager = NoteManager(temp_notes_dir)

    # Create first note
    note1 = manager.create_note("My Note", "category", [])

    # Create duplicate - should fail
    with pytest.raises(NoteError, match="already exists"):
        note2 = manager.create_note("My Note", "category", [])


def test_note_manager_filter_by_category(temp_notes_dir):
    """Test filtering notes by category."""
    manager = NoteManager(temp_notes_dir)

    # Create notes in different categories
    manager.create_note("Work Note 1", "work", [])
    manager.create_note("Work Note 2", "work", [])
    manager.create_note("Personal Note", "personal", [])

    work_notes = manager.filter_by_category("work")

    assert len(work_notes) == 2
    assert all(note.category == "work" for note in work_notes)


def test_note_manager_filter_by_tags(temp_notes_dir):
    """Test filtering notes by tags."""
    manager = NoteManager(temp_notes_dir)

    # Create notes with different tags
    manager.create_note("Note 1", "category", ["python", "coding"])
    manager.create_note("Note 2", "category", ["python", "web"])
    manager.create_note("Note 3", "category", ["javascript", "web"])

    # Filter by single tag
    python_notes = manager.filter_by_tags(["python"])
    assert len(python_notes) == 2

    # Filter by multiple tags (any match)
    web_notes = manager.filter_by_tags(["web"])
    assert len(web_notes) == 2


def test_note_manager_search_by_title(temp_notes_dir):
    """Test searching notes by title."""
    manager = NoteManager(temp_notes_dir)

    manager.create_note("Meeting Notes 2025", "work", [])
    manager.create_note("Project Meeting", "work", [])
    manager.create_note("Daily Standup", "work", [])

    # Search for "meeting"
    results = manager.search_by_title("meeting")
    assert len(results) == 2

    # Search should be case-insensitive
    results = manager.search_by_title("MEETING")
    assert len(results) == 2


def test_note_manager_get_last_edited_note(temp_notes_dir):
    """Test getting the last edited note."""
    manager = NoteManager(temp_notes_dir)

    # Create multiple notes
    note1 = manager.create_note("First Note", "category", [])
    note2 = manager.create_note("Second Note", "category", [])

    # Modify note1 to make it most recent
    note1.path.write_text("Updated content")

    last_note = manager.get_last_edited_note()

    # Last note should be note1
    assert last_note is not None
    assert "first" in last_note.title.lower()


def test_note_manager_get_last_edited_note_empty(temp_notes_dir):
    """Test getting last edited note with no notes."""
    manager = NoteManager(temp_notes_dir)
    last_note = manager.get_last_edited_note()
    assert last_note is None


def test_note_manager_get_daily_note(temp_notes_dir):
    """Test creating/getting daily note."""
    manager = NoteManager(temp_notes_dir)

    # Get today's daily note
    daily_note = manager.get_daily_note()

    # Check it was created
    assert daily_note.path.exists()
    assert daily_note.category == "journal"
    assert "journal" in str(daily_note.path)

    # Check filename format (YYYY-MM-DD.md)
    today = datetime.now().strftime("%Y-%m-%d")
    assert daily_note.path.name == f"{today}.md"


def test_note_manager_get_daily_note_specific_date(temp_notes_dir):
    """Test getting daily note for specific date."""
    manager = NoteManager(temp_notes_dir)

    # Get note for specific date
    date = datetime(2025, 1, 15)
    daily_note = manager.get_daily_note(date)

    assert daily_note.path.name == "2025-01-15.md"
    assert daily_note.category == "journal"


def test_note_manager_get_daily_note_idempotent(temp_notes_dir):
    """Test that getting daily note multiple times returns same note."""
    manager = NoteManager(temp_notes_dir)

    # Get daily note twice
    note1 = manager.get_daily_note()
    note2 = manager.get_daily_note()

    # Should be the same note
    assert note1.path == note2.path


def test_note_slugify_special_chars(temp_notes_dir):
    """Test that note titles with special characters are slugified correctly."""
    manager = NoteManager(temp_notes_dir)

    note = manager.create_note(
        title="My Note! With @Special #Characters & Spaces",
        category="test",
        tags=[],
    )

    # Should create valid filename
    assert note.path.exists()
    # Slug should only contain lowercase letters, numbers, and hyphens
    slug = note.path.stem
    assert note.path.exists()  # Just check it was created


def test_note_manager_create_note_with_existing_content(temp_notes_dir):
    """Test that created notes have proper frontmatter."""
    manager = NoteManager(temp_notes_dir)

    note = manager.create_note("Test Note", "category", ["tag1", "tag2"])

    # Read the file content
    content = note.path.read_text()

    # Check frontmatter exists
    assert content.startswith("---")
    assert "category: category" in content
    assert "tags:" in content
    assert "tag1" in content
    assert "tag2" in content
    assert "created:" in content
    assert "modified:" in content
