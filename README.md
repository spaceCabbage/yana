# YANA - Yet another notes app


this app will
- manage mnarkdown notes
- use frontmatter for categrory 
- configurable notes folder and other settings via config file (read first from environment variable, then root of project, then from ~/.config/jot/)
- configurable editor
- git sync toggle config
- git sync on save file/exit editor
- fzf searching by name or category
- can pipe a path to open it (folders in fzf, files in editor)
- or pipe a list of paths to open all in fzf

usages
```sh
jot # opens fzf in main notes repo folder
jot /path/to/notes folder # opens fzf in that folder showing markdown files
jot /path/to/file # opens (and creates new) note 
```

## Implenentation steps
- [ ] setup app structure
- [ ] read env vars/config file
- [ ] read notes folder on start
- [ ] dispay in fzf
- [ ] markdown preview in fzf
- [ ] filter by name or category in fzf
- [ ] open in editor
- [ ] auto commit to git (if enabled) when exiting editor or in intervals (allow fopr user to decide)
- [ ] auto stash, pull and apply and commit and push when there are changes in wrking tree and remote changes, basically we need to gracefully sync
- [ ] setup cli args: help, new, paths, piping, last, etc

## Extras
- [ ] render markdown prettily in terminal when file is opned and have a buttno to "edit" which then opens in edotr, saving and exiting edotr synx to git and goes back to rendering the markdown
- [ ] filetree
- [ ] welcome dashboard
- [ ] themes
- [ ] built in editor?