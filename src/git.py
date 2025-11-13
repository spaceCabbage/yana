"""
Git integration using subprocess for all git operations.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.utils import GitError


@dataclass
class SyncResult:
    """Result of a git sync operation."""

    success: bool
    message: str
    conflicts: list[str] = None

    def __post_init__(self) -> None:
        if self.conflicts is None:
            self.conflicts = []


class GitSync:
    """Handles git operations for note synchronization."""

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self._check_git_repo()

    @staticmethod
    def is_git_available() -> bool:
        """Check if git command is available on the system."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    def is_git_repo(path: Path) -> bool:
        """Check if the path is a git repository."""
        git_dir = path / ".git"
        return git_dir.exists() and git_dir.is_dir()

    @staticmethod
    def is_git_enabled(path: Path) -> bool:
        """
        Check if git operations can be performed.

        Returns True only if:
        1. Git command is available on the system
        2. The path is a valid git repository

        Args:
            path: Path to check for git repository

        Returns:
            bool: True if git is available and path is a repo
        """
        return GitSync.is_git_available() and GitSync.is_git_repo(path)

    def _check_git_repo(self) -> None:
        """Check if the path is a valid git repository."""
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            raise GitError(
                f"{self.repo_path} is not a git repository. "
                f"Initialize with: git init {self.repo_path}"
            )

    def _run_git_command(
        self, args: list[str], check: bool = True, timeout: int = 30
    ) -> subprocess.CompletedProcess:
        """
        Run a git command and return the result.

        Args:
            args: Git command arguments (e.g., ['status', '--porcelain'])
            check: Raise GitError on non-zero exit code
            timeout: Command timeout in seconds

        Returns:
            CompletedProcess with stdout/stderr

        Raises:
            GitError: If command fails and check=True
        """
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )

            if check and result.returncode != 0:
                # Detect network-related errors and provide helpful messages
                error_msg = result.stderr.lower()

                if any(
                    phrase in error_msg
                    for phrase in [
                        "could not resolve host",
                        "temporary failure in name resolution",
                    ]
                ):
                    raise GitError(
                        f"Network error: Could not resolve hostname.\n"
                        f"Check your internet connection and DNS settings."
                    )
                elif any(
                    phrase in error_msg
                    for phrase in [
                        "connection refused",
                        "connection timed out",
                        "network is unreachable",
                    ]
                ):
                    raise GitError(
                        f"Network error: Could not connect to remote repository.\n"
                        f"Check your internet connection and remote URL."
                    )
                elif (
                    "ssl certificate problem" in error_msg
                    or "certificate verify failed" in error_msg
                ):
                    raise GitError(
                        f"SSL certificate error: Could not verify remote certificate.\n"
                        f"Try: git config --global http.sslVerify false (not recommended for production)"
                    )
                elif (
                    "authentication failed" in error_msg
                    or "permission denied" in error_msg
                ):
                    raise GitError(
                        f"Authentication error: Could not authenticate with remote.\n"
                        f"Check your SSH keys or HTTPS credentials."
                    )
                else:
                    # Generic error
                    raise GitError(
                        f"Git command failed: git {' '.join(args)}\n"
                        f"Exit code: {result.returncode}\n"
                        f"Error: {result.stderr}"
                    )

            return result

        except subprocess.TimeoutExpired:
            raise GitError(
                f"Git command timed out after {timeout}s: git {' '.join(args)}\n"
                f"This may indicate a network issue. Check your internet connection."
            )
        except Exception as e:
            raise GitError(f"Failed to run git command: {e}")

    def has_local_changes(self) -> bool:
        """Check if there are uncommitted local changes."""
        result = self._run_git_command(["status", "--porcelain"])
        return bool(result.stdout.strip())

    def has_remote_changes(self) -> bool:
        """Check if there are changes on the remote."""
        # Fetch latest from remote
        self._run_git_command(["fetch"], check=False)

        # Check if we're behind
        result = self._run_git_command(
            ["rev-list", "HEAD..@{u}", "--count"], check=False
        )

        if result.returncode != 0:
            # No upstream branch configured
            return False

        commits_behind = int(result.stdout.strip() or "0")
        return commits_behind > 0

    def commit_file(self, file_path: Path, message: Optional[str] = None) -> None:
        """
        Commit a single file.

        Args:
            file_path: Path to the file to commit
            message: Commit message (auto-generated if None)
        """
        if message is None:
            message = f"Update: {file_path.name}"

        # Add file
        self._run_git_command(["add", str(file_path)])

        # Commit
        self._run_git_command(["commit", "-m", message])

    def commit_all(self, message: Optional[str] = None) -> None:
        """
        Commit all changes.

        Args:
            message: Commit message (auto-generated if None)
        """
        if message is None:
            from datetime import datetime

            message = f"Auto-commit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # Add all changes
        self._run_git_command(["add", "-A"])

        # Commit
        self._run_git_command(["commit", "-m", message])

    def push(self) -> None:
        """Push commits to remote."""
        self._run_git_command(["push"])

    def pull(self) -> None:
        """Pull changes from remote with rebase."""
        self._run_git_command(["pull", "--rebase"])

    def stash_changes(self) -> bool:
        """
        Stash local changes.

        Returns:
            True if changes were stashed, False if nothing to stash
        """
        result = self._run_git_command(["stash", "push", "-u"], check=False)
        return "No local changes to save" not in result.stdout

    def pop_stash(self) -> SyncResult:
        """
        Pop stashed changes.

        Returns:
            SyncResult indicating success or conflicts
        """
        result = self._run_git_command(["stash", "pop"], check=False)

        if result.returncode == 0:
            return SyncResult(success=True, message="Stash applied successfully")

        # Check for conflicts
        if "CONFLICT" in result.stdout:
            conflicts = self._get_conflicted_files()
            return SyncResult(
                success=False,
                message="Conflicts occurred while applying stash",
                conflicts=conflicts,
            )

        raise GitError(f"Failed to pop stash: {result.stderr}")

    def _get_conflicted_files(self) -> list[str]:
        """Get list of files with merge conflicts."""
        result = self._run_git_command(["diff", "--name-only", "--diff-filter=U"])
        return result.stdout.strip().split("\n") if result.stdout.strip() else []

    def handle_conflicts(self) -> None:
        """
        Handle merge conflicts by creating .conflict backups.

        Strategy:
        - Keep local version in main file
        - Save remote version to .conflict.md file
        """
        conflicts = self._get_conflicted_files()

        for conflict_file in conflicts:
            file_path = self.repo_path / conflict_file
            conflict_backup = file_path.with_suffix(".conflict.md")

            # TODO: Implement conflict resolution
            # For now, just mark as resolved
            self._run_git_command(["add", conflict_file])

    def sync(self) -> SyncResult:
        """
        Perform a full sync: stash, pull, pop, commit, push.

        Workflow:
        1. Stash local changes (if any) to avoid conflicts
        2. Pull remote changes with rebase
        3. Pop stashed changes back on top
        4. Handle any conflicts that arise

        Returns:
            SyncResult with operation status
        """
        stashed = False

        try:
            # 1. Stash local changes if any
            # This temporarily saves uncommitted changes so we can pull cleanly
            if self.has_local_changes():
                stashed = self.stash_changes()

            # 2. Pull remote changes
            # Fetch and rebase local commits on top of remote commits
            if self.has_remote_changes():
                self.pull()

            # 3. Pop stash if we stashed
            # Reapply the uncommitted changes we saved earlier
            if stashed:
                result = self.pop_stash()
                if not result.success:
                    # Conflicts occurred - create .conflict backups
                    self.handle_conflicts()
                    return result

            return SyncResult(success=True, message="Sync completed successfully")

        except GitError as e:
            return SyncResult(success=False, message=str(e))
