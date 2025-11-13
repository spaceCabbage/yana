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

# Auto-commit and auto-push happen after editing
# If network unavailable, changes are committed locally with graceful message
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

## Troubleshooting

### Git Authentication Errors

If you see authentication errors when syncing:

```bash
# For SSH (recommended)
ssh-keygen -t ed25519 -C "your_email@example.com"
ssh-add ~/.ssh/id_ed25519
# Add the public key to your GitHub/GitLab account

# For HTTPS
# Configure git credential helper
git config --global credential.helper store
```

### Network Errors

YANA provides helpful error messages for network issues:

- **"Could not resolve hostname"** - Check your internet connection and DNS settings
- **"Could not connect to remote"** - Verify your remote URL: `git remote -v`
- **"SSL certificate error"** - Your system may have outdated CA certificates
- **"Authentication failed"** - Check your SSH keys or HTTPS credentials

### FZF Not Found

YANA uses `iterfzf` which bundles the fzf binary, so you don't need to install fzf separately. If you still encounter issues:

```bash
# Reinstall yana
pip uninstall yana
pip install -e .
```

### Editor Not Opening

If your editor doesn't open:

1. **Check editor is installed**: `which nvim` (or your editor)
2. **Set YANA_EDITOR**: `export YANA_EDITOR="nvim"`
3. **For VS Code**: Use `code -w` to wait for window to close
4. **For Sublime**: Use `subl -w` to wait for window to close

YANA automatically handles wait flags for common editors.

### Configuration Errors

```bash
# Check current configuration
yana config

# Verify notes directory exists
ls -la ~/notes

# Check config file
cat ~/.config/yana/config.json

# Override with environment variables
export YANA_NOTES_DIR="$HOME/notes"
export YANA_EDITOR="nvim"
```

### Sync Conflicts

If git sync conflicts occur:

1. YANA creates `.conflict.md` backup files with remote versions
2. Your local version remains in the main file
3. Manually resolve conflicts and run:

```bash
yana sync
```

### Quiet Mode

To suppress output messages (useful for scripts):

```bash
yana --quiet
yana new "Note" category --quiet
yana sync --quiet
```

### Logs

Check logs for detailed error information:

```bash
# View logs
tail -f ~/.config/yana/yana.log

# Enable debug logging
export YANA_LOG_LEVEL="DEBUG"
yana --daily
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

See [TODO.md](TODO.md) for the complete task list with granular breakdown.

---

**YANA** - *Keep your notes simple, fast, and synced* 📝
