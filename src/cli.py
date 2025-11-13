"""
CLI interface for YANA using Typer.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

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
            console.print("[blue]Pulling remote changes...[/blue]")
            logger.info("Pulling remote changes")
            git_sync.pull()
            console.print("[green]✓[/green] Synced with remote")
            logger.info("Successfully synced with remote")
    except GitError as e:
        logger.warning(f"Could not pull changes: {e}")
        console.print(f"[yellow]Warning: Could not pull changes: {e}[/yellow]")


def _sync_after_edit(git_sync: GitSync, note_path: Path, was_modified: bool) -> None:
    """Commit changes after editing."""
    if not was_modified:
        logger.debug("No modifications detected, skipping commit")
        return

    try:
        # Commit the file
        logger.info(f"Committing changes to {note_path}")
        git_sync.commit_file(note_path)
        console.print(f"[green]✓[/green] Changes committed: {note_path.name}")
        logger.info(f"Successfully committed {note_path.name}")

    except GitError as e:
        logger.error(f"Could not commit changes: {e}")
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
    daily: bool = typer.Option(False, "--daily", "-d", help="Open today's journal"),
    last: bool = typer.Option(False, "--last", "-l", help="Open last edited note"),
) -> None:
    """
    Browse and manage your markdown notes with FZF.

    Examples:

        \b
        yana                        # Browse all notes
        yana --category work        # Filter by category
        yana /path/to/note.md       # Open specific note
        yana --daily                # Open today's journal
        yana --last                 # Open last edited note
    """
    try:
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

            # Launch FZF to select note
            finder = NoteFuzzyFinder(
                all_notes,
                preview_enabled=config.fzf_preview,
                preview_command=config.fzf_preview_command,
            )
            note_to_open = finder.select(category_filter=category)

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
) -> None:
    """
    Create a new note with frontmatter.

    Examples:

        \b
        yana new "Meeting Notes" work-projects
        yana new "Daily Standup" team-sync --tag meeting --tag standup
    """
    try:
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
        console.print(f"[blue]Creating note:[/blue] {title}")
        note = note_manager.create_note(title, category, tags)
        logger.info(f"Note created: {note.path}")
        console.print(f"[green]✓[/green] Created: {note.path}")

        # Sync before editing
        if git_sync:
            _sync_before_edit(git_sync)

        # Open in editor
        was_modified = open_in_editor(note.path, config.editor)

        # Sync after editing
        if git_sync:
            _sync_after_edit(git_sync, note.path, True)
        else:
            console.print(f"[green]✓[/green] Note ready: {note.path}")

    except YanaError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        raise typer.Exit(130)


@app.command()
def sync() -> None:
    """
    Manually sync notes with git (commit, pull, push).

    Examples:

        \b
        yana sync    # Sync all changes
    """
    try:
        logger.debug("Starting manual sync")
        config = load_config()

        if not config.git_enabled:
            logger.info("Git sync is disabled in config")
            console.print("[yellow]Git sync is disabled in config[/yellow]")
            raise typer.Exit(0)

        # Initialize git
        try:
            git_sync = GitSync(config.notes_dir)
        except GitError as e:
            logger.error(f"Git initialization failed: {e}")
            console.print(f"[red]Git Error:[/red] {e}")
            raise typer.Exit(1)

        # Perform sync
        logger.info("Performing git sync")
        console.print("[blue]Syncing notes...[/blue]")
        result = git_sync.sync()
        logger.debug(f"Sync result: success={result.success}, message={result.message}")

        if result.success:
            console.print(f"[green]✓[/green] {result.message}")

            # Always push when manually syncing
            if git_sync.has_local_changes():
                console.print("[blue]Pushing to remote...[/blue]")
                git_sync.push()
                console.print("[green]✓[/green] Pushed to remote")
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
