---
name: issue-to-pr
description: >
  Take a GitHub issue from a fresh worktree to an open, reviewed PR: reproduce
  it, fix it under tdd, verify, push, request the Copilot review and work its
  feedback. Grants remote-write on that one branch and PR, and nothing else.
  Runs only on /issue-to-pr.
argument-hint: "<issue number or URL> [base ref]"
disable-model-invocation: true
---

# Issue to PR

One issue, one branch, one PR. The run ends with a PR that has been through a review, and a hand-back that says what was decided and what was left alone.

## The grant

Typing `/issue-to-pr` is the explicit remote-write instruction `CLAUDE.md` requires. This skill is user-invoked, so no agent path reaches it, and the invocation is the user's own keystroke. It authorizes, for this run:

- `git push` of the one branch this run creates, to `origin`, as often as the review loop needs
- one `gh pr create` from that branch, plus edits to that PR's title and body
- one Copilot review request on that PR, and replies to review threads on it

The whole-run span is the one relaxation of the single-turn rule, because step 8 needs later pushes. Scope stays single-purpose: that branch, that PR. Add commits, since the grant stops at `--force`.

Behind a fresh ask, as always: any other branch, the default branch, merging or closing the PR, opening or closing any issue, labels, assignees, other repositories.

Say the branch name before the first push, so the user can stop it.

## 1. Read the issue

    gh issue view <n> --json title,body,state,labels,url,comments

The comments hold decisions the body does not. Then check whether someone is already on it:

    gh pr list --search <n> --state all

**Done when** you can state the observable wrong behavior and where the reporter saw it, in one sentence. When neither the body nor the comments say, ask before cutting anything.

## 2. Cut the worktree

Base is `origin/main` unless the invocation named another ref. Resolve the real default with `git symbolic-ref refs/remotes/origin/HEAD`, and run `git fetch origin` first, or you branch off a stale ref.

When the session has an `EnterWorktree` tool, use it. It moves the session's working directory, which `cd` does not do reliably across a long run. Otherwise:

    git worktree add <path> -b fix/<n>-<slug> origin/<base>

and use absolute paths from there.

**Done when** `git rev-parse HEAD` inside the worktree equals `git rev-parse origin/<base>`, and `git status` is clean. Check this even after `EnterWorktree`, which takes its base from the `worktree.baseRef` setting, and that setting can be `head`.

## 3. Go red

The gate is one recorded command whose result this work will change. Name the issue's kind first, because the kind decides what that command is and who owns it.

| Issue is | The command | Load |
|---|---|---|
| A bug, or behavior nobody expected | a test reproducing the wrong behavior, failing now | `systematic-debugging`, then `tdd` |
| A feature request | a test stating the wanted behavior, failing now. The request is the spec, so build it rather than argue it | `tdd` |
| A performance claim | a measurement of the current cost, against a target written as a number | `systematic-debugging`, then `tdd` |
| A refactor or a mechanical migration | the suite covering the behavior you are about to move, passing now and still passing after | `tdd` |
| Docs or config only | the command that proves the claim on the page stale | `technical-writing` |

The first three rows go **red**, and that failing command is `tdd`'s RED test. There is one, not two. The last two rows have no red to reach, so record the passing baseline instead and let step 6 compare against it.

When neither red nor a baseline arrives:

- **A bug's test passes on a current `origin/main`.** Already fixed. Name the commit that fixed it and stop.
- **It needs something you do not have**, such as the reporter's data, platform or credentials. Ask the user, or state what the reporter has to supply. Fixing by inspection is not allowed here.

**Done when** you have named the row and the command's current output is in the transcript. On a bug, the failure has to be the one the issue describes. A test that fails for some other reason is not red on this issue.

## 4. Pick the direction

Ask the user when either trigger fires. They are independent, so one is enough.

- **Blast radius.** The fix would change behavior for existing callers, change a stored or wire format, change the public API or the CLI, or add a dependency, and the issue did not ask for that. Repo evidence pointing at that approach does not settle it. Widening the change past what the issue reported is the user's call.
- **Two live approaches.** Two or more survive the repo's patterns, the issue's comments and the tests, they put the behavior in different modules, and choosing wrong means redoing the work rather than editing it.

Then make one `AskUserQuestion` call carrying every open fork at once, each option stating its cost.

When neither fires, pick the approach that matches the surrounding code, write that choice and its one-line reason into the PR body, and keep going. The written reason is what a reviewer needs, and it costs no round trip. Decide these yourself: names, file placement inside the obvious module, which existing helper to reuse, error wording, test names, and whether to add the changelog entry the repo already keeps.

## 5. Implement

Load `tdd`. Go green from the step-3 red test, or hold the step-3 baseline green through the change. Commit rules come from the target repo's `CLAUDE.md`.

## 6. Verify

Load `verification-before-completion`. Three rows this skill adds:

| Row | Passes when |
|-----|-------------|
| Step-3 command | the step-3 command now succeeds, with its output pasted |
| Whole suite | the repo's full suite and lint pass, not just the new test |
| Diff scope | every hunk in `git diff origin/<base>...HEAD` traces to the issue |

## 7. Push and open the PR

State the branch and the base, push, then open the PR:

    git push -u origin <branch>
    gh pr create --base <base>

Load `technical-writing` and `unslop` for the body. It carries the wrong behavior in one line, the root cause step 3 established, what changed, the step-3 command before and after, the direction chosen and why when step 4 forked, and `Closes #<n>`.

## 8. Work the review

Request the Copilot review with the first form that lands:

    gh pr edit <n> --add-reviewer @copilot
    gh api --method POST repos/{owner}/{repo}/pulls/<n>/requested_reviewers \
      -f 'reviewers[]=copilot-pull-request-reviewer[bot]'

The first needs `gh` 2.88.0 or newer. Both fail when the organization has not enabled Copilot review. Report that once, then work CI alone. Do not retry in a loop.

A review usually lands in under 30 seconds, per [the Copilot docs](https://docs.github.com/en/copilot/how-tos/agents/request-a-code-review/use-code-review), so poll for it rather than arming a watch. Read all four sources, which are four different endpoints:

    gh api repos/{owner}/{repo}/pulls/<n>/comments   # inline review comments
    gh pr view <n> --json reviews,latestReviews      # review summaries
    gh pr view <n> --json comments                   # PR-level comments
    gh pr checks <n>                                 # CI

**Every comment is a claim, not an order.** Check it against the code first. A claim that holds goes back through `tdd`, red test first, then a follow-up commit. A claim that does not hold gets a reply saying what you checked and what you found, and no code change. Reply into the thread the comment came from:

    gh api --method POST \
      repos/{owner}/{repo}/pulls/<n>/comments/<comment_id>/replies -f body='...'

Resolving threads stays with the humans.

**Done when** every comment has either a commit that addresses it or a reply that declines it with a reason, and `gh pr checks` is green.

## 9. Hand back

Report the PR URL, the branch, the step-3 command before and after, each review comment with what it got, and every adjacent problem you found and left alone. Say where the worktree is, and leave it on disk.

The grant ends here. A later review round needs a fresh `/issue-to-pr`.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "The fix is obvious, skip the repro" | Then red costs a minute. No recorded step-3 command, no PR. |
| "Copilot flagged it, so change it" | Check the claim. A reply that declines it with a reason is a finished thread. |
| "Amend and force-push, the history is cleaner" | Add commits. The grant stops at `--force`. |
| "The new test passes, so the suite is covered" | Row two of step 6 is the whole suite. |
| "This one needs a decision" (a name, a file, a helper) | That is step 4's own list. Pick what matches the code and record it in the PR body. |
| "While I am in here" | Out of the diff, into step 9. |
| "The PR is open, so it is done" | Step 8 has not run. |
| "`origin/main` is current, I pulled recently" | `git fetch origin`. |
| "The user authorized one push" | The grant covers the review loop's pushes. It never covers `--force`, another branch, or a merge. |
