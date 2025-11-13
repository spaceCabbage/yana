# YANA - Implementation TODO

**Last Updated**: 2025-01-13
**Status**: 🚧 In Progress

---

## Phase 1: Project Setup

- [x] Create project structure
- [x] Create CLAUDE.md with architecture decisions
- [x] Create TODO.md (this file)
- [x] Update pyproject.toml with dependencies
- [x] Create .gitignore
- [x] Create config.example.json
- [x] Create src/ directory structure
- [x] Create __init__.py files
- [ ] Set up .python-version file (3.13)

---

## Phase 2: Core Infrastructure

### Configuration System (config.py)
- [x] Create Config dataclass with all settings
- [x] Implement JSON config file loading
- [x] Implement environment variable override
- [x] Implement config file search (YANA_CONFIG → ./.yana → ~/.config/yana)
- [x] Add config validation
- [x] Add create_default_config() function
- [x] Add get_config() singleton function
- [x] Handle missing notes_dir error gracefully
- [x] Add config command to show current config

### Data Models (notes.py)
- [x] Create Note dataclass with slots
- [x] Add Note.from_file() class method
- [x] Add Note.save() method
- [ ] Add Note.update_frontmatter() method
- [x] Implement frontmatter parsing (PyYAML)
- [x] Implement frontmatter writing
- [x] Add created/modified timestamp handling
- [x] Add title extraction from filename

### Utilities (utils.py)
- [x] Create custom exception classes (YanaError, ConfigError, etc.)
- [x] Add date/time helper functions
- [x] Add path validation functions
- [x] Add file existence checks
- [x] Add Rich console singleton
- [ ] Add logging setup function

---

## Phase 3: Note Management

### Note Operations (notes.py - NoteManager class)
- [x] Create NoteManager class
- [x] Implement list_all_notes() - scan directory for .md files
- [x] Implement get_note(path) - load single note
- [x] Implement create_note(title, category, tags) - new note with frontmatter
- [ ] Implement update_note(note) - save changes
- [ ] Implement delete_note(path) - remove note
- [x] Implement filter_by_category(category) - filter notes list
- [x] Implement filter_by_tags(tags) - filter notes list
- [x] Implement search_by_title(query) - search note titles
- [x] Add get_last_edited_note() - find most recently modified
- [x] Add note path generation (category-based)
- [x] Handle duplicate note names gracefully

### Daily Notes
- [x] Implement get_daily_note(date) - get or create daily note
- [x] Add daily note path generation (journal/YYYY-MM-DD.md)
- [x] Auto-create journal directory if needed
- [x] Set category to "journal" for daily notes
- [x] Add date to frontmatter automatically

---

## Phase 4: Editor Integration

### Editor Module (editor.py)
- [x] Create get_editor() function with priority chain
- [x] Support YANA_EDITOR env var
- [x] Support config.editor
- [x] Support VISUAL env var
- [x] Support EDITOR env var
- [x] Raise error if no editor configured
- [x] Implement open_in_editor(path) - blocking call
- [x] Track file modification time before/after editing
- [x] Return boolean indicating if file was modified
- [x] Handle editor-specific flags (code -w, subl -w)
- [x] Handle editor exit codes
- [x] Display error if editor fails

---

## Phase 5: FZF Integration

### FZF Module (fzf.py)
- [x] Create NoteFuzzyFinder class
- [x] Implement format_note_for_fzf(note) - display format
- [x] Format: `[category] Title | #tags | path`
- [x] Implement select_note(notes, category_filter) - single select
- [x] Add FZF preview pane configuration
- [x] Add preview command (bat with fallback to cat)
- [x] Check for bat availability
- [x] Implement parse_selection() - extract note from FZF output
- [x] Add category filtering in FZF prompt
- [x] Add tag filtering in FZF prompt
- [x] Handle FZF cancellation (None return)
- [x] Add FZF options (height, preview-window, etc.)

### Markdown Preview
- [ ] **TODO: Decide rendering approach** (bat vs rich)
- [ ] If bat: implement preview with bat command
- [ ] If rich: implement rich.markdown rendering
- [ ] Add preview command customization in config
- [ ] Test preview with code blocks
- [ ] Test preview with tables
- [ ] Test preview with links

---

## Phase 6: Git Integration

### Git Module (git.py)
- [x] Create GitSync class
- [x] Implement init_repo(path) - check if git repo exists
- [ ] Implement is_git_enabled() - check config + repo existence
- [x] Implement has_local_changes() - check git status
- [x] Implement has_remote_changes() - check if behind origin
- [x] Implement commit_file(path, message) - single file commit
- [x] Implement commit_all(message) - commit all changes
- [x] Implement push() - git push
- [x] Implement pull() - git pull --rebase
- [x] Implement stash_changes() - git stash push -u
- [x] Implement pop_stash() - git stash pop
- [x] Implement handle_conflicts() - detect and create .conflict backups
- [x] Add proper error handling for git commands
- [x] Add timeout for git operations
- [ ] Add network error detection

### Auto-Sync Workflow
- [ ] Implement sync_before_edit() - pull if needed
- [ ] Implement sync_after_edit(modified) - commit + push if modified
- [ ] Add auto-commit message generation
- [ ] Add git_auto_push config check
- [ ] Test sync with no remote
- [ ] Test sync with conflicts
- [ ] Test sync with network failure

---

## Phase 7: CLI Commands

### Main CLI (cli.py)
- [x] Create Typer app instance
- [x] Add rich console for pretty output
- [x] Implement main() command - browse all notes (skeleton)
- [x] Add --category/-c option for filtering
- [x] Add path argument for specific note/folder
- [x] Implement new command - create note (skeleton, requires title + category)
- [x] Implement --daily option - open today's journal (skeleton)
- [x] Implement --last option - open last edited note (skeleton)
- [x] Implement sync command - manual git sync (skeleton)
- [x] Implement config command - show current configuration
- [x] Add --help with examples
- [x] Add version command (from __version__)
- [x] Handle missing config error
- [ ] Handle no notes found error
- [x] Handle keyboard interrupts gracefully (Ctrl+C)

### CLI Flow Logic
- [ ] Implement browse_all_notes() - launch FZF with all notes
- [ ] Implement browse_with_category_filter(category) - filtered FZF
- [ ] Implement browse_directory(path) - FZF for specific folder
- [ ] Implement open_specific_note(path) - direct editor open
- [ ] Add git sync before opening note
- [ ] Add git sync after closing editor
- [ ] Handle FZF cancellation (exit gracefully)
- [ ] Handle editor failures

---

## Phase 8: File Watching (Optional)

### Watchdog Integration (notes.py or separate module)
- [ ] Create NoteWatcher class (FileSystemEventHandler)
- [ ] Implement on_modified() handler
- [ ] Add debouncing for rapid changes (2s default)
- [ ] Filter for .md files only
- [ ] Trigger sync callback on changes
- [ ] Add watch_enabled config option
- [ ] Start/stop observer based on config
- [ ] Handle watch errors gracefully
- [ ] Test with external editor changes

---

## Phase 9: Search & Filtering

### Content Search
- [ ] Add search_content(query) - search note bodies
- [ ] Use ripgrep if available (faster)
- [ ] Fallback to grep
- [ ] Fallback to Python search if no external tools
- [ ] Display search results in FZF
- [ ] Show context around matches
- [ ] Add --search/-s CLI option

### Advanced Filtering
- [ ] Add filter_by_multiple_tags(tags) - AND logic
- [ ] Add filter_by_any_tag(tags) - OR logic
- [ ] Add date range filtering (created/modified)
- [ ] Add --tag option to CLI
- [ ] Add --since option for date filtering

---

## Phase 10: Polish & UX

### Error Handling
- [ ] Add helpful error messages for all errors
- [ ] Show config path in ConfigError
- [ ] Show git command output in GitError
- [ ] Add suggestions for common errors
- [ ] Color code errors (red), warnings (yellow), info (blue)

### User Feedback
- [ ] Add success messages for operations
- [ ] Show spinner for slow git operations
- [ ] Add progress bars for long operations
- [ ] Show git sync status
- [ ] Add quiet mode (--quiet/-q)

### Documentation
- [x] Add docstrings to all functions
- [x] Add type hints everywhere
- [ ] Add inline comments for complex logic
- [x] Create comprehensive README examples
- [ ] Add troubleshooting section to README
- [x] Add configuration examples

### Testing
- [ ] Write unit tests for config loading
- [ ] Write unit tests for note operations
- [ ] Write unit tests for frontmatter parsing
- [ ] Write integration tests for git sync
- [ ] Write integration tests for FZF
- [ ] Add test fixtures for sample notes
- [ ] Set up CI/CD (GitHub Actions?)

---

## Later/Extra Features

### Enhancements
- [ ] Templates system for new notes
- [ ] Create ~/.config/yana/templates/ directory
- [ ] Load template based on category or default
- [ ] Variable substitution in templates ({{title}}, {{date}}, etc.)
- [ ] Template command to manage templates

### Content Search (ripgrep/grep)
- [ ] Implement full-text content search across all notes
- [ ] Use ripgrep if available (much faster)
- [ ] Fallback to grep
- [ ] Show context lines around matches
- [ ] Highlight search terms in results
- [ ] Add --search command to CLI

### Statistics & Analytics
- [ ] Implement stats command
- [ ] Show note count by category
- [ ] Show tag cloud (frequency)
- [ ] Show notes per day/week/month
- [ ] Show most edited notes
- [ ] Export statistics as JSON

### Note Linking & Backlinks
- [ ] Parse wiki-style links `[[note-name]]`
- [ ] Track links between notes
- [ ] Implement backlinks (which notes link here)
- [ ] Add graph command to show connections
- [ ] Auto-update links on note rename

### Export Features
- [ ] Export note to HTML (pandoc)
- [ ] Export note to PDF (pandoc)
- [ ] Export category to archive (zip/tar)
- [ ] Export all notes with formatting

### Attachments
- [ ] Support attachments folder per note
- [ ] Auto-copy attachments to notes directory
- [ ] Relative path links in markdown
- [ ] Attachment management commands

### Visual Enhancements (from README extras)
- [ ] **Gruvbox color theme** - implement as theme in Rich
- [ ] **Nerd fonts support** - use icons for categories/tags
- [ ] **File tree view** - ASCII tree of note categories
- [ ] **Welcome dashboard** - stats + recent notes on startup
- [ ] **Multiple themes** - theme system with config
- [ ] **Render markdown prettily** - rich markdown with edit button
- [ ] Built-in editor? (probably not, but considering it)

### Advanced Git Features
- [ ] Git branch support (work on feature branches)
- [ ] Git history browser (see note history)
- [ ] Restore previous versions
- [ ] Compare note versions (diff)
- [ ] Merge conflict resolution UI

### Performance
- [ ] SQLite indexing for large note collections (1000+ notes)
- [ ] Full-text search index
- [ ] Cache note metadata
- [ ] Lazy loading for large directories
- [ ] Background sync (non-blocking)

### Multi-Repository Support
- [ ] Support multiple note repositories
- [ ] Switch between repos (yana switch <repo>)
- [ ] Config per repo
- [ ] List all configured repos

### Encryption
- [ ] GPG encryption for sensitive notes
- [ ] Encrypt/decrypt on the fly
- [ ] Support for .gpg files
- [ ] Key management

### Collaboration
- [ ] Conflict resolution UI
- [ ] Show who last edited (git blame)
- [ ] Comment system (via git notes?)
- [ ] Shared notes (team wiki mode)

### Web Interface (Ambitious)
- [ ] Optional web UI for browsing
- [ ] Markdown rendering in browser
- [ ] Real-time sync via websockets
- [ ] Mobile-friendly interface

### Plugin System (Very Ambitious)
- [ ] Plugin architecture
- [ ] Custom commands
- [ ] Custom filters
- [ ] Custom themes
- [ ] Community plugins

---

## Bugs to Watch For

### Git Sync Issues
- [ ] Test with no internet connection
- [ ] Test with SSH key authentication
- [ ] Test with HTTPS authentication
- [ ] Test with large files
- [ ] Test with binary files
- [ ] Test with rapid consecutive edits
- [ ] Test merge conflicts
- [ ] Test divergent branches

### FZF Issues
- [ ] Test with 0 notes
- [ ] Test with 10,000+ notes
- [ ] Test with very long note titles
- [ ] Test with special characters in filenames
- [ ] Test with unicode in filenames
- [ ] Test cancellation (Esc)

### Editor Issues
- [ ] Test with vim
- [ ] Test with nvim
- [ ] Test with nano
- [ ] Test with VS Code
- [ ] Test with Sublime Text
- [ ] Test with emacs
- [ ] Test editor crash/kill
- [ ] Test editor not found

### Config Issues
- [ ] Test with no config file
- [ ] Test with invalid JSON
- [ ] Test with missing required fields
- [ ] Test with invalid paths
- [ ] Test with permission errors
- [ ] Test environment variable override

### Cross-Platform Issues
- [ ] Test on Linux
- [ ] Test on macOS
- [ ] Test on Windows
- [ ] Test path separators
- [ ] Test line endings (CRLF vs LF)
- [ ] Test unicode filenames

---

## Done ✅

- [x] Create CLAUDE.md with architecture
- [x] Create TODO.md with task breakdown
- [x] Define minimal dependency list
- [x] Design CLI interface
- [x] Design config system
- [x] Design note structure
- [x] Design git sync strategy
- [x] Reorganize to flat src/ package structure
- [x] Implement all core modules (config, notes, git, fzf, editor, utils)
- [x] Create comprehensive README with examples
- [x] Simplify pyproject.toml
- [x] Add python-frontmatter dependency

---

## Notes

### Decisions to Make During Implementation
1. **Markdown rendering**: bat vs rich.markdown
2. **Async git**: Should git operations be async?
3. **Cache strategy**: In-memory vs SQLite for large collections
4. **Template format**: Jinja2 vs simple string substitution

### Installation Instructions (to add to README)
```bash
# Install from source
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"

# Run yana
yana

# Or using python module
python -m yana
```

### Configuration Example (to add to README)
```json
{
  "notes_dir": "~/notes",
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

### Environment Variables
```bash
export YANA_NOTES_DIR="$HOME/notes"
export YANA_EDITOR="nvim"
export YANA_GIT_ENABLED="true"
export YANA_GIT_AUTO_PUSH="false"
```
