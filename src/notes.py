"""
Note management and operations.
"""

import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import frontmatter
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

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

    def filter_by_any_tag(self, tags: list[str]) -> list[Note]:
        """Filter notes by tags (OR logic - note must have at least one tag)."""
        all_notes = self.list_all_notes()
        return [note for note in all_notes if any(tag in note.tags for tag in tags)]

    def filter_by_date_range(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        date_field: str = "modified",
    ) -> list[Note]:
        """
        Filter notes by date range.

        Args:
            start_date: Include notes on or after this date
            end_date: Include notes on or before this date
            date_field: Which date field to filter on ("modified" or "created")

        Returns:
            List of notes within the date range
        """
        all_notes = self.list_all_notes()

        if date_field not in ("modified", "created"):
            raise NoteError(
                f"Invalid date_field: {date_field}. Must be 'modified' or 'created'"
            )

        return [
            note
            for note in all_notes
            if (
                not start_date
                or (note.modified_at if date_field == "modified" else note.created_at)
                >= start_date
            )
            and (
                not end_date
                or (note.modified_at if date_field == "modified" else note.created_at)
                <= end_date
            )
        ]

    def filter_notes(
        self,
        category: Optional[str] = None,
        all_tags: Optional[list[str]] = None,
        any_tags: Optional[list[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        date_field: str = "modified",
    ) -> list[Note]:
        """
        Apply multiple filters to notes.

        Args:
            category: Filter by category
            all_tags: Filter by tags (AND logic - note must have ALL tags)
            any_tags: Filter by tags (OR logic - note must have ANY tag)
            start_date: Include notes on or after this date
            end_date: Include notes on or before this date
            date_field: Which date field to filter on ("modified" or "created")

        Returns:
            List of notes matching all specified filters
        """
        notes = self.list_all_notes()

        # Apply category filter
        if category:
            notes = [n for n in notes if n.category == category]

        # Apply all_tags filter (AND logic)
        if all_tags:
            notes = [n for n in notes if all(tag in n.tags for tag in all_tags)]

        # Apply any_tags filter (OR logic)
        if any_tags:
            notes = [n for n in notes if any(tag in n.tags for tag in any_tags)]

        # Apply date range filter
        if start_date or end_date:
            if date_field not in ("modified", "created"):
                raise NoteError(
                    f"Invalid date_field: {date_field}. Must be 'modified' or 'created'"
                )

            notes = [
                n
                for n in notes
                if (
                    not start_date
                    or (n.modified_at if date_field == "modified" else n.created_at)
                    >= start_date
                )
                and (
                    not end_date
                    or (n.modified_at if date_field == "modified" else n.created_at)
                    <= end_date
                )
            ]

        return notes

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
                        # Add match with context lines before and after
                        # Calculate the range of lines to include (1-indexed)
                        # Example: context_lines=2, match on line 10 → include lines 8-12
                        start_line = max(1, i - context_lines)
                        end_line = min(len(lines), i + context_lines)

                        # Add all lines in range (avoiding duplicates from overlapping matches)
                        for line_num in range(start_line, end_line + 1):
                            if line_num not in matched_lines:
                                matched_lines.add(line_num)
                                # Convert to 0-indexed for array access
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
        """
        Parse grep/ripgrep output into structured results.

        Grep output formats:
        - Match lines: path:line_number:content
        - Context lines: path-line_number-content

        This method parses both formats and groups matches by file.
        """
        if not output.strip():
            return []

        # Group matches by file path
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
                        line_number = int(line[first_colon + 1 : second_colon])
                        line_content = line[second_colon + 1 :]
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
                    line_number = int(line[first_dash + 1 : second_dash])
                    line_content = line[second_dash + 1 :]
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


# ============================================================================
# File Watching
# ============================================================================


class NoteWatcher(FileSystemEventHandler):
    """
    Watches note directory for external changes and triggers callbacks.

    Implements debouncing to avoid rapid repeated events.
    Only watches .md files for changes.
    """

    def __init__(
        self,
        callback: Callable[[Path], None],
        debounce_seconds: float = 2.0,
    ) -> None:
        """
        Initialize the note watcher.

        Args:
            callback: Function to call when a note is modified (receives file path)
            debounce_seconds: Time to wait before triggering callback (default: 2.0s)
        """
        super().__init__()
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._last_event_times: dict[str, float] = {}
        logger.debug(f"NoteWatcher initialized with {debounce_seconds}s debounce")

    def on_modified(self, event) -> None:
        """
        Handle file modification events.

        Args:
            event: Watchdog file system event
        """
        # Ignore directory events
        if event.is_directory:
            return

        # Only watch .md files
        file_path = Path(event.src_path)
        if file_path.suffix != ".md":
            return

        # Implement debouncing
        now = time.time()
        last_event_time = self._last_event_times.get(event.src_path, 0)

        if now - last_event_time < self.debounce_seconds:
            logger.debug(f"Debouncing modification event for {file_path.name}")
            return

        # Update last event time
        self._last_event_times[event.src_path] = now

        logger.info(f"Detected modification: {file_path}")

        # Trigger callback
        try:
            self.callback(file_path)
        except Exception as e:
            logger.error(f"Error in watcher callback for {file_path}: {e}")

    def on_created(self, event) -> None:
        """
        Handle file creation events.

        Args:
            event: Watchdog file system event
        """
        # Treat creation same as modification
        self.on_modified(event)


class NoteWatcherManager:
    """
    Manages the file system observer for note watching.

    Provides start/stop controls and error handling.
    """

    def __init__(
        self,
        notes_dir: Path,
        callback: Callable[[Path], None],
        debounce_seconds: float = 2.0,
    ) -> None:
        """
        Initialize the watcher manager.

        Args:
            notes_dir: Directory to watch
            callback: Function to call when a note changes
            debounce_seconds: Debounce time in seconds
        """
        self.notes_dir = notes_dir
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[NoteWatcher] = None

    def start(self) -> None:
        """
        Start watching the notes directory.

        Raises:
            NoteError: If watcher fails to start
        """
        if self.observer is not None:
            logger.warning("Watcher already running")
            return

        try:
            logger.info(f"Starting note watcher for {self.notes_dir}")

            # Create event handler
            self.event_handler = NoteWatcher(
                callback=self.callback,
                debounce_seconds=self.debounce_seconds,
            )

            # Create and start observer
            self.observer = Observer()
            self.observer.schedule(
                self.event_handler,
                str(self.notes_dir),
                recursive=True,
            )
            self.observer.start()

            logger.info("Note watcher started successfully")

        except Exception as e:
            raise NoteError(f"Failed to start note watcher: {e}")

    def stop(self) -> None:
        """Stop the watcher if running."""
        if self.observer is None:
            logger.debug("Watcher not running")
            return

        try:
            logger.info("Stopping note watcher")
            self.observer.stop()
            self.observer.join(timeout=5)
            self.observer = None
            self.event_handler = None
            logger.info("Note watcher stopped")

        except Exception as e:
            logger.error(f"Error stopping watcher: {e}")

    def is_running(self) -> bool:
        """Check if watcher is currently running."""
        return self.observer is not None and self.observer.is_alive()

    def __enter__(self):
        """Context manager entry - start watching."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop watching."""
        self.stop()
