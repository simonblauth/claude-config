# About the design of this vault

This note explains why the vault is built the way it is. Change the design here first, then change the rules in [CLAUDE.md](../CLAUDE.md) and [schema.yaml](../schema.yaml) to match.

## What the vault has to do

- Track projects with states, and the smaller tasks inside them.
- Hold structured research knowledge. A rule set and a domain model keep it from decaying into loose notes.
- Give a brief at the start of each day, a wrap at the end, and a weekly version of both on the first and last workday. Produce status reports on request.
- Stay private to the user.
- Let Claude do all the editing. The user decides. Claude acts on its own only on clear evidence and reports what it did.

## Why markdown in git

Research projects change direction often, so a backlog of tasks goes stale fast. The vault keeps each project's state as prose that Claude rewrites, keeps next tasks for the near term, and keeps ideas apart from commitments. Markdown in git also gives a diff and a history for every change Claude makes, which is the audit trail for its autonomous edits.

Every clone pulls before a change and pushes right after it. Several clones that sync only at the start and end of the day would conflict often.

## Why note types and a checker

The vault separates knowledge by role:

- A `question` is the research question: why it matters and its current answer.
- A `project` is the vehicle for answering questions.
- An `experiment` tests a hypothesis with a concrete setup and runs.
- An `implementation` is code that the user built, linked to its repo.
- A `decision` records a choice, its options, and its consequences.
- A `concept` holds lasting knowledge about a method, a tool, or the field.
- A `source` summarizes a paper, a dataset, a standard, or a document.
- A `person` records shared work and open requests.
- An `org` is an institute, a company, or a team that the user works with as a whole. It exists so that a project can wait on an organization when no single person is the contact. A person's `org` field links to the org note.

A project often has one line of work that waits beside others that move. So a single task can wait with `waiting:`, and the project's `waiting` status is kept for a project whose work all waits.

The structure aims between two extremes: heavy structure that is tiring to keep up, and unstructured notes that pile up into an unreadable heap. Typed notes with few required sections sit between the two. `tools/check.py` enforces the schema on every commit, which keeps the structure honest without anyone checking by hand. A gardening pass in the weekly wrap finds what no script can: duplicates, orphans, stale questions.

Daily notes exist only for the current week and roll into one journal note per week, so they never pile up.

## Why Claude acts alone only on clear evidence

Claude can edit everything, so access is never the limit. The limit is initiative. Claude changes things on its own only when evidence settles the change, gives each such change its own `auto:` commit, and lists it in the daily note so the next brief shows it first.

## Why the dashboard is a snapshot

The dashboard is a private claude.ai artifact. It shows today's brief, the week, a project board, and the open tasks, which a phone or a browser can open without a Claude session. No connector reaches the vault, so the `dashboard` skill exports the vault as JSON files and uploads them after each brief and wrap. Between refreshes the dashboard shows the last upload. The files hold vault content, so the dashboard stays private.
