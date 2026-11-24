# Codex tool mapping for reflection

Adapted from pstack's Codex mapping; upstream provenance is tracked in
`support-sources.tsv` and `NOTICE.md` in the source repository.

| Workflow action | Codex behavior |
| --- | --- |
| Read, search, or execute | Use the available file, search, and shell tools. |
| Edit a file | Use the available patch or editing tool. |
| Load a named skill | Read its discovered `SKILL.md` and follow it. |
| Ask the user | Use a question tool when available and applicable; otherwise ask in plain text. |
| Load instructions | Read applicable `AGENTS.md` files and configured fallbacks, including global instructions. |

Tool availability and argument names vary between Codex surfaces. Use
[runtime.md](runtime.md) for this skill's transcript procedure.
