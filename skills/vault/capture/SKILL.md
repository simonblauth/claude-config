---
name: capture
description: Use when the user mentions something to keep for later, such as a task, an idea, a finding, or a reminder ("remember to", "note that", "idea:"), including mid-task in an unrelated repo.
---

# Capture

The vault lives at `$VAULT_DIR` (default `~/vault`). Its `CLAUDE.md` and `schema.yaml` hold the rules and formats. Read both before the first capture of a session. This skill holds the procedure only.

A capture is a quick save. Interrupt the user's current work as little as possible.

## Steps

1. Pull, as the vault's `CLAUDE.md` says under sync.
2. Split the message into items, and route each item:

   | Item | Destination |
   | --- | --- |
   | Task for a known project | That project's `## Next`. If Next already has 5 open tasks, put it under `## Ideas` and say so. |
   | Idea for a known project | That project's `## Ideas` |
   | Finding or event in a known project | A dated line in that project's `## Log` |
   | Anything with no clear project | `inbox.md`, as a dated line |

   Keep the user's wording. Add `due:` or `@owner` only when the user gave them.
3. Add one line per item under `## Captures` in today's daily note, linking to where the item went. If the note does not exist, create it with the sections from `CLAUDE.md`, all empty except Captures.
4. Commit all items from one message as one commit, `Capture: <short summary>`, and push.
5. Reply with one line per item, naming where it went. Then return to the work at hand.

Write vault content only into the vault. The current repo, its commits, and its issues stay free of it.
