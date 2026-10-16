## Claude Code

Project instructions live in `CLAUDE.md`. Machine-local and language-specific
rules live in `~/.claude/rules/` (or `$CLAUDE_CONFIG_DIR/rules/`), with `paths:`
frontmatter for file-scoped rules. Auto memory is disabled in the installed settings.

The owned-remotes file is `owned-remotes.md` in that rules directory. It loads
with the other rules.

Load skills through the Skill tool. Resolve each supporting file relative to the
loaded skill's directory, not the working repository.
