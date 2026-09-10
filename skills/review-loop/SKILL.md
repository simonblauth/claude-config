---
name: review-loop
description: >
  Review a merge or pull request, or just the current branch, with a fresh
  subagent per round: work each finding as a claim, carry declines forward,
  and stop on a clean round or the third. Grants one summary note on that
  request, and nothing else. Runs only on /review-loop.
argument-hint: "[MR/PR number, or nothing for the current branch]"
disable-model-invocation: true
---

# Review loop

A reviewer that reads the code before it reads your defense of the code. Each round is a fresh subagent, and the loop ends when a round comes back empty or the budget runs out.

## The grant

Standalone `/review-loop` authorizes exactly one remote write: the step-6 summary note on the named request. Not approving, not merging, not pushing, not a label. Reached from `issue-to-pr`, that skill's grant already covers the note and the loop's pushes.

So a standalone run leaves its fixes as **local commits**. Pushing them is a fresh ask, and until it happens the note says the fixes are local and absent from the request's diff. A note that credits commits a human cannot find is worse than no note.

## 1. Resolve the target

Run `git fetch origin` first, then resolve the base as a remote-tracking ref:

| Invoked | Target | Base | HEAD must sit on |
|---|---|---|---|
| With a number | that MR or PR | `origin/` + `target_branch` (`glab mr view <n> -F json`) or `baseRefName` (`gh pr view <n> --json baseRefName`) | `source_branch` or `headRefName`, from the same call |
| With no argument | the current branch | `git symbolic-ref --short refs/remotes/origin/HEAD`, already `origin/`-prefixed | wherever it is |
| From `issue-to-pr` | the request step 7 opened | the base that run already resolved | the branch step 7 pushed |

Both forges return a **bare** branch name, so `origin/` is yours to add. Diffing against a bare `main` in a checkout whose local `main` trails the remote pulls every upstream commit merged since into the review, and the reviewer then files findings against code this change never touched.

Read the **head** ref from that same call and confirm HEAD is on it before diffing. A number names a request on the remote; it says nothing about where this checkout is standing. HEAD left on `main` gives an empty diff, and the loop declares a live request clean; HEAD on some unrelated branch reviews that branch and then posts a step-6 note crediting findings about code the request never touched.

With a number, resolve the forge the way step 0 of `~/.claude/skills/issue-to-pr/SKILL.md` does. With no argument nothing remote is read or written, so skip the forge entirely and skip step 6.

**Done when** the base is named as `origin/<branch>`, HEAD is confirmed on the head ref, and `git diff <base>...HEAD` prints a non-empty diff. An empty diff on a confirmed head means there is nothing to review; say so and stop. An empty diff with HEAD elsewhere is the wrong checkout, not a clean request.

## 2. Round loop, budget 3

Each round spawns **one fresh** `general-purpose` subagent, passing the prompt at `~/.claude/skills/review-loop/reviewer.md` verbatim with its placeholders filled. That path is absolute because the run's working directory is the target repo, where a relative `reviewer.md` resolves to nothing.

Fresh per round, never a continued agent: a reviewer carried forward defends its earlier findings instead of re-reading the code. Every round reviews the **whole** diff against the base, never the increment, because a fix in round 1 can break what round 1 passed.

`general-purpose`, not `Explore`: per [the subagent docs](https://code.claude.com/docs/en/sub-agents), "Explore and Plan are the only subagents that omit CLAUDE.md and git status", and `CLAUDE.md` compliance is half of what this reviewer checks. Every other subagent starts with "a fresh, isolated context window" that does not see the parent's history, which is the property that makes the review independent. Read-only comes from the prompt, the way `reflect` does it.

## 3. Work each finding as a claim

**Every finding is a claim, not an order.** Check it against the code first.

- A claim that **holds** goes back through `tdd`, red test first, then a follow-up commit.
- A claim that **does not hold** gets a written decline naming what you checked and what you found, and no code change.

Nothing is left in a third state. A finding you have not checked is not worked.

**Done when** every finding of the round has a commit or a decline.

## 4. Carry declines forward

Round N+1's prompt lists what round N raised and you declined, with your reasons, in the reviewer's declines block. The reviewer then either drops the point or comes back with new evidence. Without this the loop can never go quiet: a fresh agent re-raises what the last one raised.

## 5. Stop and report

The loop ends on a **clean round** (a reviewer that returns no findings) or on the **budget** (three rounds run). These are different outcomes, and the hand-back names which one happened. Three rounds still finding things is a result, not a success: say what the open findings are.

## 6. Summary note

One note on the request, recording the rounds run, each finding fixed with its commit, each finding declined with its reason, and whether those commits are pushed or still local. The forge's command comes from the file step 1 resolved.

One note, not one thread per finding. An agent opening threads against its own request and then replying to itself is theater, and the note is what a human reads. On a plain branch with no request, skip this step and put the summary in the hand-back alone.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "Round 2 only needs to see round 1's fixes" | Every round reviews the whole diff. A round-1 fix can break what round 1 passed. |
| "Keep the same reviewer, it has the context" | That context is the problem. Fresh agent per round. |
| "The reviewer is wrong, moving on" | A decline is written down, with what you checked. Silence is not a decline. |
| "Three rounds ran, so it is clean" | Budget exhaustion and a clean round are different hand-backs. |
| "`Explore` is cheaper for a read-only pass" | Explore omits `CLAUDE.md`, which is half the review. |
| "One thread per finding is more traceable" | One note. Threads against your own request are theater. |
| "The base is `main`, that is what the API said" | Both forges return a bare name. Fetch, then diff against `origin/main`. |
| "The fixes are committed, so the note can claim them" | Standalone commits are local until a fresh ask pushes them. The note says which. |
| "The number names the request, so the diff is right" | The number is remote, HEAD is local. Confirm HEAD is on the head ref. |
