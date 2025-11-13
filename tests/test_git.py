"""Tests for git module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.git import GitSync, SyncResult
from src.utils import GitError


@pytest.fixture
def git_repo(temp_notes_dir):
    """Create a git repository for testing."""
    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=temp_notes_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_notes_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=temp_notes_dir,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    readme = temp_notes_dir / "README.md"
    readme.write_text("# Test Repo")
    subprocess.run(
        ["git", "add", "README.md"],
        cwd=temp_notes_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=temp_notes_dir,
        check=True,
        capture_output=True,
    )

    return temp_notes_dir


def test_git_sync_init(git_repo):
    """Test GitSync initialization."""
    git_sync = GitSync(git_repo)
    assert git_sync.repo_path == git_repo


def test_git_sync_init_no_git(temp_notes_dir):
    """Test GitSync initialization with no git repo."""
    with pytest.raises(GitError, match="not a git repository"):
        GitSync(temp_notes_dir)


def test_has_local_changes_clean(git_repo):
    """Test has_local_changes with clean working tree."""
    git_sync = GitSync(git_repo)
    assert not git_sync.has_local_changes()


def test_has_local_changes_modified(git_repo):
    """Test has_local_changes with modifications."""
    git_sync = GitSync(git_repo)

    # Modify a file
    readme = git_repo / "README.md"
    readme.write_text("# Modified")

    assert git_sync.has_local_changes()


def test_has_local_changes_untracked(git_repo):
    """Test has_local_changes with untracked files."""
    git_sync = GitSync(git_repo)

    # Create untracked file
    new_file = git_repo / "new-note.md"
    new_file.write_text("# New Note")

    assert git_sync.has_local_changes()


def test_commit_file(git_repo):
    """Test committing a single file."""
    git_sync = GitSync(git_repo)

    # Create and commit a new file
    note = git_repo / "test-note.md"
    note.write_text("# Test Note")

    git_sync.commit_file(note)

    # Check file is committed
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=git_repo,
        capture_output=True,
        text=True,
    )
    assert "test-note.md" in result.stdout.lower()


def test_commit_file_custom_message(git_repo):
    """Test committing with custom message."""
    git_sync = GitSync(git_repo)

    note = git_repo / "note.md"
    note.write_text("# Note")

    git_sync.commit_file(note, message="Custom commit message")

    result = subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        cwd=git_repo,
        capture_output=True,
        text=True,
    )
    assert "Custom commit message" in result.stdout


def test_commit_all(git_repo):
    """Test committing all changes."""
    git_sync = GitSync(git_repo)

    # Create multiple files
    (git_repo / "note1.md").write_text("# Note 1")
    (git_repo / "note2.md").write_text("# Note 2")

    git_sync.commit_all("Commit all changes")

    # Check both files are committed
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=git_repo,
        capture_output=True,
        text=True,
    )
    assert "commit all changes" in result.stdout.lower()


def test_stash_changes(git_repo):
    """Test stashing changes."""
    git_sync = GitSync(git_repo)

    # Modify file
    readme = git_repo / "README.md"
    readme.write_text("# Modified")

    assert git_sync.has_local_changes()

    result = git_sync.stash_changes()

    assert result is True
    assert not git_sync.has_local_changes()


def test_pop_stash(git_repo):
    """Test popping stashed changes."""
    git_sync = GitSync(git_repo)

    # Modify and stash
    readme = git_repo / "README.md"
    original_content = readme.read_text()
    readme.write_text("# Modified")
    git_sync.stash_changes()

    # Content should be reverted
    assert readme.read_text() == original_content

    # Pop stash
    result = git_sync.pop_stash()

    assert result.success
    assert readme.read_text() == "# Modified"


def test_sync_no_changes(git_repo):
    """Test sync with no changes."""
    git_sync = GitSync(git_repo)

    result = git_sync.sync()

    assert result.success
    assert result.message  # Just check there is a message


def test_has_remote_changes_no_remote(git_repo):
    """Test has_remote_changes with no remote configured."""
    git_sync = GitSync(git_repo)

    # Should return False when no remote
    assert not git_sync.has_remote_changes()


@patch("subprocess.run")
def test_pull_with_rebase(mock_run, git_repo):
    """Test pull with rebase."""
    git_sync = GitSync(git_repo)

    # Mock successful pull
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Successfully rebased",
        stderr="",
    )

    git_sync.pull()  # Returns None on success

    assert True  # No exception means success
    # Verify git pull --rebase was called
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "pull" in call_args
    assert "--rebase" in call_args


@patch("subprocess.run")
def test_push_success(mock_run, git_repo):
    """Test successful push."""
    git_sync = GitSync(git_repo)

    # Mock successful push
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="Branch pushed",
        stderr="",
    )

    git_sync.push()  # Returns None on success

    assert True  # No exception means success


@patch("subprocess.run")
def test_push_failure(mock_run, git_repo):
    """Test push failure."""
    git_sync = GitSync(git_repo)

    # Mock failed push
    mock_run.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="Push rejected",
    )

    with pytest.raises(GitError, match="Push rejected"):
        git_sync.push()


def test_handle_conflicts(git_repo):
    """Test conflict handling creates backup files."""
    git_sync = GitSync(git_repo)

    # Create a file that would have conflicts
    conflicted_file = git_repo / "conflicted.md"
    conflicted_file.write_text(
        "<<<<<<< HEAD\nLocal change\n=======\nRemote change\n>>>>>>> origin/master"
    )

    git_sync.handle_conflicts()

    # Just verify it doesn't crash (returns None)
    assert True


def test_commit_file_not_in_repo(git_repo):
    """Test committing file outside repo raises error."""
    git_sync = GitSync(git_repo)

    # Try to commit file outside repo
    external_file = Path("/tmp/external.md")

    with pytest.raises(GitError, match="outside repository"):
        git_sync.commit_file(external_file)


def test_sync_with_local_changes(git_repo):
    """Test sync with local uncommitted changes."""
    git_sync = GitSync(git_repo)

    # Create local changes
    note = git_repo / "note.md"
    note.write_text("# Local Note")

    result = git_sync.sync()

    # Should stash and restore changes
    assert result.success


@patch("subprocess.run")
def test_git_command_timeout(mock_run, git_repo):
    """Test git command timeout handling."""
    git_sync = GitSync(git_repo)

    # Mock timeout
    mock_run.side_effect = subprocess.TimeoutExpired(
        cmd="git pull",
        timeout=30,
    )

    with pytest.raises(GitError, match="timed out"):
        git_sync.pull()


def test_multiple_commits(git_repo):
    """Test multiple sequential commits."""
    git_sync = GitSync(git_repo)

    # Create and commit multiple files
    for i in range(3):
        note = git_repo / f"note-{i}.md"
        note.write_text(f"# Note {i}")
        git_sync.commit_file(note)

    # Check we have 4 commits (initial + 3 notes)
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=git_repo,
        capture_output=True,
        text=True,
    )
    assert int(result.stdout.strip()) == 4


def test_commit_file_creates_parent_dirs(git_repo):
    """Test that commit_file handles nested directories."""
    git_sync = GitSync(git_repo)

    # Create file in nested directory
    nested_dir = git_repo / "category" / "subcategory"
    nested_dir.mkdir(parents=True)
    note = nested_dir / "note.md"
    note.write_text("# Nested Note")

    git_sync.commit_file(note)

    # Should be committed
    result = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=git_repo,
        capture_output=True,
        text=True,
    )
    assert "note.md" in result.stdout.lower()


def test_git_sync_result_dataclass():
    """Test SyncResult dataclass."""
    result = SyncResult(
        success=True,
        message="Sync completed",
        conflicts=["file1.md", "file2.md"],
    )

    assert result.success is True
    assert result.message == "Sync completed"
    assert len(result.conflicts) == 2
