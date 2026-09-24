# claude-config

Shared instructions and curated skills for Claude Code and Codex. Most skills
are vendored under stable local names; a few are written here. Installations
copy files, with no symlinks or automatic updates.

## Install and check

Requires [uv](https://docs.astral.sh/uv/) and Git. uv supplies Python 3.11+,
and the startup hooks run `cc.py` through it.

```sh
uv run --script cc.py install --target all
uv run --script cc.py check --target all --local-only
uv run --script cc.py vendor [name ...]
```

`--target` accepts `claude`, `codex`, or `all`; it defaults to `claude` for
existing commands and hooks. `vendor` updates the shared sources for both.

| Content | Claude Code | Codex |
| --- | --- | --- |
| Global instructions | `~/.claude/CLAUDE.md` | `~/.codex/AGENTS.md` |
| Skills | `~/.claude/skills/` | `~/.agents/skills/` |
| Settings | `~/.claude/settings.json` | `~/.codex/config.toml` |
| Startup drift check | inside settings | `~/.codex/hooks.json` |

`CLAUDE_CONFIG_DIR` and `CODEX_HOME` override the respective configuration roots.
`CODEX_SKILLS_DIR` overrides this installer's Codex skill destination for testing
or a custom layout; it does **not** configure Codex discovery. Use a directory
Codex already scans. Changing `CODEX_HOME` does not move `~/.agents/skills/`.

Each destination has its own ownership manifest. Installation removes only
obsolete paths in that manifest and leaves unrelated files alone. Existing
files at managed instruction and skill paths are replaced. Claude's existing
manifest remains valid.

`check` reports repository, installed-file, attribution, and upstream drift.
It applies no updates; `--daily` throttles each runtime separately to once per
calendar day, and `--local-only` skips network checks. Startup hooks run the
check with the appropriate target. **After installing Codex, review and trust
its hook with `/hooks`**; Codex requires review again when the hook changes.
[Codex hook documentation](https://learn.chatgpt.com/docs/hooks)

## Instructions and settings

Edit `instructions/shared.md` for common policy and `instructions/claude.md`
or `instructions/codex.md` for runtime-specific guidance. Installation combines
them into the appropriate global instruction file. The root `AGENTS.md` governs
this repository; root `CLAUDE.md` points to it.

`settings/codex.toml` supplies managed root-level Codex settings. Currently it
adds `CLAUDE.md` to `project_doc_fallback_filenames`, preserving existing fallback
names and their order. Codex uses that fallback only when the same directory
has no applicable `AGENTS.override.md` or `AGENTS.md`.
[Instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

The Codex settings merge preserves unrelated settings, tables, and comments.
Its hook merge preserves other handlers. Models, permissions, and MCP settings
remain machine-local. Claude's `settings.json` is managed as before, except its
installed model, effort level, and model settings take precedence.

Claude-only `rules/` files are copied into the Claude rules directory; other
files there remain machine-local. For Codex, the installed instructions ask the
agent to read `$CODEX_HOME/local-instructions.md` if present (default
`~/.codex/local-instructions.md`). That file is not managed. Write file scopes
as explicit conditions there; Claude `paths:` rules are not converted.

## Claude permission rules

Write Bash permission rules in space form — `Bash(uv run pytest *)`, not
`Bash(uv run pytest:*)`. The VSCode extension (observed on 2.1.195) silently
fails to match the colon form when the prefix is more than one word: every
matching command still prompts, and adding more colon rules changes nothing.
The standalone CLI matches both, so the forms are not interchangeable in
practice. Space form is also what the permission dialog writes when you pick
"Yes, don't ask again".


## Editing and updating skills

Edit shared skills under `skills/`, then reinstall the desired target. For a
vendored skill, also record the edit in the appropriate patch so re-vendoring
preserves it. Patches use paths relative to the skill directory:

1. `sources.tsv`: upstream directory, revision, and pristine content hash.
2. `support-sources.tsv`: additional upstream files needed by a skill, including
   the pstack Codex mapping. The first column is the destination under `skills/`.
3. `patches/content/<name>.patch`: workflow and editorial customizations.
4. `patches/compat/shared/<name>.patch`: portability changes used by both agents.
5. `patches/compat/{claude,codex}/<name>.patch`: runtime-specific additions or edits.

`vendor` applies steps 1–4 into the checked-in shared skill tree and verifies
both target patch sets before publishing the batch. `install` and `check`
apply step 5 in temporary directories. A failed patch stops the operation;
installation renders both requested targets before writing either one.

Codex patches move explicit-only invocation policy into `agents/openai.yaml`,
remove Claude-specific frontmatter, and preserve argument hints in the body.
`reflect` and `review-loop` receive separate runtime guides. Codex reflection
uses an explicitly supplied readable current-session transcript or a labeled
conversation digest; it does not run Claude's transcript parser. The review
loop requires a fresh independent reviewer and reports when that is unavailable.
[Codex skill metadata](https://learn.chatgpt.com/docs/build-skills)

Pstack remains sourced from `michael-denyer/pstack-claude`. Its supporting Codex
mapping is pinned, attributed, patched, and drift-checked along with the skills.

## Verification

```sh
uv run --no-project --python '>=3.11' python -m unittest discover -s tests -v
```

Tests use temporary installation roots and cover both targets, repeated installs,
configuration preservation, drift, owned-file cleanup, patch failures, and
legacy Claude manifests. The pinned-source reproduction test also runs when
the upstream commits are present in `.cache/`; otherwise it reports a skip.
When Codex is installed and supports `debug prompt-input`, a local discovery
test checks global instructions, the project fallback, and invocation policy
without running a model.

## License

MIT, in `LICENSE`. Vendored licenses are reproduced under `licenses/`.
`vendor` rebuilds `NOTICE.md` from both source tables and license notes;
`check` reports missing licenses or a stale notice. Per-source prose belongs
in `licenses/<slug>.note.md`.
