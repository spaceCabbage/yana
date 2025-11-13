# YANA - Yet Another Notes App

> A lean, modern CLI markdown notes manager with FZF and git sync

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **FZF Integration** - Fast, fuzzy finding of notes with preview
- **Git Sync** - Automatic commit, pull, and push with conflict handling
- **Frontmatter** - YAML frontmatter for categories and tags
- **Configurable** - JSON config + environment variables
- **Editor Agnostic** - Use your favorite editor (vim, nvim, VS Code, etc.)
- **Daily Notes** - Quick journaling with `--daily`
- **Modern Python** - Built with Python 3.13+ features

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/yana.git
cd yana

# Install in editable mode
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

## Quick Start

### 1. Configure YANA

Create a config file at `~/.config/yana/config.json`:

```json
{
  "notes_dir": "~/notes",
  "editor": "nvim",
  "git_enabled": true,
  "git_auto_commit": true,
  "git_auto_push": false
}
```

Or use environment variables:

```bash
export YANA_NOTES_DIR="$HOME/notes"
export YANA_EDITOR="nvim"
export YANA_GIT_ENABLED="true"
```

### 2. Initialize Your Notes Directory

```bash
# Create notes directory
mkdir -p ~/notes
cd ~/notes

# Initialize git (optional but recommended)
git init
```

### 3. Start Using YANA

```bash
# Browse all notes in FZF
yana

# Create a new note
yana new "Meeting Notes" work-projects

# Open today's journal
yana --daily

# Filter by category
yana --category work-projects

# Open last edited note
yana --last

# Manual git sync
yana sync

# Show current config
yana config
```

## Usage Examples

### Browse Notes

```bash
# Open FZF to browse all notes
yana

# Browse notes in a specific category
yana --category personal

# Open a specific note
yana ~/notes/meeting-notes.md

# Browse a specific folder
yana ~/notes/work/
```

### Create Notes

```bash
# Create a new note (requires title and category)
yana new "Daily Standup" team-sync

# Create with tags
yana new "Project Ideas" brainstorm --tag ideas --tag todo
```

### Daily Notes

```bash
# Open or create today's journal entry
yana --daily

# This creates: ~/notes/journal/YYYY-MM-DD.md
```

### Git Sync

```bash
# Manually sync notes (commit, pull, push)
yana sync

# Auto-sync happens on editor close if enabled in config
```

## Configuration

### Config File Locations (Priority Order)

1. `$YANA_CONFIG` - Environment variable pointing to config file
2. `./.yana/config.json` - Project-local config
3. `~/.config/yana/config.json` - User config (created automatically)

### Configuration Options

| Option                | Type    | Default                                 | Description                     |
|-----------------------|---------|-----------------------------------------|---------------------------------|
| `notes_dir`           | string  | *required*                              | Path to notes directory         |
| `editor`              | string  | `"vim"`                                 | Editor command                  |
| `git_enabled`         | boolean | `true`                                  | Enable git sync                 |
| `git_auto_commit`     | boolean | `true`                                  | Auto-commit on save             |
| `git_auto_push`       | boolean | `false`                                 | Auto-push commits               |
| `git_commit_interval` | integer | `300`                                   | Auto-commit interval (seconds)  |
| `watch_enabled`       | boolean | `false`                                 | Watch for external file changes |
| `fzf_preview`         | boolean | `true`                                  | Show preview in FZF             |
| `fzf_preview_command` | string  | `"bat --style=plain --color=always {}"` | Preview command                 |

### Environment Variables

All config options can be set via environment variables with the `YANA_` prefix:

```bash
export YANA_NOTES_DIR="$HOME/notes"
export YANA_EDITOR="nvim"
export YANA_GIT_ENABLED="true"
export YANA_GIT_AUTO_COMMIT="true"
export YANA_GIT_AUTO_PUSH="false"
```

## Note Format

Notes are markdown files with YAML frontmatter:

```markdown
---
category: work-projects
tags: [meeting, action-items]
created: 2025-01-13T10:30:00
modified: 2025-01-13T15:45:00
---

# Meeting Notes

## Attendees
- Alice
- Bob

## Action Items
- [ ] Review proposal
- [ ] Schedule follow-up
```

### Frontmatter Fields

- **category** (string): Flat category name (e.g., `work-projects`, `personal-journal`)
- **tags** (list): Freeform tags for filtering
- **created** (datetime): Auto-generated creation timestamp
- **modified** (datetime): Auto-updated modification timestamp

## Architecture

YANA is built with modern Python 3.13 features and minimal dependencies:

### Dependencies (5 lean libraries)

- **iterfzf** - FZF integration (bundles fzf binary)
- **typer** - Modern CLI framework
- **pyyaml** - YAML frontmatter parsing
- **rich** - Beautiful terminal output
- **watchdog** - File system monitoring

### Project Structure

```
yana/
├── src/yana/
│   ├── cli.py       # Typer CLI commands
│   ├── config.py    # Configuration management
│   ├── notes.py     # Note operations
│   ├── git.py       # Git integration
│   ├── fzf.py       # FZF integration
│   ├── editor.py    # Editor integration
│   └── utils.py     # Utilities
├── tests/           # Test suite
├── CLAUDE.md        # Technical architecture docs
├── TODO.md          # Implementation roadmap
└── pyproject.toml   # Project configuration
```

## Development

See [TODO.md](TODO.md) for detailed implementation tasks and [CLAUDE.md](CLAUDE.md) for architecture decisions.

### Setup Development Environment

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=yana --cov-report=html

# Type checking
mypy src/yana

# Code formatting
black src/yana tests

# Linting
ruff check src/yana tests
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=yana

# Run specific test file
pytest tests/test_notes.py

# Run with verbose output
pytest -v
```

## Roadmap

### Phase 1: Core MVP ✅
- [x] Project structure
- [x] Configuration system
- [x] Note management
- [x] FZF integration skeleton
- [x] Editor integration skeleton
- [x] Git integration skeleton
- [x] CLI commands skeleton

### Phase 2: Core Functionality (In Progress)
- [ ] Complete note CRUD operations
- [ ] Complete FZF browsing
- [ ] Complete editor integration
- [ ] Complete git sync workflow
- [ ] Daily notes
- [ ] Category filtering
- [ ] Last edited note

### Phase 3: Advanced Features
- [ ] Content search (ripgrep/grep)
- [ ] Tag filtering
- [ ] Templates for new notes
- [ ] File watching
- [ ] Statistics command

### Phase 4: Polish
- [ ] Gruvbox colors theme
- [ ] Nerd fonts support
- [ ] Rich markdown rendering
- [ ] File tree view
- [ ] Welcome dashboard

See [TODO.md](TODO.md) for the complete task list with granular breakdown.

---

**YANA** - *Keep your notes simple, fast, and synced* 📝
