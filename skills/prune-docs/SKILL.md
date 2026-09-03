---
name: prune-docs
description: >
  Audit a repo's docs, CLAUDE.md and AGENTS.md against the environment, then
  restructure so each fact has one home. Probes for stale claims, counts
  duplication, validates links, anchors and symbols. Sibling of deslopify,
  which fixes prose inside one text; this one fixes which page owns which
  fact across a tree. Runs only on /prune-docs.
disable-model-invocation: true
---

# Prune docs

Bring a doc tree back to three properties: every claim is true at this commit, every fact has exactly one home, and whatever the environment can answer itself has been left to the environment. Docs are a cache of the environment (`writing-for-agents`, "Pruning"). This skill is the cache invalidation pass, run by hand, with the user approving every cut.

## Why the order is fixed

Two failure modes shape the sequence:

1. **Cuts made on judgement get argued back.** "This looks outdated" is an opinion. A stale-claim list where every line carries the command that proved it is a decision the user can approve in one pass, and it becomes the PR body verbatim. So the fact-check comes before any edit, and the user gate comes before any edit.
2. **Moving facts loses facts silently.** One fact, one home means text moves between pages, and moves drop things: the mechanism or number that justified a rule vanishes while the rule survives, and nothing fails. The pre-state claim list, taken before the first edit, is what makes the loss visible afterwards. That comparison is the **absence check**, and it is a mandatory row of the verification set.

Workflow: **Inventory → Fact-check → Duplication and claim list → Scope gate → Ownership map and triage → Rewrite → Verify and report.**

## Loaded, not restated

Load these at the start and follow their bodies. This skill adds only the docs-specific steps.

- `technical-writing`: one Diátaxis mode per page, and review checklist item 8 ("symbols, paths, counts real at this commit") as the fact-check bar.
- `writing-for-agents`: "Pruning" (environment as source of truth, docs as cache, sediment) and "Information hierarchy" for any `CLAUDE.md`, `AGENTS.md` or skill file in scope.
- `unslop` for the style-pass catalog.
- `verification-before-completion` for the gate. The docs rows are in Phase 7.

## Phase 1: Inventory

Every Markdown file on disk: tracked, untracked and gitignored. Commands in [references/probes.md](references/probes.md). Per file: lines, words, last-touched date, commit count, and a readership signal where one is available (the transcript-log probe in the reference is one; when its key is absent, report "no signal", never zero reads).

Untracked and ignored files appear in the table flagged **user-decides** and that is the last the skill does with them. An ignored file is the user's stated choice. An untracked file has no history to restore it from, so a wrong cut is permanent. Every later phase's **doc set** is the tracked Markdown only.

Show the table to the user before proposing a single cut. Done when every `.md` on disk is in the table with its class.

## Phase 2: Fact-check

Per document, extract every checkable claim: file trees, paths, symbol names, flag tables, dependency and lint lists, sample outputs, counts, line-number references. Prove each one live or stale with a command. Probes by ecosystem are in [references/probes.md](references/probes.md). Scan source comments too: they point at doc pages and doc headings, so a stale-reference scan over the doc set alone misses half the pointers.

Output: the **stale-claim list**, one line per claim: file and heading, the claim, the command, the verdict. This list justifies the plan, drives the scope questions, and later becomes the PR body.

Done when every checkable claim in scope carries a verdict and its command.

## Phase 3: Duplication and the pre-state claim list

- **Duplication counts.** For each suspect block, pick one distinctive verbatim line (a YAML key, a formula, a proper noun) and count it across the doc set with `grep -c`. Save the probe lines to a file. The same file re-runs in Phase 7 as the regression check: every line then hits exactly once.
- **Pre-state claim list.** One line per thing each page currently asserts: rules, mechanisms, numbers, API names. Write each as a grep pattern that matches only that claim. This file is the input to the absence check, so take it now, while the pages are untouched.

Done when both files exist and the user has seen the duplication counts.

## Phase 4: Scope gate

Hand the user the inventory, the stale-claim list and the duplication counts. Then ask one batch of scope questions. The three recurring axes:

- **Restructure** (move each fact to its owner page) or **trim in place**.
- **Prune** (delete what is stale) or **update in place** (rewrite to current truth).
- **Style pass in or out.**

Each option states its line target and its failure mode. The style-pass option states its churn cost: every reworded sentence with no content defect is a diff line a reviewer reads against no change in meaning. `technical-writing` already rules against churning what did not change, so this option never carries "(Recommended)". More generally, "(Recommended)" goes only on an option consistent with every rule loaded in context.

Done when the user has answered. The answers are the approved targets that Phase 7 measures against.

## Phase 5: Ownership map and triage

**Ownership map.** One line per file: its Diátaxis mode and the facts it owns. A fact that appears on two pages gets one owner; the other page links. The commit split falls out of this map: one ownership move per commit.

**Triage**, applied to every candidate line:

- A "why" that names a mechanism, an API or a number moves to the explanation page. Only a "why" that restates the rule it justifies gets cut. "Every write is billed" restates a rule; "the logger flushes once per message, about 500 writes per run" is the mechanism the rule exists for, and it moves.
- Delegating a fact to the environment (`--help`, a `list` subcommand, a generated tree) is legitimate once three things are on the table: the delegate has been run, its output is pasted, and the output is shown to cover every row being deleted. Then name the reader who cannot run the delegate (typically someone deciding whether to install) and decide, explicitly and in writing, whether that reader is in scope.
- A sentence with no content defect keeps its wording unless the user chose the style pass.
- Reference pages stay dry through the style pass. Voice and opinion belong to explanation pages.
- A line-number reference into source becomes a symbol name.
- Renaming a page: grep source, tests and untracked docs for the old filename first, then `git mv`.

## Phase 6: Rewrite

One ownership move per commit. Each file's style pass, when chosen, rides in that file's content commit unless the user asked for separate commits. Each commit message names the stale-claim entries it resolves.

## Phase 7: Verify and report

Run [references/check-docs.sh](references/check-docs.sh) over the doc set, or its rows by hand, then this repo's test and lint commands. The rows:

| Row | Passes when |
|-----|-------------|
| Links | every relative link target in the doc set resolves to a file |
| Anchors | every `#fragment` matches a heading slug in its target, GitHub rules, duplicate headings suffixed `-1`, `-2`. Another renderer needs its own slugger |
| Symbols | every symbol and fixture the docs name exists in source or tests |
| Stale paths | no doc, source comment or test names a renamed or deleted page |
| Duplication | every Phase 3 probe line hits exactly once |
| Absence check | every pre-state claim still hits somewhere, or its drop is on the stale-claim list or was approved at the gate |
| Style counters | for the pass that ran: em-dash count, duplicated signature blocks |
| Targets | line and word counts against what the user approved |
| Tests | the repo's suite, whenever a source comment was touched |
| Lint | the whole-tree run (`pre-commit run --all-files` or this repo's equivalent). A staged-set run on a Markdown-only commit reports `Skipped` for every file-scoped hook and proves nothing |

Report: every row with its output; every deviation from the approved targets with its reason; the absence-check result as three lists (survived, moved where, dropped and why); and adjacent problems found and deliberately left alone.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "This looks outdated" | Run the probe. A verdict is a command and its output. |
| "`--help` owns this now" | Run it, paste it, show it covers each deleted row, name the reader who cannot run it. |
| "That why just restates the rule" | Does it name a mechanism, an API or a number? Then it moves. |
| "pre-commit passed" | On a Markdown-only staged set, file-scoped hooks print `Skipped`. Run the whole tree. |
| "Cleaning the wording while I'm here" | Only if the user picked the style pass. |
| "That untracked file is obviously sediment" | Listed, flagged user-decides, untouched. There is no git to restore it from. |
