---
name: dispatch
description: >
  Dispatch one skill across owned repos: one background subagent per repo or
  per issue, each in its own worktree. Use when the user, or a schedule they
  set, asks to dispatch improve, improve-codebase-architecture, triage or
  issue-to-pr over an owner or a repo.
argument-hint: "<owner | owner/repo> <skill> [skill args] [--parallel N] [--max N] [--dry-run]"
---

# Dispatch

Dispatch is a driver. One run takes one **scope**, one **skill** and its arguments, and runs that skill once per **target**, unattended. The skills hand work to each other through issue labels, not through dispatch:

| Run | Target | Selected | Leaves behind |
|---|---|---|---|
| `dispatch <scope> improve` | repo | every repo in scope | issues labelled `source:improve` and `needs-triage` |
| `dispatch <scope> improve-codebase-architecture` | repo | every repo in scope | issues labelled `source:architecture` and `needs-triage` |
| `dispatch <scope> triage` | repo | repos with an open issue that is unlabelled, `needs-triage`, or `needs-info` | each issue moved to `ready-for-agent`, `ready-for-human`, `needs-info` or `wontfix` |
| `dispatch <scope> issue-to-pr` | issue | open `ready-for-agent` issues, see step 2 | one reviewed, open pull request per issue |

Each run is a single stage, so each stage gets its own schedule. A person steps in by changing a label. Dispatch keeps no state between runs: the labels are the state.

Arguments:

- `--parallel N`: subagents running at once. Default 3.
- `--max N`: targets per run. Default 10. A selection larger than `--max` takes the oldest targets first and names the rest in the summary.
- `--dry-run`: run steps 0 to 2, print the targets, and stop.
- Anything else after the skill name passes through to the skill, for example `quick` or `modernize` for `improve`.

GitHub only. GitLab scopes stop at step 0 with that reason.

## 0. Check ownership

Dispatch runs only on owned remotes, as the global instructions define them. Read the owned-remotes file (on Claude Code, `${CLAUDE_CONFIG_DIR:-~/.claude}/rules/owned-remotes.md`). Each repo in scope must match an entry. An entry marked `(private)` needs `gh repo view <owner>/<repo> --json visibility` to say `PRIVATE`.

The owned-remote rules cover every write the four skills make: issues, comments, labels, branches they create, and pull requests. Merging and everything else those rules hold back stays with the user.

**Done when** every repo in scope is owned or listed as refused. A scope with no owned repo stops here, and the summary says why.

## 1. List the repos

For a bare owner:

    gh repo list <owner> --no-archived --source --limit 1000 --json nameWithOwner,visibility,defaultBranchRef

A result of exactly 1000 repos means the list is truncated: stop and say so. Forks are left out, because their issues live upstream.

Check that each repo has the labels its skill uses: `gh label list -R <repo> --limit 200`. The label set is `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`, `bug`, `enhancement`, `source:improve`, `source:architecture` and `agent:claimed`. Creating a label is outside the owned-remote rules. List the missing ones per repo, with the `gh label create` lines for the user to run, and skip that repo for this run.

## 2. Select targets

Repo targets come from the table above. For `triage`, a repo qualifies when `gh issue list -R <repo> --search 'no:label' --limit 1` or the same query on `label:needs-triage` or `label:needs-info` returns an issue.

Issue targets for `issue-to-pr`, per repo:

    gh issue list -R <repo> --label ready-for-agent --search 'no:assignee -label:agent:claimed' --limit 200 --json number,title,createdAt,closedByPullRequestsReferences

Drop an issue whose `closedByPullRequestsReferences` names an open pull request: work is already in flight. An assignee means a person has claimed it.

**Stop rule.** Count the repo's open issues labelled `agent:claimed`. At 3 or more, select nothing from that repo this run. A claimed issue with no open pull request that names it is a stale claim from a run that died: remove its `agent:claimed` label and report it. It is selectable again on the next run.

**Done when** every selected target is listed with its repo, and every skipped repo has a reason.

## 3. Prepare each target

Each target gets a clone in the dispatch cache, `~/.cache/dispatch/repos/<owner>/<repo>`. Clone the repo the first time it is needed, then run `git fetch origin` before every run.

- **Repo target:** `git worktree add --detach ~/.cache/dispatch/worktrees/<run>/<repo> origin/<default>`. `<run>` is the run's start time as `YYYYmmdd-HHMMSS`.
- **Issue target:** first claim it with `gh issue edit <n> -R <repo> --add-label agent:claimed`. Read the labels back with `gh issue view`. If the claim is missing, drop the target. `issue-to-pr` cuts its own worktree from the cache clone.

## 4. Spawn the subagents

Read [references/preamble.md](references/preamble.md), fill it for the target, and start one background `general-purpose` subagent with it. The skill directory it names is the installed one, on Claude Code `${CLAUDE_CONFIG_DIR:-~/.claude}/skills/<skill>`. The four skills are user-invoked, so the subagent reads the file rather than invoking the skill, as `issue-to-pr` does with `review-loop`. Keep `--parallel` running. When one finishes, start the next.

A subagent can't ask the user, so a question comes back as a `QUESTION:` block in its report. Answer it with `SendMessage` to that subagent, but only from a source you can cite:

- the skill's own dispatched-run section or its stated defaults
- the target repo's `AGENTS.md`, `CLAUDE.md`, ADRs or docs
- this file

When no source settles it, reply `No answer. Take your skill's dispatched fallback.` A question about design, scope, or what the user wants always gets that reply: those decisions belong to a person, and the fallback routes them to `ready-for-human`. Give each target at most two answered questions. On a third, reply with the fallback.

**Done when** every target has a final report, or has been marked failed with the reason.

## 5. Summarize

Write the summary to `~/.cache/dispatch/runs/<run>.md` and print it. List:

- refused repos, skipped repos, and the labels each repo is missing
- each target's status, and the URLs of the issues, comments and pull requests it wrote
- every proposal a subagent reported: problems found outside its task. These are the user's to file or drop, so list them and file nothing.
- stale claims cleared, and targets cut by `--max`

Then remove the repo-target worktrees with `git worktree remove`. Leave `issue-to-pr` worktrees on disk: its hand-back names them.
