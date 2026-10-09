---
name: distill
description: Use when the user asks to distill, save, or file knowledge into the vault from the current session, a repo, or a pasted chat summary, or when a research conversation produced decisions or findings worth keeping.
---

# Distill

The vault lives at `$VAULT_DIR` (default `~/vault`). Its `CLAUDE.md`, `schema.yaml`, and `GLOSSARY.md` (when it exists) hold the rules, formats, and terms. Read them first. This skill holds the procedure only.

Distilling changes the knowledge base, so the user approves every change first. Nothing is written to the vault before that approval.

## Steps

1. Pull, as the vault's `CLAUDE.md` says under sync.
2. Name the source: the pasted text, this session, or the current repo.
3. Extract candidate changes:
   - a question's current answer, or a new question
   - a decision, with its context, options, and consequences
   - a concept, a source, or an experiment result
   - a project's State or Log
   - a research term for `GLOSSARY.md`

   Code explains the current state, so a repo stays the home of what its code and docs say. The vault takes the reasons, the process, and the questions, and links to the repo through an `implementation` note.
4. For each candidate, search the vault for an existing note. Prefer updating a note to creating one. List each place where the source contradicts an existing note.
5. Mark claims that come from a chat or the web and that nobody has checked as `(unverified, from <source> <date>)`. Research further only when the user asks.
6. Present the proposal as a numbered list. For each change, give the file, whether it is new or updated, and the exact text to add or the replaced passage beside its replacement. Then list the contradictions. Ask which changes to apply, edit, or drop.
7. After the user approves:
   1. Write the approved changes.
   2. Run the checker through the pre-commit hook by committing, one commit per purpose.
   3. Push.
   4. Report the files changed.

Load the `domain-modeling` skill when a glossary term or a decision needs sharpening.

Distilling moves knowledge into the vault only. The source repo and its history stay free of vault content.
