# claude-config

My Claude Code setup: user instructions, rules, and a curated set of skills
vendored from other people's repos under names I chose.

## Why it works this way

Skill names are mine, not upstream's. `tdd` is currently superpowers'
`test-driven-development`; swapping in a different one means editing one line of
`sources.tsv` and re-vendoring, with no name to relearn and no CLAUDE.md edit.

Nothing is symlinked. `install` copies, so bare Windows works without
Developer Mode.

Nothing auto-applies. `check` reports and stops.

## Commands

    python cc.py vendor [name ...]   fetch upstream, record sha + content hash
    python cc.py install             copy this repo into the Claude config dir
    python cc.py check [--daily]     report drift, change nothing

`check` reports three things and fixes none of them:

- this repo is dirty, behind `origin`, or holds commits you never pushed
- an installed file under `~/.claude` no longer matches this repo
- an upstream skill's content moved past the recorded hash

The middle one is why a machine that never pulls still gets told. It runs from a
SessionStart hook, once per calendar day. `--local-only` skips the network.

## New machine

    git clone git@github.com:<you>/claude-config.git ~/Projects/claude-config
    cd ~/Projects/claude-config && python cc.py install

`install` fills this machine's Python path and repo path into the hook command,
so the same `settings.json` works on Arch, WSL, and Windows.

## Machine-local rules

`~/.claude/rules/` holds both kinds of file. Anything in this repo's `rules/`
is copied there and managed. Anything else you drop in is left alone: `install`
only deletes paths recorded in its own manifest. Work-only rules go there
untracked, with `paths:` frontmatter so they load only for matching files.

The one gap: `settings.json` has no user-level local override, so it is a single
tracked file. A machine that needs different settings needs another answer.

## Permission rules

Write Bash permission rules in space form — `Bash(uv run pytest *)`, not
`Bash(uv run pytest:*)`. The VSCode extension (observed on 2.1.195) silently
fails to match the colon form when the prefix is more than one word: every
matching command still prompts, and adding more colon rules changes nothing.
The standalone CLI matches both, so the forms are not interchangeable in
practice. Space form is also what the permission dialog writes when you pick
"Yes, don't ask again".

## Editing a skill

Edit it here, then `python cc.py install`. Editing the copy under `~/.claude`
works until the next install overwrites it, and `check` will tell you first.

Upstream edits that survive re-vendoring belong in `patches/<name>.patch`.
`patches/reflect.patch` drops a Codex platform note that references a pstack
file this repo does not vendor. If a patch stops applying, `vendor` says so
instead of silently skipping it.
