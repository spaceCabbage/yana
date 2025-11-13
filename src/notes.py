"""
Note management and operations.
"""

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import frontmatter

from src.utils import NoteError, logger


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

    def search_content(
        self, query: str, context_lines: int = 2
    ) -> list[tuple[Note, list[tuple[int, str]]]]:
        """
        Search note content for a query string.

        Uses ripgrep (rg) if available, falls back to grep, then Python regex.

        Args:
            query: Search query (treated as regex)
            context_lines: Number of context lines to show around matches

        Returns:
            List of (Note, matches) tuples where matches is a list of (line_number, line_text)

        Raises:
            NoteError: If search fails
        """
        logger.debug(f"Searching for '{query}' in notes directory: {self.notes_dir}")

        # Check which search tool is available
        search_tool = self._detect_search_tool()
        logger.debug(f"Using search tool: {search_tool}")

        if search_tool == "ripgrep":
            return self._search_with_ripgrep(query, context_lines)
        elif search_tool == "grep":
            return self._search_with_grep(query, context_lines)
        else:
            return self._search_with_python(query, context_lines)

    def _detect_search_tool(self) -> str:
        """Detect which search tool is available (ripgrep > grep > python)."""
        # Try ripgrep
        try:
            result = subprocess.run(
                ["rg", "--version"],
                capture_output=True,
                timeout=2,
            )
            if result.returncode == 0:
                logger.debug("ripgrep (rg) detected")
                return "ripgrep"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Try grep
        try:
            result = subprocess.run(
                ["grep", "--version"],
                capture_output=True,
                timeout=2,
            )
            if result.returncode == 0:
                logger.debug("grep detected")
                return "grep"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        logger.debug("No external search tool found, using Python regex")
        return "python"

    def _search_with_ripgrep(
        self, query: str, context_lines: int
    ) -> list[tuple[Note, list[tuple[int, str]]]]:
        """Search using ripgrep (rg)."""
        try:
            # Run ripgrep with line numbers and context
            result = subprocess.run(
                [
                    "rg",
                    "--line-number",
                    "--with-filename",
                    "--no-heading",
                    "--color=never",
                    f"--context={context_lines}",
                    "--type=md",
                    query,
                    str(self.notes_dir),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Parse results
            return self._parse_grep_output(result.stdout)

        except subprocess.TimeoutExpired:
            raise NoteError("Search timed out (>30s)")
        except Exception as e:
            logger.warning(f"ripgrep search failed: {e}, falling back to Python")
            return self._search_with_python(query, context_lines)

    def _search_with_grep(
        self, query: str, context_lines: int
    ) -> list[tuple[Note, list[tuple[int, str]]]]:
        """Search using grep."""
        try:
            # Run grep with line numbers and context
            result = subprocess.run(
                [
                    "grep",
                    "-r",
                    "-n",
                    "--color=never",
                    f"-C{context_lines}",
                    "--include=*.md",
                    query,
                    str(self.notes_dir),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Parse results
            return self._parse_grep_output(result.stdout)

        except subprocess.TimeoutExpired:
            raise NoteError("Search timed out (>30s)")
        except Exception as e:
            logger.warning(f"grep search failed: {e}, falling back to Python")
            return self._search_with_python(query, context_lines)

    def _search_with_python(
        self, query: str, context_lines: int
    ) -> list[tuple[Note, list[tuple[int, str]]]]:
        """Search using Python regex (fallback)."""
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error as e:
            raise NoteError(f"Invalid regex pattern: {e}")

        results: list[tuple[Note, list[tuple[int, str]]]] = []

        for md_file in self.notes_dir.rglob("*.md"):
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                matches: list[tuple[int, str]] = []
                matched_lines = set()  # Track which lines we've already added

                for i, line in enumerate(lines, start=1):
                    if pattern.search(line):
                        # Add match with context
                        # Calculate the range of lines to include (1-indexed)
                        start_line = max(1, i - context_lines)
                        end_line = min(len(lines), i + context_lines)

                        # Add all lines in range (avoiding duplicates)
                        for line_num in range(start_line, end_line + 1):
                            if line_num not in matched_lines:
                                matched_lines.add(line_num)
                                matches.append((line_num, lines[line_num - 1].rstrip()))

                if matches:
                    note = Note.from_file(md_file)
                    results.append((note, matches))

            except Exception as e:
                logger.warning(f"Failed to search {md_file}: {e}")
                continue

        return results

    def _parse_grep_output(
        self, output: str
    ) -> list[tuple[Note, list[tuple[int, str]]]]:
        """Parse grep/ripgrep output into structured results."""
        if not output.strip():
            return []

        results: dict[Path, list[tuple[int, str]]] = {}

        for line in output.split("\n"):
            if not line.strip():
                continue

            # Parse format: path:line_number:content or path-line_number-content (context)
            # Try colon separator first (match lines)
            if ":" in line:
                # Find second colon (first is after path, second is after line number)
                first_colon = line.find(":")
                second_colon = line.find(":", first_colon + 1)

                if second_colon > 0:
                    file_path = Path(line[:first_colon])
                    try:
                        line_number = int(line[first_colon + 1:second_colon])
                        line_content = line[second_colon + 1:]
                    except ValueError:
                        continue
                else:
                    continue
            # Try dash separator (context lines)
            elif "-" in line:
                # Find the FIRST dash after the file path
                # The file path ends with .md, so find that first
                md_ext = line.rfind(".md")
                if md_ext == -1:
                    continue

                # Find first dash after .md
                first_dash = line.find("-", md_ext)
                if first_dash == -1:
                    continue

                # Find second dash
                second_dash = line.find("-", first_dash + 1)
                if second_dash == -1:
                    continue

                file_path = Path(line[:first_dash])
                try:
                    line_number = int(line[first_dash + 1:second_dash])
                    line_content = line[second_dash + 1:]
                except ValueError:
                    continue
            else:
                continue

            if file_path not in results:
                results[file_path] = []

            results[file_path].append((line_number, line_content))

        # Convert to Note objects
        final_results: list[tuple[Note, list[tuple[int, str]]]] = []
        for file_path, matches in results.items():
            try:
                note = Note.from_file(file_path)
                final_results.append((note, matches))
            except NoteError:
                logger.warning(f"Failed to load note: {file_path}")
                continue

        return final_results
