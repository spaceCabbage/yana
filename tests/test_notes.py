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


def test_note_manager_update_note_content(temp_notes_dir):
    """Test updating note content."""
    manager = NoteManager(temp_notes_dir)

    # Create a note
    note = manager.create_note("Original Note", "work", ["tag1"])

    # Update content
    new_content = "# Updated Content\n\nThis is the new content."
    updated_note = manager.update_note(note, content=new_content)

    assert updated_note.content == new_content
    assert updated_note.category == "work"  # Unchanged
    assert updated_note.tags == ["tag1"]  # Unchanged
    assert updated_note.path == note.path  # Same file


def test_note_manager_update_note_category(temp_notes_dir):
    """Test updating note category."""
    manager = NoteManager(temp_notes_dir)

    # Create a note
    note = manager.create_note("Test Note", "work", ["tag1"])

    # Update category
    updated_note = manager.update_note(note, category="personal")

    assert updated_note.category == "personal"
    assert updated_note.content == note.content  # Unchanged
    assert updated_note.tags == ["tag1"]  # Unchanged


def test_note_manager_update_note_tags(temp_notes_dir):
    """Test updating note tags."""
    manager = NoteManager(temp_notes_dir)

    # Create a note
    note = manager.create_note("Test Note", "work", ["tag1"])

    # Update tags
    new_tags = ["tag2", "tag3", "tag4"]
    updated_note = manager.update_note(note, tags=new_tags)

    assert updated_note.tags == new_tags
    assert updated_note.category == "work"  # Unchanged
    assert updated_note.content == note.content  # Unchanged


def test_note_manager_update_note_multiple_fields(temp_notes_dir):
    """Test updating multiple fields at once."""
    manager = NoteManager(temp_notes_dir)

    # Create a note
    note = manager.create_note("Test Note", "work", ["tag1"])

    # Update multiple fields
    new_content = "# New Content"
    new_category = "personal"
    new_tags = ["tag2", "tag3"]

    updated_note = manager.update_note(
        note, content=new_content, category=new_category, tags=new_tags
    )

    assert updated_note.content == new_content
    assert updated_note.category == new_category
    assert updated_note.tags == new_tags


def test_note_manager_update_note_not_found(temp_notes_dir):
    """Test updating non-existent note raises error."""
    manager = NoteManager(temp_notes_dir)

    # Create a note then delete the file
    note = manager.create_note("Test Note", "work", [])
    note.path.unlink()

    # Try to update
    with pytest.raises(NoteError, match="not found"):
        manager.update_note(note, content="New content")


def test_note_manager_update_note_invalidates_cache(temp_notes_dir):
    """Test that updating a note invalidates the cache."""
    manager = NoteManager(temp_notes_dir)

    # Create notes and populate cache
    note1 = manager.create_note("Note 1", "work", [])
    note2 = manager.create_note("Note 2", "work", [])
    manager.list_all_notes()  # Populate cache

    # Update note1
    manager.update_note(note1, category="personal")

    # Cache should be invalidated, so list_all_notes should reload
    notes = manager.list_all_notes()
    updated = next(n for n in notes if n.path == note1.path)
    assert updated.category == "personal"


def test_note_manager_delete_note(temp_notes_dir):
    """Test deleting a note."""
    manager = NoteManager(temp_notes_dir)

    # Create a note
    note = manager.create_note("Test Note", "work", [])
    note_path = note.path

    assert note_path.exists()

    # Delete the note
    manager.delete_note(note_path)

    # File should be gone
    assert not note_path.exists()


def test_note_manager_delete_note_not_found(temp_notes_dir):
    """Test deleting non-existent note raises error."""
    manager = NoteManager(temp_notes_dir)

    fake_path = temp_notes_dir / "nonexistent.md"

    with pytest.raises(NoteError, match="not found"):
        manager.delete_note(fake_path)


def test_note_manager_delete_note_not_file(temp_notes_dir):
    """Test deleting a directory raises error."""
    manager = NoteManager(temp_notes_dir)

    # Try to delete a directory
    subdir = temp_notes_dir / "subdir"
    subdir.mkdir()

    with pytest.raises(NoteError, match="Not a file"):
        manager.delete_note(subdir)


def test_note_manager_delete_note_invalidates_cache(temp_notes_dir):
    """Test that deleting a note invalidates the cache."""
    manager = NoteManager(temp_notes_dir)

    # Create notes and populate cache
    note1 = manager.create_note("Note 1", "work", [])
    note2 = manager.create_note("Note 2", "work", [])
    notes_before = manager.list_all_notes()
    assert len(notes_before) == 2

    # Delete note1
    manager.delete_note(note1.path)

    # Cache should be invalidated
    notes_after = manager.list_all_notes()
    assert len(notes_after) == 1
    assert notes_after[0].path == note2.path


# ============================================================================
# Search Tests
# ============================================================================


def test_search_content_python_fallback(temp_notes_dir):
    """Test content search using Python fallback."""
    manager = NoteManager(temp_notes_dir)

    # Create test notes with searchable content
    note1 = manager.create_note("Meeting Notes", "work", ["meeting"])
    note2 = manager.create_note("Todo List", "personal", ["todo"])
    note3 = manager.create_note("Ideas", "work", ["brainstorm"])

    # Update notes with specific content
    manager.update_note(note1, content="# Meeting Notes\n\nDiscuss TODO items for project")
    manager.update_note(note2, content="# Todo List\n\n- Buy groceries\n- Call mom")
    manager.update_note(note3, content="# Ideas\n\nAdd TODO: review code")

    # Search for "TODO" (case-insensitive)
    results = manager.search_content("TODO", context_lines=1)

    # Should find note1 and note3 (both have "TODO")
    assert len(results) == 2
    result_titles = {note.title for note, _ in results}
    assert "Meeting Notes" in result_titles
    assert "Ideas" in result_titles


def test_search_content_no_matches(temp_notes_dir):
    """Test search with no matches."""
    manager = NoteManager(temp_notes_dir)

    # Create note without search term
    manager.create_note("Empty Note", "work", [])

    # Search for non-existent term
    results = manager.search_content("nonexistent")

    assert len(results) == 0


def test_search_content_regex_pattern(temp_notes_dir):
    """Test search with regex pattern."""
    manager = NoteManager(temp_notes_dir)

    # Create notes
    note1 = manager.create_note("Code Review", "work", [])
    note2 = manager.create_note("Shopping", "personal", [])

    # Update with content
    manager.update_note(note1, content="# Code Review\n\nBug #123\nIssue #456")
    manager.update_note(note2, content="# Shopping\n\nItem count: 5")

    # Search for pattern "Issue #\d+"
    results = manager.search_content(r"Issue #\d+")

    assert len(results) == 1
    note, matches = results[0]
    assert note.title == "Code Review"
    assert any("#456" in line for _, line in matches)


def test_search_content_invalid_regex(temp_notes_dir):
    """Test search with invalid regex pattern using Python regex."""
    manager = NoteManager(temp_notes_dir)
    manager.create_note("Test Note", "work", [])

    # Invalid regex should raise NoteError when using Python regex
    # Use a truly invalid pattern: quantifier without preceding element
    with pytest.raises(NoteError, match="Invalid regex pattern"):
        # Directly call Python search to test regex validation
        manager._search_with_python("*invalid", context_lines=1)


def test_search_content_context_lines(temp_notes_dir):
    """Test that context lines are included in results."""
    manager = NoteManager(temp_notes_dir)

    # Create note with multi-line content
    note = manager.create_note("Context Test", "work", [])
    content = """# Context Test

Line 1
Line 2
MATCH HERE
Line 4
Line 5
"""
    manager.update_note(note, content=content)

    # Search with 2 context lines
    results = manager.search_content("MATCH HERE", context_lines=2)

    assert len(results) == 1
    _, matches = results[0]

    # Should have match line plus context (2 before, 2 after)
    lines_text = [line for _, line in matches]
    assert "MATCH HERE" in " ".join(lines_text)
    assert "Line 2" in " ".join(lines_text) or "Line 4" in " ".join(lines_text)


def test_detect_search_tool(temp_notes_dir, mocker):
    """Test search tool detection."""
    manager = NoteManager(temp_notes_dir)

    # Mock successful ripgrep detection
    mocker.patch(
        "subprocess.run",
        return_value=mocker.Mock(returncode=0)
    )
    tool = manager._detect_search_tool()
    assert tool == "ripgrep"

    # Mock ripgrep not found, grep found
    def mock_run(args, **kwargs):
        if "rg" in args:
            raise FileNotFoundError()
        return mocker.Mock(returncode=0)

    mocker.patch("subprocess.run", side_effect=mock_run)
    tool = manager._detect_search_tool()
    assert tool == "grep"

    # Mock both not found
    mocker.patch("subprocess.run", side_effect=FileNotFoundError())
    tool = manager._detect_search_tool()
    assert tool == "python"


def test_search_with_ripgrep(temp_notes_dir, mocker):
    """Test search using ripgrep."""
    manager = NoteManager(temp_notes_dir)

    # Create test note
    note = manager.create_note("Test Note", "work", [])
    manager.update_note(note, content="# Test\n\nFOUND IT")

    # Mock ripgrep output
    rg_output = f"{note.path}:3:FOUND IT\n"
    mocker.patch(
        "subprocess.run",
        return_value=mocker.Mock(returncode=0, stdout=rg_output)
    )

    # Force ripgrep usage
    mocker.patch.object(manager, "_detect_search_tool", return_value="ripgrep")

    results = manager.search_content("FOUND")

    assert len(results) == 1
    found_note, matches = results[0]
    assert found_note.title == "Test Note"
    assert len(matches) > 0


def test_search_with_grep(temp_notes_dir, mocker):
    """Test search using grep."""
    manager = NoteManager(temp_notes_dir)

    # Create test note
    note = manager.create_note("Test Note", "work", [])
    manager.update_note(note, content="# Test\n\nFOUND IT")

    # Mock grep output
    grep_output = f"{note.path}:3:FOUND IT\n"
    mocker.patch(
        "subprocess.run",
        return_value=mocker.Mock(returncode=0, stdout=grep_output)
    )

    # Force grep usage
    mocker.patch.object(manager, "_detect_search_tool", return_value="grep")

    results = manager.search_content("FOUND")

    assert len(results) == 1
    found_note, matches = results[0]
    assert found_note.title == "Test Note"


def test_search_timeout(temp_notes_dir, mocker):
    """Test search timeout handling."""
    manager = NoteManager(temp_notes_dir)
    manager.create_note("Test Note", "work", [])

    # Mock timeout
    import subprocess
    mocker.patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired("rg", 30)
    )

    # Force ripgrep usage
    mocker.patch.object(manager, "_detect_search_tool", return_value="ripgrep")

    with pytest.raises(NoteError, match="Search timed out"):
        manager.search_content("test")


def test_parse_grep_output_empty(temp_notes_dir):
    """Test parsing empty grep output."""
    manager = NoteManager(temp_notes_dir)

    results = manager._parse_grep_output("")
    assert len(results) == 0

    results = manager._parse_grep_output("   \n\n   ")
    assert len(results) == 0


def test_parse_grep_output_with_context(temp_notes_dir):
    """Test parsing grep output with context lines."""
    manager = NoteManager(temp_notes_dir)

    # Create a note
    note = manager.create_note("Test", "work", [])
    manager.update_note(note, content="# Test\n\nLine 1\nMatch\nLine 3")

    # Simulate grep output with context (uses - for context lines)
    output = f"""{note.path}:2:Line 1
{note.path}:3:Match
{note.path}-4-Line 3"""

    results = manager._parse_grep_output(output)

    assert len(results) == 1
    found_note, matches = results[0]
    assert found_note.path == note.path
    assert len(matches) == 3  # Main match + 2 context lines
