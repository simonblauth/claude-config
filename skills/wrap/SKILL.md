---
name: wrap
description: Use when the user ends the workday or the week, says they are wrapping up or done for today, or asks to close out the day or week in the vault.
---

# Wrap

The vault lives at `$VAULT_DIR` (default `~/vault`). Its `CLAUDE.md` and `schema.yaml` hold the rules and formats. Read both first. This skill holds the procedure only.

## Pick the mode

- **Week wrap**: today is the last workday of the week, or the user says the week is over.
- **Day wrap**: otherwise.

## Steps

1. Pull, as the vault's `CLAUDE.md` says under sync.
2. Gather:
   - today's daily note
   - what the user reports in their message
   - optional: the user's merged PRs and pushed commits from today, through `gh`
   - `inbox.md` and today's Captures
3. Record what the user reported or confirmed, as normal commits:
   - Done tasks leave Next and become Log lines, as `CLAUDE.md` describes. Recurring tasks get their next occurrence.
   - Other events become dated Log lines.
   - Rewrite a project's State when the day changed where the project stands.
4. Make changes on your own only where evidence settles them, such as a merged PR that closes a task. Each one gets an `auto:` commit and a line under `## Claude did`.
5. File each capture and inbox entry whose home is obvious. Keep the rest as questions.
6. Write `## Wrap` in today's daily note: what got done, and what moves to tomorrow. Create the note first if it is missing.
7. In week mode, also:
   1. Write `journal/YYYY-Www.md` from the week's daily notes and today, with the sections from `CLAUDE.md`. Under `## Next week`, propose up to three outcomes.
   2. Commit the journal.
   3. Remove the week's daily notes with `git rm`, and commit. Their content now lives in the journal and in the history.
   4. Run the gardening pass below.
8. Reply in this shape:
   1. **Recorded**: one line per change.
   2. **Claude did**: the `auto:` changes.
   3. **Questions**: numbered, at most eight.
   4. **Gardening**: week mode only.

## Gardening pass

List findings. Change nothing in this pass.

- `active` projects whose State has not changed in 14 days
- `active` projects with an empty Next
- `open` questions that no project or experiment links to
- notes that no other note links to
- notes whose titles or content suggest duplicates
- `proposed` decisions older than 14 days
- `running` experiments with no Log activity in 14 days
- claims in a note that a newer note contradicts

The wrap is complete when the user's report is recorded, the daily note has its Wrap, every commit is pushed as `CLAUDE.md` says, and, in week mode, the journal exists and the daily notes are gone.
