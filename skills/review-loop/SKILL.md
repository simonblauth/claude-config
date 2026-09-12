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

The change also has a **boundary**, the statement of what it set out to do. From `issue-to-pr` it is the one that run's step 1 recorded; with a number, the request's title and description; with no argument, the commit messages in `git log <base>..HEAD`. It fills the reviewer's boundary block in step 2, and step 3 measures each finding against it.

Both forges return a **bare** branch name, so `origin/` is yours to add. Diffing against a bare `main` in a checkout whose local `main` trails the remote pulls every upstream commit merged since into the review, and the reviewer then files findings against code this change never touched.

Read the **head** ref from that same call and confirm HEAD is on it before diffing. A number names a request on the remote; it says nothing about where this checkout is standing. HEAD left on `main` gives an empty diff, and the loop declares a live request clean; HEAD on some unrelated branch reviews that branch and then posts a step-6 note crediting findings about code the request never touched.

With a number, resolve the forge the way step 0 of `~/.claude/skills/issue-to-pr/SKILL.md` does. With no argument nothing remote is read or written, so skip the forge entirely and skip step 6.

**Done when** the base is named as `origin/<branch>`, HEAD is confirmed on the head ref, and `git diff <base>...HEAD` prints a non-empty diff. An empty diff on a confirmed head means there is nothing to review; say so and stop. An empty diff with HEAD elsewhere is the wrong checkout, not a clean request.

## 2. Round loop, budget 3

Each round spawns **one fresh** `general-purpose` subagent, passing the prompt at `~/.claude/skills/review-loop/reviewer.md` verbatim with its placeholders filled. That path is absolute because the run's working directory is the target repo, where a relative `reviewer.md` resolves to nothing.

Opus is this loop's ceiling. Leave `model` off the spawn unless the round is going cheaper, and never pass one above Opus.

Fresh per round, never a continued agent: a reviewer carried forward defends its earlier findings instead of re-reading the code. Every round reviews the **whole** diff against the base, never the increment, because a fix in round 1 can break what round 1 passed.

`general-purpose`, not `Explore`: per [the subagent docs](https://code.claude.com/docs/en/sub-agents), "Explore and Plan are the only subagents that omit CLAUDE.md and git status", and `CLAUDE.md` compliance is half of what this reviewer checks. Every other subagent starts with "a fresh, isolated context window" that does not see the parent's history, which is the property that makes the review independent. Read-only comes from the prompt, the way `reflect` does it.

## 3. Work each finding as a claim

**Every finding is a claim, not an order.** Sort it by what it asks for, then check it against the code.

- A claim that a line the diff wrote is **wrong**, in its result, its test coverage or a `CLAUDE.md` rule it breaks, is in scope whatever the boundary says. The boundary decides what the branch adds, and says nothing about how well it is written. Check it against the code, below.
- A claim that asks for **behavior the boundary does not name**, a case handled, a feature grown, a path covered, is out of scope, however real. It gets a decline that quotes the boundary, and a line in the step-5 hand-back proposing the issue it belongs in.
- A claim that **does not hold** gets a written decline naming what you checked and what you found, and no code change.
- A claim that **holds** is a symptom. Load `systematic-debugging` and trace it to the mechanism before touching code; the reviewer's Mechanism line is its hypothesis, and you confirm or replace it. Then grep for every site that mechanism runs, in the diff and outside it. Then `tdd`: one red test covering the class, one fix at the mechanism, one commit that also covers the sites the reviewer did not anchor.

Two findings with one mechanism are one fix and one commit. `tdd`'s minimal green is minimal for the class the test names, not for the reviewer's one line: a patch at the anchor that leaves the mechanism in place hands the next round a fresh anchor, and the loop turns into one commit per site.

Nothing is left in a third state. A finding you have not checked is not worked.

**Done when** every finding of the round has a commit or a decline, and no two commits remove the same mechanism.

## 4. Carry the round forward

Round N+1's prompt fills the reviewer's earlier-rounds block with both halves of round N: each fix with its mechanism and commit, and each decline with your reason. The reviewer then either drops a declined point or comes back with new evidence, and files a failure at a fixed mechanism as a missed site rather than a new bug. Without the declines the loop can never go quiet, because a fresh agent re-raises what the last one raised. Without the fixes it cannot tell you that a fix was a patch.

A finding filed against a fixed mechanism is that signal. Round N fixed a symptom. Go back to the mechanism, and when the same one comes back a second time, stop fixing sites and take the structure to the user.

## 5. Stop and report

The loop ends on a **clean round** (a reviewer that returns no findings) or on the **budget** (three rounds run). These are different outcomes, and the hand-back names which one happened. Three rounds still finding things is a result, not a success: say what the open findings are. List the out-of-scope findings separately, each with the issue it belongs in.

## 6. Summary note

One note on the request, recording the rounds run, each finding fixed with its commit, each finding declined with its reason, and whether those commits are pushed or still local. The forge's command comes from the file step 1 resolved.

One note, not one thread per finding. An agent opening threads against its own request and then replying to itself is theater, and the note is what a human reads. On a plain branch with no request, skip this step and put the summary in the hand-back alone.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "Round 2 only needs to see round 1's fixes" | Every round reviews the whole diff. A round-1 fix can break what round 1 passed. |
| "The reviewer said line 42, so fix line 42" | The anchor is a symptom. Fix the mechanism and every site it runs, in one commit. |
| "Minimal green means touch nothing but the anchor" | Minimal for the class the test names. A patch that leaves the mechanism in place buys the next round a fresh anchor. |
| "Round 2 found a new bug" (same mechanism as a round-1 fix) | Round 1 fixed a symptom. Back to the mechanism, and after a second miss, to the user. |
| "Keep the same reviewer, it has the context" | That context is the problem. Fresh agent per round. |
| "The reviewer found it, so it is in scope" | The reviewer read the diff, not the boundary. A real finding outside the boundary gets a decline and a proposed issue. |
| "The reviewer is wrong, moving on" | A decline is written down, with what you checked. Silence is not a decline. |
| "Three rounds ran, so it is clean" | Budget exhaustion and a clean round are different hand-backs. |
| "`Explore` is cheaper for a read-only pass" | Explore omits `CLAUDE.md`, which is half the review. |
| "A costlier model would review better" | Opus is the ceiling for this loop. Spawn at the cap, not above it. |
| "One thread per finding is more traceable" | One note. Threads against your own request are theater. |
| "The base is `main`, that is what the API said" | Both forges return a bare name. Fetch, then diff against `origin/main`. |
| "The fixes are committed, so the note can claim them" | Standalone commits are local until a fresh ask pushes them. The note says which. |
| "The number names the request, so the diff is right" | The number is remote, HEAD is local. Confirm HEAD is on the head ref. |
