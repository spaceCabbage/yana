# YANA - Development Documentation

**Generated**: 2025-01-13
**Python Version**: 3.13+
**Philosophy**: Lean, modern, stdlib-first

---

## Project Overview

YANA (Yet Another Notes App) is a CLI-based markdown notes manager with FZF integration and git synchronization. Built with modern Python 3.13 features and minimal dependencies.

### Core Features
- Markdown notes with YAML frontmatter (categories + tags)
- FZF fuzzy finding for fast note browsing
- Configurable external editor integration
- Git auto-sync (commit, pull, push)
- Category filtering (CLI and FZF)
- Daily journal notes
- File watching for external changes

---

## Architecture Decisions

### 1. Dependencies (Minimal by Design)

**Core Dependencies (5 libraries):**
```toml
dependencies = [
    "iterfzf>=1.4.0",   # FZF integration (bundles fzf binary)
    "typer>=0.9.0",     # Modern CLI framework with type hints
    "pyyaml>=6.0",      # YAML frontmatter parsing
    "rich>=13.7.0",     # Terminal UI, colors, pretty output
    "watchdog>=3.0.0",  # File system monitoring
]
```

**Why These?**
- `iterfzf`: Bundles fzf, cross-platform, no external deps
- `typer`: Type-safe CLI with minimal boilerplate
- `pyyaml`: Standard YAML parser for frontmatter
- `rich`: Beautiful terminal output, worth the dependency
- `watchdog`: Cross-platform file watching

**Stdlib Usage:**
- `json` - Config file parsing (no tomllib needed)
- `subprocess` - Git operations and editor launching
- `pathlib` - All file operations
- `dataclasses` - Data structures with slots
- `typing` - Modern type hints

**What We're NOT Using:**
- ❌ GitPython - subprocess is simpler and more direct
- ❌ pydantic-settings - overkill for simple config
- ❌ click - typer is more modern
- ❌ argparse - typer handles it better

### 2. Configuration System

**Priority (highest to lowest):**
1. `YANA_*` environment variables
2. `./.yana/config.json` (project-local)
3. `~/.config/yana/config.json` (user default)

**No default `notes_dir`** - user must configure!

**Config Schema:**
```json
{
  "notes_dir": "/path/to/notes",
  "editor": "nvim",
  "git_enabled": true,
  "git_auto_commit": true,
  "git_auto_push": false,
  "git_commit_interval": 300,
  "watch_enabled": false,
  "fzf_preview": true,
  "fzf_preview_command": "bat --style=plain --color=always {}"
}
```

**Environment Variable Mapping:**
- `YANA_NOTES_DIR` → `notes_dir`
- `YANA_EDITOR` → `editor`
- `YANA_GIT_ENABLED` → `git_enabled`
- etc.

### 3. Note Structure

**File Format:**
```markdown
---
category: work-projects
tags: [meeting, action-items]
created: 2025-01-13T10:30:00
modified: 2025-01-13T15:45:00
---

# Meeting Notes

Content here...
```

**Frontmatter Fields:**
- `category` (string): Flat category (e.g., "work-projects", "personal-journal")
- `tags` (list): Freeform tags for filtering
- `created` (datetime): Auto-generated on creation
- `modified` (datetime): Auto-updated on save

**Note Data Class:**
```python
@dataclass(slots=True, frozen=True)
class Note:
    path: Path
    title: str
    category: str
    tags: list[str]
    content: str
    created_at: datetime
    modified_at: datetime
```

### 4. CLI Interface

**Command Name:** `yana` (primary), can alias to `jot` in shell

**Usage:**
```bash
# Browse all notes
yana

# Filter by category
yana --category work-projects
yana -c personal

# Open specific note or folder
yana /path/to/note.md
yana /path/to/folder

# Create new note (both args required!)
yana new "Meeting Notes" work-projects
yana new daily-standup team-sync

# Special commands
yana --daily        # Open journal/YYYY-MM-DD.md
yana --last         # Open last edited note
yana sync           # Manual git sync
yana config         # Show current config

# Help
yana --help
```

**Argument Design:**
- Use typer for automatic validation
- Require both filename and category for `new` command
- Support piping paths (read from stdin)

### 5. Category System

**Format:** Flat categories (not hierarchical)
- ✅ `work-projects`
- ✅ `personal-journal`
- ✅ `team-sync`
- ❌ NOT `work/projects` (no nesting)

**Rationale:**
- Simpler file organization
- Easier to filter and search
- Tags provide additional organization
- Can use dashes for pseudo-hierarchy if needed

**Daily Notes:**
- Location: `{notes_dir}/journal/YYYY-MM-DD.md`
- Category: `journal`
- Auto-created frontmatter with journal category

### 6. FZF Integration

**Display Format:**
```
[category] Title | #tag1 #tag2 | path/to/note.md
```

**Features:**
- Interactive filtering by category, tags, title
- Preview pane showing note content
- Multi-select support (future)
- Custom keybindings (future)

**Preview Command:**
```bash
# Prefer bat with syntax highlighting
bat --style=plain --color=always {}

# Fallback to cat
cat {}
```

**FZF Options:**
- `--preview` - Show file preview
- `--preview-window` - Preview pane size/position
- `--height 80%` - Terminal height
- `--multi` - Multi-select (optional)

### 7. Git Synchronization

**Strategy: Safe and Simple**

**Auto-commit (when enabled):**
1. User opens note in editor (blocking)
2. On editor exit, check if file modified
3. If modified: `git add <file> && git commit -m "Update: <filename>"`
4. If `git_auto_push=true`: `git push`

**Manual Sync Workflow:**
```python
def sync():
    # 1. Check for local changes
    if has_local_changes():
        stash_changes()

    # 2. Pull remote changes
    try:
        git pull --rebase
    except ConflictError:
        handle_conflicts()

    # 3. Apply stashed changes
    if stash_exists():
        try:
            git stash pop
        except ConflictError:
            create_conflict_backup()

    # 4. Commit and push
    if git_auto_commit:
        commit_all()
    if git_auto_push:
        push()
```

**Conflict Resolution:**
- Detect conflicts in `git stash pop`
- Create `<filename>.conflict.md` backup with remote version
- Keep local version in main file
- Notify user to manually resolve

**Git Commands (via subprocess):**
```python
# Check status
subprocess.run(["git", "status", "--porcelain"], capture_output=True)

# Add and commit
subprocess.run(["git", "add", file_path])
subprocess.run(["git", "commit", "-m", message])

# Sync
subprocess.run(["git", "stash", "push", "-u"])
subprocess.run(["git", "pull", "--rebase"])
subprocess.run(["git", "stash", "pop"])
subprocess.run(["git", "push"])
```

### 8. Editor Integration

**Editor Selection (priority):**
1. `YANA_EDITOR` env var
2. `editor` in config.json
3. `VISUAL` env var
4. `EDITOR` env var
5. Error: "No editor configured"

**Opening Files:**
```python
def open_in_editor(file_path: Path) -> bool:
    """
    Open file in editor (blocking).
    Returns True if file was modified.
    """
    editor = get_editor()
    initial_mtime = file_path.stat().st_mtime

    # Open editor (blocking call)
    result = subprocess.run([editor, str(file_path)])

    if result.returncode != 0:
        raise EditorError(f"Editor exited with code {result.returncode}")

    # Check if modified
    final_mtime = file_path.stat().st_mtime
    return final_mtime > initial_mtime
```

**Special Editor Handling:**
```python
# VS Code: need -w flag to wait
if 'code' in editor:
    subprocess.run([editor, '-w', file_path])

# Sublime: need -w flag
if 'subl' in editor:
    subprocess.run([editor, '-w', file_path])

# Vim, nvim, nano, etc: just work
else:
    subprocess.run([editor, file_path])
```

### 9. File Watching (Optional Feature)

**Use Case:** Auto-sync when files change externally

**Implementation:**
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class NoteWatcher(FileSystemEventHandler):
    def __init__(self, sync_callback, debounce=2.0):
        self.sync_callback = sync_callback
        self.debounce = debounce
        self.last_event = {}

    def on_modified(self, event):
        if not event.src_path.endswith('.md'):
            return

        # Debounce rapid changes
        now = time.time()
        if now - self.last_event.get(event.src_path, 0) < self.debounce:
            return

        self.last_event[event.src_path] = now
        self.sync_callback(event.src_path)
```

**When to Enable:**
- User working with external editors/tools
- Multiple devices syncing same notes
- Disabled by default (can be CPU intensive)

### 10. Markdown Rendering

**Decision: TBD**

**Option A: cat/bat (Current Plan)**
- Use `bat` if available for syntax highlighting
- Fallback to `cat`
- Pros: No extra rendering logic
- Cons: Limited styling

**Option B: Rich (Alternative)**
- Use `rich.markdown.Markdown`
- Pros: Beautiful rendering, syntax highlighting
- Cons: Rich already a dependency

**TODO:** Decide during implementation which feels better

### 11. Modern Python 3.13 Features

**Type Parameter Syntax (PEP 695):**
```python
def filter_notes[T](notes: list[T], predicate: Callable[[T], bool]) -> list[T]:
    return [n for n in notes if predicate(n)]
```

**Pattern Matching:**
```python
match (path, args.get('new'), args.get('daily')):
    case (None, True, _):
        create_new_note()
    case (None, _, True):
        open_daily_note()
    case (Path() as p, _, _) if p.is_file():
        open_note(p)
    case (Path() as p, _, _) if p.is_dir():
        browse_directory(p)
    case (None, False, False):
        browse_all_notes()
```

**Dataclasses with Slots:**
```python
@dataclass(slots=True, frozen=True)
class Config:
    notes_dir: Path
    editor: str
    git_enabled: bool = True
    git_auto_commit: bool = True
    git_auto_push: bool = False
```

**Type Aliases:**
```python
type NotePath = Path
type CategoryName = str
type NoteFilter = Callable[[Note], bool]
```

---

## Project Structure

```
yana/
├── pyproject.toml           # Modern Python packaging
├── README.md                # User documentation
├── CLAUDE.md               # This file - technical docs
├── TODO.md                  # Task breakdown
├── .python-version          # 3.13
├── .gitignore               # Python + IDE ignores
├── config.example.json      # Example config
├── src/
│   └── yana/
│       ├── __init__.py      # Package exports
│       ├── __main__.py      # Entry point: python -m yana
│       ├── cli.py           # Typer CLI commands
│       ├── config.py        # Config management (JSON + env)
│       ├── notes.py         # Note CRUD operations
│       ├── git.py           # Git operations via subprocess
│       ├── fzf.py           # FZF integration
│       ├── editor.py        # Editor integration
│       └── utils.py         # Helper functions
└── tests/
    ├── __init__.py
    ├── conftest.py          # Pytest fixtures
    ├── test_config.py
    ├── test_notes.py
    ├── test_git.py
    └── test_fzf.py
```

---

## Module Responsibilities

### `cli.py` - Command Line Interface
- Typer app definition
- Command handlers (main, new, sync, etc.)
- Argument parsing and validation
- Error display with Rich

### `config.py` - Configuration Management
- Load config from JSON + env vars
- Cascading config resolution
- Config validation
- Default config creation

### `notes.py` - Note Management
- Note dataclass
- NoteManager class
- CRUD operations (create, read, update, delete)
- Frontmatter parsing/writing
- Note listing and filtering
- Search functionality

### `git.py` - Git Integration
- GitSync class
- Auto-commit logic
- Sync workflow (stash/pull/pop/push)
- Conflict detection and resolution
- Git command execution via subprocess

### `fzf.py` - FZF Integration
- NoteFuzzyFinder class
- Format notes for FZF display
- Launch FZF with preview
- Parse FZF selection
- Filter by category/tags

### `editor.py` - Editor Integration
- Editor detection (env vars, config)
- Open file in editor (blocking)
- Detect file modifications
- Handle editor-specific flags

### `utils.py` - Utilities
- Date/time helpers
- Path validation
- Error classes
- Logging setup

---

## Error Handling

**Strategy: Fail Fast with Helpful Messages**

```python
class YanaError(Exception):
    """Base exception for YANA"""
    pass

class ConfigError(YanaError):
    """Configuration errors"""
    pass

class GitError(YanaError):
    """Git operation errors"""
    pass

class EditorError(YanaError):
    """Editor errors"""
    pass

class NoteError(YanaError):
    """Note operation errors"""
    pass
```

**Display Errors with Rich:**
```python
from rich.console import Console

console = Console()

try:
    do_something()
except ConfigError as e:
    console.print(f"[red]Config Error:[/red] {e}")
    console.print("[yellow]Run 'yana config' to set up configuration[/yellow]")
    sys.exit(1)
```

---

## Testing Strategy

**Unit Tests:**
- Config loading and validation
- Frontmatter parsing
- Note filtering and search
- Git command construction

**Integration Tests:**
- FZF integration (mock iterfzf)
- Editor opening (mock subprocess)
- Git operations (use temporary git repos)
- File watching (mock watchdog)

**Test Tools:**
- pytest
- pytest-cov (coverage)
- pytest-mock (mocking)

---

## Development Workflow

**Setup:**
```bash
# Install in editable mode
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/yana
```

**Git Workflow:**
- Feature branches
- Descriptive commit messages
- Keep main stable

---

## Performance Considerations

**Lazy Loading:**
- Don't load all notes on startup
- Load notes only when browsing
- Cache note list in memory during FZF session

**Git Operations:**
- Run git commands asynchronously (future)
- Don't block UI on slow network
- Show progress for long operations

**FZF Performance:**
- iterfzf streams items (no temp files)
- Efficient for thousands of notes
- Preview command should be fast (bat is fast)

---

## Security Considerations

**Git Authentication:**
- Use SSH keys (recommended)
- Support HTTPS with credential helper
- Never store passwords in config

**File Permissions:**
- Config files: 0600 (user read/write only)
- Notes: 0644 (user read/write, others read)

**Path Validation:**
- Always use pathlib.Path
- Validate paths before operations
- Prevent directory traversal

---

## Future Enhancements

**High Priority:**
- [ ] Content search (use ripgrep)
- [ ] Templates for new notes
- [ ] Recent notes list
- [ ] Tag cloud / statistics

**Medium Priority:**
- [ ] Note linking (`[[other-note]]`)
- [ ] Backlinks
- [ ] Export (HTML, PDF via pandoc)
- [ ] Attachments support

**Low Priority:**
- [ ] Encryption (GPG)
- [ ] Graph view (ASCII art)
- [ ] Plugin system
- [ ] Web UI (optional)

**Extras (from README):**
- [ ] Gruvbox colors theme
- [ ] Nerd fonts support
- [ ] File tree view
- [ ] Welcome dashboard
- [ ] Multiple themes
- [ ] Built-in editor?

---

## References

**Similar Tools:**
- `zk` - Zettelkasten CLI (Ruby/Rust)
- `nb` - Note-taking CLI (Bash)
- `notable` - Markdown notes app
- `joplin` - Cross-platform notes

**Libraries:**
- [Typer Docs](https://typer.tiangolo.com/)
- [Rich Docs](https://rich.readthedocs.io/)
- [iterfzf GitHub](https://github.com/dahlia/iterfzf)
- [PyYAML Docs](https://pyyaml.org/)
- [Watchdog Docs](https://python-watchdog.readthedocs.io/)

---

## Changelog

**2025-01-13:**
- Initial architecture design
- Minimal dependencies finalized
- Flat category system chosen
- Git sync strategy defined
- Project structure established
