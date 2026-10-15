---
name: report
description: Use when the user asks for a status report, a progress summary, or what they did over a period or on a project, whether for themselves or for someone else such as their lead.
---

# Report

The vault lives at `$VAULT_DIR` (default `~/vault`). Its `CLAUDE.md` and `schema.yaml` hold the rules and formats. Read both first. This skill holds the procedure only.

A report reads the vault and changes nothing in it.

## Steps

1. Pull, as the vault's `CLAUDE.md` says under sync.
2. Fix the period and the reader. The default period is the current week. Take the reader from the request. If the request names nobody, the reader is the user.
3. Read the sources in this order, and note any gap:
   1. journal notes in the period
   2. daily notes for days that no journal covers yet
   3. project notes: State, and Log lines in the period
   4. decision notes created or changed in the period
   5. optional: the user's merged PRs and closed issues in the period, through `gh`
4. Write the report:
   - One section per project with activity, `focus: now` first. Each section covers progress, decisions, blockers, and next steps.
   - End with the plan for the next period.
   - Base every statement on a source from step 3. Present an open hypothesis as a hypothesis.
5. If the reader is someone else, keep it to work results. Leave out people notes, inbox entries, private reflections, and Claude's own changes.
6. After the report, add a section for the user only, **Before you send**: at most five gaps or out-of-date notes that change what the report should say. If the period has no journal yet, offer to run the wrap first.

Deliver the report as text in the reply. Publish or send it only when the user asks for that.
