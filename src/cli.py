"""
CLI interface for YANA using Typer.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.status import Status

from src import __version__
from src.config import ConfigError, load_config
from src.editor import open_in_editor
from src.fzf import FzfError, NoteFuzzyFinder
from src.git import GitError, GitSync
from src.notes import Note, NoteManager
from src.utils import YanaError, logger, setup_logging

app = typer.Typer(
    name="yana",
    help="Yet Another Notes App - CLI markdown notes with git sync and FZF",
    add_completion=False,
)
console = Console()

# Global quiet mode flag
_quiet_mode = False

# Initialize logging on module import
setup_logging()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"[bold]YANA[/bold] version {__version__}")
        raise typer.Exit()


# Git sync helper functions
def _sync_before_edit(git_sync: GitSync) -> None:
    """Pull changes before editing if there are remote changes."""
    try:
        logger.debug("Checking for remote changes")
        if git_sync.has_remote_changes():
            if not _quiet_mode:
                # Use spinner for git pull
                with console.status(
                    "[blue]Pulling remote changes...[/blue]", spinner="dots"
                ):
                    logger.info("Pulling remote changes")
                    git_sync.pull()
                console.print("[green]✓[/green] Synced with remote")
            else:
                # Quiet mode: no spinner, just execute
                logger.info("Pulling remote changes")
                git_sync.pull()
            logger.info("Successfully synced with remote")
    except GitError as e:
        logger.warning(f"Could not pull changes: {e}")
        if not _quiet_mode:
            console.print(f"[yellow]Warning: Could not pull changes: {e}[/yellow]")


def _sync_after_edit(git_sync: GitSync, note_path: Path, was_modified: bool) -> None:
    """Commit changes after editing and push to remote."""
    if not was_modified:
        logger.debug("No modifications detected, skipping commit")
        return

    try:
        # Commit the file
        logger.info(f"Committing changes to {note_path}")

        if not _quiet_mode:
            with console.status("[blue]Committing changes...[/blue]", spinner="dots"):
                git_sync.commit_file(note_path)
            console.print(f"[green]✓[/green] Changes committed: {note_path.name}")
        else:
            git_sync.commit_file(note_path)

        logger.info(f"Successfully committed {note_path.name}")

        # Always attempt to push after commit
        try:
            logger.info("Pushing changes to remote")
            if not _quiet_mode:
                with console.status(
                    "[blue]Pushing to remote...[/blue]", spinner="dots"
                ):
                    git_sync.push()
                console.print(f"[green]✓[/green] Pushed to remote")
            else:
                git_sync.push()

            logger.info("Successfully pushed to remote")

        except GitError as push_error:
            # Check if it's a network-related error
            error_msg = str(push_error).lower()
            is_network_error = any(
                phrase in error_msg
                for phrase in [
                    "network error",
                    "could not resolve",
                    "could not connect",
                    "connection refused",
                    "connection timed out",
                    "network is unreachable",
                    "timed out",
                ]
            )

            if is_network_error:
                logger.warning(
                    f"Could not push to remote (network issue): {push_error}"
                )
                if not _quiet_mode:
                    console.print(
                        f"[yellow]Committed locally, but could not push to remote (network issue)[/yellow]"
                    )
            else:
                # Other git errors (auth, conflicts, etc.)
                logger.error(f"Could not push to remote: {push_error}")
                if not _quiet_mode:
                    console.print(
                        f"[yellow]Warning: Could not push to remote: {push_error}[/yellow]"
                    )

    except GitError as e:
        logger.error(f"Could not commit changes: {e}")
        if not _quiet_mode:
            console.print(f"[yellow]Warning: Could not commit changes: {e}[/yellow]")


@app.callback()
def main_callback(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """YANA - Yet Another Notes App"""
    pass


@app.command()
def main(
    path: Optional[Path] = typer.Argument(None, help="Path to note or folder"),
    category: Optional[str] = typer.Option(
        None, "--category", "-c", help="Filter by category"
    ),
    search: Optional[str] = typer.Option(
        None, "--search", "-s", help="Search note content (regex)"
    ),
    tag: Optional[list[str]] = typer.Option(
        None, "--tag", "-t", help="Filter by tag (can specify multiple, uses OR logic)"
    ),
    all_tags: bool = typer.Option(
        False, "--all-tags", help="Use AND logic for tags (note must have all tags)"
    ),
    since: Optional[str] = typer.Option(
        None, "--since", help="Filter notes modified since date (YYYY-MM-DD)"
    ),
    before: Optional[str] = typer.Option(
        None, "--before", help="Filter notes modified before date (YYYY-MM-DD)"
    ),
    daily: bool = typer.Option(False, "--daily", "-d", help="Open today's journal"),
    last: bool = typer.Option(False, "--last", "-l", help="Open last edited note"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output messages"),
) -> None:
    """
    Browse and manage your markdown notes with FZF.

    Examples:

        \b
        yana                        # Browse all notes
        yana --category work        # Filter by category
        yana --search "TODO"        # Search note content
        yana --tag python --tag web # Filter by tags (OR: python OR web)
        yana --tag python --all-tags --tag coding  # AND: python AND coding
        yana --since 2025-01-01     # Notes modified since Jan 1
        yana --category work --tag meeting --since 2025-01-01  # Combined filters
        yana /path/to/note.md       # Open specific note
        yana --daily                # Open today's journal
        yana --last                 # Open last edited note
    """
    try:
        # Set global quiet mode
        global _quiet_mode
        _quiet_mode = quiet

        logger.debug("Loading configuration")
        config = load_config()
        logger.debug(f"Config loaded: notes_dir={config.notes_dir}")

        note_manager = NoteManager(config.notes_dir)

        # Initialize git if enabled
        git_sync = None
        if config.git_enabled:
            try:
                logger.debug("Initializing git sync")
                git_sync = GitSync(config.notes_dir)
                logger.info("Git sync initialized")
            except GitError as e:
                logger.warning(f"Git not available: {e}")
                console.print(f"[yellow]Git not available: {e}[/yellow]")

        note_to_open: Optional[Note] = None

        # Handle --daily flag
        if daily:
            logger.info("Opening daily journal")
            note_to_open = note_manager.get_daily_note()
            console.print(
                f"[blue]Opening daily journal:[/blue] {note_to_open.path.name}"
            )

        # Handle --last flag
        elif last:
            logger.info("Opening last edited note")
            note_to_open = note_manager.get_last_edited_note()
            if not note_to_open:
                logger.debug("No notes found in directory")
                console.print("[yellow]No notes found[/yellow]")
                raise typer.Exit(0)
            console.print(f"[blue]Opening last note:[/blue] {note_to_open.title}")

        # Handle --search flag
        elif search:
            logger.info(f"Searching for: {search}")
            console.print(f"[blue]Searching for:[/blue] {search}")

            try:
                search_results = note_manager.search_content(search)

                if not search_results:
                    console.print(f"[yellow]No matches found for '{search}'[/yellow]")
                    raise typer.Exit(0)

                # Extract notes from results (discard match details for FZF)
                matched_notes = [note for note, _ in search_results]
                console.print(
                    f"[green]Found {len(matched_notes)} note(s) with matches[/green]"
                )
                logger.info(f"Found {len(matched_notes)} matching notes")

                # Launch FZF to select from matching notes
                finder = NoteFuzzyFinder(
                    matched_notes,
                    preview_enabled=config.fzf_preview,
                    preview_command=config.fzf_preview_command,
                )
                note_to_open = finder.select()

            except Exception as e:
                logger.error(f"Search failed: {e}")
                console.print(f"[red]Search failed:[/red] {e}")
                raise typer.Exit(1)

        # Handle direct path argument
        elif path:
            if path.is_file():
                # Open specific file
                note_to_open = note_manager.get_note(path)
            elif path.is_dir():
                # Browse notes in specific directory
                # Get all notes and filter by directory
                all_notes = note_manager.list_all_notes()
                dir_notes = [n for n in all_notes if path in n.path.parents]
                if not dir_notes:
                    console.print(f"[yellow]No notes found in {path}[/yellow]")
                    raise typer.Exit(0)
                # Launch FZF for directory
                finder = NoteFuzzyFinder(
                    dir_notes,
                    preview_enabled=config.fzf_preview,
                    preview_command=config.fzf_preview_command,
                )
                note_to_open = finder.select()
            else:
                console.print(f"[red]Path not found:[/red] {path}")
                raise typer.Exit(1)

        # Handle browse mode (default)
        else:
            # Load all notes
            logger.debug("Loading all notes for browsing")
            all_notes = note_manager.list_all_notes()
            logger.debug(f"Found {len(all_notes)} notes")

            if not all_notes:
                logger.info("No notes found in directory")
                console.print(
                    "[yellow]No notes found.[/yellow] Create one with: [bold]yana new <title> <category>[/bold]"
                )
                raise typer.Exit(0)

            # Apply filters
            filtered_notes = all_notes

            # Apply category filter
            if category:
                filtered_notes = [n for n in filtered_notes if n.category == category]
                logger.debug(
                    f"Filtered by category '{category}': {len(filtered_notes)} notes"
                )

            # Apply tag filter
            if tag:
                if all_tags:
                    # AND logic: note must have ALL tags
                    filtered_notes = [
                        n for n in filtered_notes if all(t in n.tags for t in tag)
                    ]
                    logger.debug(
                        f"Filtered by all tags {tag}: {len(filtered_notes)} notes"
                    )
                else:
                    # OR logic: note must have ANY tag
                    filtered_notes = [
                        n for n in filtered_notes if any(t in n.tags for t in tag)
                    ]
                    logger.debug(
                        f"Filtered by any tag {tag}: {len(filtered_notes)} notes"
                    )

            # Apply date filters
            if since or before:
                try:
                    start_date = datetime.strptime(since, "%Y-%m-%d") if since else None
                    end_date = datetime.strptime(before, "%Y-%m-%d") if before else None

                    filtered_notes = [
                        n
                        for n in filtered_notes
                        if (not start_date or n.modified_at >= start_date)
                        and (not end_date or n.modified_at <= end_date)
                    ]
                    logger.debug(f"Filtered by date range: {len(filtered_notes)} notes")
                except ValueError as e:
                    console.print(f"[red]Invalid date format:[/red] {e}")
                    console.print(
                        "[yellow]Use YYYY-MM-DD format (e.g., 2025-01-01)[/yellow]"
                    )
                    raise typer.Exit(1)

            # Check if filtering resulted in no notes
            if not filtered_notes:
                console.print("[yellow]No notes match the specified filters[/yellow]")
                raise typer.Exit(0)

            # Launch FZF to select note
            finder = NoteFuzzyFinder(
                filtered_notes,
                preview_enabled=config.fzf_preview,
                preview_command=config.fzf_preview_command,
            )
            note_to_open = finder.select()

        # Handle FZF cancellation
        if not note_to_open:
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit(0)

        # Sync before editing
        if git_sync:
            _sync_before_edit(git_sync)

        # Open in editor
        was_modified = open_in_editor(note_to_open.path, config.editor)

        # Sync after editing
        if git_sync and was_modified:
            _sync_after_edit(git_sync, note_to_open.path, was_modified)
        elif was_modified:
            console.print(f"[green]✓[/green] Saved: {note_to_open.path.name}")

    except ConfigError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        console.print("\n[yellow]Run 'yana config' to set up configuration[/yellow]")
        raise typer.Exit(1)
    except FzfError as e:
        console.print(f"[red]FZF Error:[/red] {e}")
        raise typer.Exit(1)
    except YanaError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        raise typer.Exit(130)


@app.command()
def new(
    title: str = typer.Argument(..., help="Note title"),
    category: str = typer.Argument(..., help="Note category"),
    tags: Optional[list[str]] = typer.Option(None, "--tag", "-t", help="Add tags"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output messages"),
) -> None:
    """
    Create a new note with frontmatter.

    Examples:

        \b
        yana new "Meeting Notes" work-projects
        yana new "Daily Standup" team-sync --tag meeting --tag standup
    """
    try:
        # Set global quiet mode
        global _quiet_mode
        _quiet_mode = quiet

        logger.debug("Loading configuration for new note")
        config = load_config()
        note_manager = NoteManager(config.notes_dir)

        # Initialize git if enabled
        git_sync = None
        if config.git_enabled:
            try:
                git_sync = GitSync(config.notes_dir)
            except GitError as e:
                logger.warning(f"Git not available: {e}")
                console.print(f"[yellow]Git not available: {e}[/yellow]")

        # Create the note
        logger.info(
            f"Creating new note: title={title}, category={category}, tags={tags}"
        )
        if not _quiet_mode:
            console.print(f"[blue]Creating note:[/blue] {title}")
        note = note_manager.create_note(title, category, tags)
        logger.info(f"Note created: {note.path}")
        if not _quiet_mode:
            console.print(f"[green]✓[/green] Created: {note.path}")

        # Sync before editing
        if git_sync:
            _sync_before_edit(git_sync)

        # Open in editor
        was_modified = open_in_editor(note.path, config.editor)

        # Sync after editing
        if git_sync:
            _sync_after_edit(git_sync, note.path, True)
        elif not _quiet_mode:
            console.print(f"[green]✓[/green] Note ready: {note.path}")

    except YanaError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        raise typer.Exit(130)


@app.command()
def sync(
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output messages"),
) -> None:
    """
    Manually sync notes with git (commit, pull, push).

    Examples:

        \b
        yana sync    # Sync all changes
    """
    try:
        # Set global quiet mode
        global _quiet_mode
        _quiet_mode = quiet

        logger.debug("Starting manual sync")
        config = load_config()

        if not config.git_enabled:
            logger.info("Git sync is disabled in config")
            if not _quiet_mode:
                console.print("[yellow]Git sync is disabled in config[/yellow]")
            raise typer.Exit(0)

        # Initialize git
        try:
            git_sync = GitSync(config.notes_dir)
        except GitError as e:
            logger.error(f"Git initialization failed: {e}")
            if not _quiet_mode:
                console.print(f"[red]Git Error:[/red] {e}")
            raise typer.Exit(1)

        # Perform sync
        logger.info("Performing git sync")
        if not _quiet_mode:
            with console.status("[blue]Syncing notes...[/blue]", spinner="dots"):
                result = git_sync.sync()
        else:
            result = git_sync.sync()

        logger.debug(f"Sync result: success={result.success}, message={result.message}")

        if result.success:
            if not _quiet_mode:
                console.print(f"[green]✓[/green] {result.message}")

            # Always attempt to push after successful sync
            try:
                logger.info("Pushing changes to remote")
                if not _quiet_mode:
                    with console.status(
                        "[blue]Pushing to remote...[/blue]", spinner="dots"
                    ):
                        git_sync.push()
                    console.print("[green]✓[/green] Pushed to remote")
                else:
                    git_sync.push()

                logger.info("Successfully pushed to remote")

            except GitError as push_error:
                # Check if it's a network-related error
                error_msg = str(push_error).lower()
                is_network_error = any(
                    phrase in error_msg
                    for phrase in [
                        "network error",
                        "could not resolve",
                        "could not connect",
                        "connection refused",
                        "connection timed out",
                        "network is unreachable",
                        "timed out",
                    ]
                )

                if is_network_error:
                    logger.warning(
                        f"Could not push to remote (network issue): {push_error}"
                    )
                    if not _quiet_mode:
                        console.print(
                            f"[yellow]Synced locally, but could not push to remote (network issue)[/yellow]"
                        )
                else:
                    # Other git errors (auth, conflicts, etc.)
                    logger.error(f"Could not push to remote: {push_error}")
                    if not _quiet_mode:
                        console.print(
                            f"[yellow]Warning: Could not push to remote: {push_error}[/yellow]"
                        )
        else:
            console.print(f"[red]Sync failed:[/red] {result.message}")
            if result.conflicts:
                console.print(
                    f"[yellow]Conflicts in:[/yellow] {', '.join(result.conflicts)}"
                )
                console.print(
                    "[yellow]Please resolve conflicts manually and run 'yana sync' again[/yellow]"
                )
            raise typer.Exit(1)

    except GitError as e:
        console.print(f"[red]Git Error:[/red] {e}")
        raise typer.Exit(1)
    except YanaError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        raise typer.Exit(130)


@app.command()
def config() -> None:
    """
    Show current configuration.

    Examples:

        \b
        yana config    # Show config
    """
    try:
        cfg = load_config()

        panel = Panel.fit(
            f"""[bold]Configuration[/bold]

Notes Directory: {cfg.notes_dir}
Editor: {cfg.editor}
Git Enabled: {cfg.git_enabled}
Git Commit Interval: {cfg.git_commit_interval}s
Watch Enabled: {cfg.watch_enabled}
FZF Preview: {cfg.fzf_preview}
""",
            title="YANA Config",
            border_style="blue",
        )
        console.print(panel)

    except ConfigError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        console.print(
            "\n[yellow]Create a config file at ~/.config/yana/config.json[/yellow]"
        )
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
