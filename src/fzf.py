"""
FZF integration for fuzzy finding notes.
"""

import shutil
from pathlib import Path
from typing import Optional

from iterfzf import iterfzf

from src.notes import Note
from src.utils import FzfError


class NoteFuzzyFinder:
    """FZF integration for selecting notes."""

    def __init__(
        self,
        notes: list[Note],
        preview_enabled: bool = True,
        preview_command: str = "bat --style=plain --color=always {}",
    ) -> None:
        self.notes = notes
        self.preview_enabled = preview_enabled
        self.preview_command = preview_command

    def format_note_for_fzf(self, note: Note) -> str:
        """
        Format note for FZF display.

        Format: [category] Title | #tags | path
        Example: [work-projects] Meeting Notes | #meeting #action-items | ~/notes/meeting-notes.md
        """
        tags = " ".join(f"#{tag}" for tag in note.tags) if note.tags else ""
        return f"[{note.category}] {note.title} | {tags} | {note.path}"

    def parse_selection(self, selection: str) -> Optional[Note]:
        """
        Parse FZF selection back to Note object.

        Args:
            selection: FZF output string

        Returns:
            Matching Note object or None
        """
        # Extract path from end of selection
        try:
            path_str = selection.split(" | ")[-1].strip()
            path = Path(path_str)

            # Find matching note
            for note in self.notes:
                if note.path == path:
                    return note

        except Exception:
            return None

        return None

    def _get_preview_command(self) -> Optional[str]:
        """
        Get preview command, checking if required tools are available.

        Falls back to cat if bat is not available.
        """
        if not self.preview_enabled:
            return None

        # Check if bat is available
        if "bat" in self.preview_command and shutil.which("bat") is None:
            # Fallback to cat
            return "cat {}"

        return self.preview_command

    def select(self, category_filter: Optional[str] = None) -> Optional[Note]:
        """
        Launch FZF to select a note.

        Args:
            category_filter: Optional category to filter by

        Returns:
            Selected Note or None if cancelled
        """
        # Filter by category if specified
        notes_to_show = self.notes
        if category_filter:
            notes_to_show = [n for n in self.notes if n.category == category_filter]

        if not notes_to_show:
            raise FzfError(
                f"No notes found"
                + (f" in category: {category_filter}" if category_filter else "")
            )

        # Format notes for display
        items = [self.format_note_for_fzf(note) for note in notes_to_show]

        # Get preview command
        preview_cmd = self._get_preview_command()

        # Build FZF options
        fzf_options = {
            "multi": False,
            "exact": False,
        }

        # Add preview if enabled
        if preview_cmd:
            # Extract path from formatted string for preview
            # FZF will pass the entire line to preview command
            # We need to extract the path part
            fzf_options["preview"] = (
                f"echo {{}} | awk -F' \\| ' '{{print $NF}}' | xargs {preview_cmd.replace('{}', '')}"
            )
            # Use __extra__ for FZF-specific options like preview-window
            fzf_options["__extra__"] = ["--preview-window=right:50%:wrap"]

        # Launch FZF
        try:
            selection = iterfzf(
                items,
                **fzf_options,
            )
        except Exception as e:
            raise FzfError(f"FZF error: {e}")

        if selection is None:
            return None

        return self.parse_selection(selection)

    def select_multiple(self, category_filter: Optional[str] = None) -> list[Note]:
        """
        Launch FZF to select multiple notes.

        Args:
            category_filter: Optional category to filter by

        Returns:
            List of selected Notes (empty if cancelled)
        """
        # Filter by category if specified
        notes_to_show = self.notes
        if category_filter:
            notes_to_show = [n for n in self.notes if n.category == category_filter]

        if not notes_to_show:
            return []

        # Format notes for display
        items = [self.format_note_for_fzf(note) for note in notes_to_show]

        # Launch FZF with multi-select
        try:
            selections = iterfzf(
                items,
                multi=True,
                exact=False,
            )
        except Exception as e:
            raise FzfError(f"FZF error: {e}")

        if not selections:
            return []

        # Parse all selections
        selected_notes = []
        for selection in selections:
            note = self.parse_selection(selection)
            if note:
                selected_notes.append(note)

        return selected_notes
