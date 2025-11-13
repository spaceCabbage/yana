"""
Note management and operations.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import frontmatter

from src.utils import NoteError


@dataclass(slots=True, frozen=True)
class Note:
    """Represents a markdown note with frontmatter."""

    path: Path
    title: str
    category: str
    tags: list[str]
    content: str
    created_at: datetime
    modified_at: datetime

    @classmethod
    def from_file(cls, path: Path) -> "Note":
        """
        Load a note from a markdown file with YAML frontmatter.

        Expected frontmatter format:
        ---
        category: work-projects
        tags: [meeting, action-items]
        created: 2025-01-13T10:30:00
        modified: 2025-01-13T15:45:00
        ---
        """
        try:
            post = frontmatter.load(path)
        except Exception as e:
            raise NoteError(f"Failed to parse frontmatter in {path}: {e}")

        # Extract metadata
        metadata = post.metadata
        category = metadata.get("category", "uncategorized")
        tags = metadata.get("tags", [])
        created_str = metadata.get("created")
        modified_str = metadata.get("modified")

        # Parse timestamps
        try:
            created_at = (
                datetime.fromisoformat(created_str)
                if created_str
                else datetime.fromtimestamp(path.stat().st_ctime)
            )
            modified_at = (
                datetime.fromisoformat(modified_str)
                if modified_str
                else datetime.fromtimestamp(path.stat().st_mtime)
            )
        except Exception as e:
            raise NoteError(f"Invalid timestamp in {path}: {e}")

        # Extract title from filename
        title = path.stem.replace("-", " ").title()

        return cls(
            path=path,
            title=title,
            category=category,
            tags=tags,
            content=post.content,
            created_at=created_at,
            modified_at=modified_at,
        )

    def save(self) -> None:
        """Save note to file with updated frontmatter."""
        post = frontmatter.Post(
            self.content,
            category=self.category,
            tags=self.tags,
            created=self.created_at.isoformat(),
            modified=datetime.now().isoformat(),
        )

        try:
            with open(self.path, "w") as f:
                f.write(frontmatter.dumps(post))
        except Exception as e:
            raise NoteError(f"Failed to save note {self.path}: {e}")


class NoteManager:
    """Manages note operations and queries."""

    def __init__(self, notes_dir: Path) -> None:
        self.notes_dir = notes_dir
        self._cache: Optional[list[Note]] = None

    def list_all_notes(self, invalidate_cache: bool = False) -> list[Note]:
        """
        List all markdown notes in the notes directory.

        Args:
            invalidate_cache: Force reload from disk

        Returns:
            List of Note objects sorted by modified time (newest first)
        """
        if self._cache is not None and not invalidate_cache:
            return self._cache

        notes = []
        for md_file in self.notes_dir.rglob("*.md"):
            try:
                note = Note.from_file(md_file)
                notes.append(note)
            except NoteError as e:
                # Skip files that can't be parsed
                print(f"Warning: {e}")
                continue

        # Sort by modified time (newest first)
        notes.sort(key=lambda n: n.modified_at, reverse=True)

        self._cache = notes
        return notes

    def get_note(self, path: Path) -> Note:
        """Load a single note by path."""
        if not path.exists():
            raise NoteError(f"Note not found: {path}")
        return Note.from_file(path)

    def create_note(
        self, title: str, category: str, tags: Optional[list[str]] = None
    ) -> Note:
        """
        Create a new note with frontmatter.

        Args:
            title: Note title (used for filename)
            category: Flat category name (e.g., "work-projects")
            tags: Optional list of tags

        Returns:
            Newly created Note object
        """
        # Generate filename from title
        filename = title.lower().replace(" ", "-") + ".md"
        note_path = self.notes_dir / filename

        # Check if note already exists
        if note_path.exists():
            raise NoteError(f"Note already exists: {note_path}")

        # Create frontmatter
        now = datetime.now()
        post = frontmatter.Post(
            f"# {title}\n\n",
            category=category,
            tags=tags or [],
            created=now.isoformat(),
            modified=now.isoformat(),
        )

        # Write file
        try:
            with open(note_path, "w") as f:
                f.write(frontmatter.dumps(post))
        except Exception as e:
            raise NoteError(f"Failed to create note: {e}")

        # Invalidate cache
        self._cache = None

        return Note.from_file(note_path)

    def filter_by_category(self, category: str) -> list[Note]:
        """Filter notes by category."""
        all_notes = self.list_all_notes()
        return [note for note in all_notes if note.category == category]

    def filter_by_tags(self, tags: list[str]) -> list[Note]:
        """Filter notes by tags (AND logic - note must have all tags)."""
        all_notes = self.list_all_notes()
        return [note for note in all_notes if all(tag in note.tags for tag in tags)]

    def search_by_title(self, query: str) -> list[Note]:
        """Search notes by title (case-insensitive)."""
        all_notes = self.list_all_notes()
        query_lower = query.lower()
        return [note for note in all_notes if query_lower in note.title.lower()]

    def get_last_edited_note(self) -> Optional[Note]:
        """Get the most recently edited note."""
        notes = self.list_all_notes()
        return notes[0] if notes else None

    def get_daily_note(self, date: Optional[datetime] = None) -> Note:
        """
        Get or create a daily journal note.

        Args:
            date: Date for the journal entry (default: today)

        Returns:
            Note object for the daily journal
        """
        if date is None:
            date = datetime.now()

        # Create journal directory if needed
        journal_dir = self.notes_dir / "journal"
        journal_dir.mkdir(exist_ok=True)

        # Generate filename: YYYY-MM-DD.md
        filename = date.strftime("%Y-%m-%d.md")
        note_path = journal_dir / filename

        # If note exists, load it
        if note_path.exists():
            return Note.from_file(note_path)

        # Create new daily note
        title = date.strftime("%Y-%m-%d")
        post = frontmatter.Post(
            f"# {title}\n\n## Notes\n\n",
            category="journal",
            tags=["journal", "daily"],
            created=date.isoformat(),
            modified=date.isoformat(),
        )

        # Write file
        try:
            with open(note_path, "w") as f:
                f.write(frontmatter.dumps(post))
        except Exception as e:
            raise NoteError(f"Failed to create daily note: {e}")

        return Note.from_file(note_path)

    def update_note(
        self,
        note: Note,
        content: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Note:
        """
        Update a note's content or frontmatter.

        Since Note is frozen, this creates an updated frontmatter file.

        Args:
            note: The note to update
            content: New content (if None, keeps existing)
            category: New category (if None, keeps existing)
            tags: New tags (if None, keeps existing)

        Returns:
            Updated Note object (reloaded from file)

        Raises:
            NoteError: If file doesn't exist or save fails
        """
        if not note.path.exists():
            raise NoteError(f"Note not found: {note.path}")

        # Use provided values or keep existing
        updated_content = content if content is not None else note.content
        updated_category = category if category is not None else note.category
        updated_tags = tags if tags is not None else note.tags

        # Create updated frontmatter post
        post = frontmatter.Post(
            updated_content,
            category=updated_category,
            tags=updated_tags,
            created=note.created_at.isoformat(),
            modified=datetime.now().isoformat(),
        )

        # Write to file
        try:
            with open(note.path, "w") as f:
                f.write(frontmatter.dumps(post))
        except Exception as e:
            raise NoteError(f"Failed to update note {note.path}: {e}")

        # Invalidate cache
        self._cache = None

        # Return updated note
        return Note.from_file(note.path)

    def delete_note(self, path: Path) -> None:
        """
        Delete a note file.

        Args:
            path: Path to the note file to delete

        Raises:
            NoteError: If file doesn't exist or deletion fails
        """
        if not path.exists():
            raise NoteError(f"Note not found: {path}")

        if not path.is_file():
            raise NoteError(f"Not a file: {path}")

        try:
            path.unlink()
        except Exception as e:
            raise NoteError(f"Failed to delete note {path}: {e}")

        # Invalidate cache
        self._cache = None
