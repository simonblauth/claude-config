## Codex

Project instructions live in `AGENTS.md`; `CLAUDE.md` is configured as a fallback
when the directory has no `AGENTS.md` or `AGENTS.override.md`.

Machine-local instructions can live in `$CODEX_HOME/local-instructions.md`
(default `~/.codex/local-instructions.md`). Read it if present. This installer
does not manage that file. State file scopes explicitly; these are instruction
conditions, not Claude-style `paths:` frontmatter.

Load named skills from the session's skill catalog and follow their `SKILL.md`.
Resolve supporting files relative to that installed skill directory. Use the
available question tool when applicable, otherwise ask in plain text. Never
assume a Claude tool name or model identifier is accepted by Codex.
