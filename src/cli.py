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
from src.fzf import NoteFuzzyFinder
from src.git import GitSync
from src.notes import NoteManager
from src.utils import YanaError

app = typer.Typer(
    name="yana",
    help="Yet Another Notes App - CLI markdown notes with git sync and FZF",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"[bold]YANA[/bold] version {__version__}")
        raise typer.Exit()


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
        config = load_config()
        note_manager = NoteManager(config.notes_dir)

        # TODO: Implement command handlers
        console.print("[yellow]Command implementation in progress...[/yellow]")
        console.print(f"Notes directory: {config.notes_dir}")
        console.print(f"Editor: {config.editor}")

    except ConfigError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        console.print("\n[yellow]Run 'yana config' to set up configuration[/yellow]")
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
        config = load_config()
        note_manager = NoteManager(config.notes_dir)

        # TODO: Implement note creation
        console.print(f"[yellow]Creating note:[/yellow] {title}")
        console.print(f"Category: {category}")
        if tags:
            console.print(f"Tags: {', '.join(tags)}")

    except YanaError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def sync() -> None:
    """
    Manually sync notes with git (commit, pull, push).

    Examples:

        \b
        yana sync    # Sync all changes
    """
    try:
        config = load_config()

        if not config.git_enabled:
            console.print("[yellow]Git sync is disabled in config[/yellow]")
            raise typer.Exit(0)

        # TODO: Implement git sync
        console.print("[yellow]Syncing notes...[/yellow]")

    except YanaError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


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
Git Auto-Commit: {cfg.git_auto_commit}
Git Auto-Push: {cfg.git_auto_push}
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
