# NOTICE

`cc.py vendor` writes this file from `sources.tsv` and the license texts
under `licenses/`. Edits here are overwritten.

Most skills under `skills/` come from the repositories below. Each
upstream license is reproduced verbatim in `licenses/` and covers the
skills named beside it. Everything else, `cc.py` and `CLAUDE.md` and any
skill with no row here, is covered by `LICENSE`.

| Skills | Upstream | Copyright | License |
| --- | --- | --- | --- |
| `deslopify` | <https://github.com/JuliusBrussee/skills> | Copyright (c) 2026 Julius Brussee | [MIT License](licenses/JuliusBrussee-skills.txt) |
| `codebase-design`, `domain-modeling`, `grill-me`, `grill-with-docs`, `grilling`, `handoff`, `improve-codebase-architecture`, `wait-what`, `wizard`, `writing-for-agents` | <https://github.com/mattpocock/skills> | Copyright (c) 2026 Matt Pocock | [MIT License](licenses/mattpocock-skills.txt) |
| `reflect`, `technical-writing`, `unslop` | <https://github.com/michael-denyer/pstack-claude> | Copyright (c) 2026 Lauren Tan | [MIT License](licenses/michael-denyer-pstack-claude.txt) |
| `systematic-debugging`, `tdd`, `verification-before-completion`, `writing-skills` | <https://github.com/obra/superpowers> | Copyright (c) 2025 Jesse Vincent | [MIT License](licenses/obra-superpowers.txt) |

## Provenance: pstack-claude

`pstack-claude` is itself a port of MIT-licensed work, and its `LICENSE` carries
the original author's copyright rather than the porter's. Per that repository's
[NOTICE.md](https://github.com/michael-denyer/pstack-claude/blob/main/NOTICE.md),
the three skills vendored here trace back to
[cursor/plugins](https://github.com/cursor/plugins) `pstack`, copyright (c) 2026
Lauren Tan: `reflect` and `unslop` from commit `e46364b`, `technical-writing`
from `4612556`. None of them come from that repository's `cursor-team-kit`
imports, so the separate Cursor copyright in its `LICENSE-cursor-team-kit` does
not reach this repository.
