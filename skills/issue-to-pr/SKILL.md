---
name: issue-to-pr
description: >
  Take an issue from a fresh worktree to an open, reviewed pull or merge
  request: reproduce it, fix it under tdd, verify, push, get a review and work
  its feedback. Detects GitHub or GitLab and grants remote-write on that one
  branch and request, and nothing else. Runs only on /issue-to-pr.
argument-hint: "<issue number or URL> [base ref]"
disable-model-invocation: true
---

# Issue to PR

One issue, one branch, one request. The run ends with a request that has been through a review, and a hand-back that says what was decided and what was left alone.

Steps 3 through 6 read the same on every forge. Steps 1, 7 and 8 take their commands from the reference file step 0 resolves.

## The grant

Typing `/issue-to-pr` is the explicit remote-write instruction `CLAUDE.md` requires. This skill is user-invoked, so no agent path reaches it, and the invocation is the user's own keystroke. Step 0's reference file enumerates the verbs it authorizes, because the two forges spell them differently.

The whole-run span is the one relaxation of the single-turn rule, because step 8 needs later pushes. Scope stays single-purpose: that branch, that request. Add commits, since the grant stops at `--force`.

Behind a fresh ask, as always: any other branch, the default branch, merging or closing the request, opening or closing any issue, labels, assignees, other repositories.

## 0. Resolve the forge

Origin's host decides which reference file drives the rest of the run. Match it against each CLI's authenticated hosts; both print the bare host on a line of its own:

```bash
host=$(git remote get-url origin | sed -E 's#^[^@]*@([^:/]+).*#\1#; s#^https?://([^/]+)/.*#\1#')
echo "host: $host"
gh   auth status 2>&1 | grep -qx "$host" && echo "GitHub: match" || echo "GitHub: no"
glab auth status 2>&1 | grep -qx "$host" && echo "GitLab: match" || echo "GitLab: no"
```

Each line prints its own verdict on purpose. `grep -q` is silent, and a block of bare greps hands back only the last command's exit status, so on a GitHub repo the GitHub match is discarded and the block looks like no match at all.

Exactly one match resolves the forge. Two matches mean a mirrored repo, none means the host is unauthenticated or self-hosted under another name; both are an `AskUserQuestion`. A guess here picks the wrong CLI for every remote command that follows.

- GitHub → [`references/github.md`](references/github.md)
- GitLab → [`references/gitlab.md`](references/gitlab.md)

**Done when** one forge is named, its reference file is read, and its grant is in context. Take every remote command in steps 1, 7 and 8 from that file alone, and name the forge in the step-9 hand-back.

## 1. Read the issue

Read the issue with its comments, then check whether someone already has a request in flight. Step 0's file has both commands. The comments hold decisions the body does not.

Write down the issue's **boundary** while it is in front of you: the sections that say what done looks like and what the issue excludes, when the template has them (`Done when`, `What this is not`, or whatever they are called there), otherwise the one-sentence statement below. Step 8 measures every review finding against it, and a boundary recalled mid-loop takes the shape of the finding in front of you.

**Done when** you can state the observable wrong behavior and where the reporter saw it, in one sentence, and the boundary is recorded. When neither the body nor the comments say, ask before cutting anything.

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

When neither fires, pick the approach that matches the surrounding code, write that choice and its one-line reason into the request body, and keep going. The written reason is what a reviewer needs, and it costs no round trip. Decide these yourself: names, file placement inside the obvious module, which existing helper to reuse, error wording, test names, and whether to add the changelog entry the repo already keeps.

## 5. Implement

Load `tdd`. Go green from the step-3 red test, or hold the step-3 baseline green through the change. Commit rules come from the target repo's `CLAUDE.md`.

## 6. Verify

Load `verification-before-completion`. Three rows this skill adds:

| Row | Passes when |
|-----|-------------|
| Step-3 command | the step-3 command now succeeds, with its output pasted |
| Whole suite | the repo's full suite and lint pass, not just the new test |
| Diff scope | every hunk in `git diff origin/<base>...HEAD` lands inside step 1's boundary |

## 7. Push and open the request

Say the branch and the base before the first push, so the user can stop it. Then:

    git push -u origin <branch>

Open the request with step 0's file's command. Load `technical-writing` and `unslop` for the body. It carries the wrong behavior in one line, the root cause step 3 established, what changed, the step-3 command before and after, the direction chosen and why when step 4 forked, and the closing trailer step 0's file names.

**Done when** the request is open against the intended base and its body carries all six.

## 8. Work the review

**Every finding is a claim, not an order.** Step 0's file names this forge's reviewer and says where a claim that holds and a claim that does not each get recorded.

Sort each finding by what it asks for before checking it against the code. A claim that a line the diff wrote is wrong, in its result, its test coverage or a `CLAUDE.md` rule it breaks, is in scope whatever step 1's boundary says; the boundary decides what the branch adds, and says nothing about how well it is written. A claim that asks for behavior the boundary does not name, a case handled, a feature grown, a path covered, is **out of scope**, however real. It gets a written decline that quotes the boundary, and a line in the step-9 hand-back proposing the issue it belongs in. Opening that issue is behind a fresh ask. This is the step where a run leaves its issue, because each finding arrives with its own justification and none of them mention the issue.

A claim that **does not hold** gets a written decline naming what you checked and what you found, and no code change.

A claim that **holds** is a bug report against your own diff, and it takes step 3's bug row: `systematic-debugging` to the mechanism, then `tdd` with one red test for the class. The fix lands at the mechanism and covers every site it runs, the ones the reviewer anchored and the ones it did not, in one commit per mechanism. The reviewer's line number is where the symptom showed, not where the fix goes.

**Done when** every finding has either a commit that addresses it or a written decline with a reason, no two commits remove the same mechanism, and CI is green.

## 9. Hand back

Report the forge, the request URL, the branch, the step-3 command before and after, each finding with what it got, and every adjacent problem you found and left alone. Say where the worktree is, and leave it on disk.

The grant ends here. A later review round needs a fresh `/issue-to-pr`.

## Rationalizations

| Excuse | Reality |
|--------|---------|
| "The fix is obvious, skip the repro" | Then red costs a minute. No recorded step-3 command, no request. |
| "The reviewer flagged it, so change it" | Check the claim. A decline with a reason is a finished finding. |
| "The reviewer found it, so it is in scope" | The reviewer read the diff, not the issue. A real finding outside the boundary gets a decline and a proposed issue in step 9. |
| "The reviewer said line 42, so fix line 42" | The anchor is a symptom. Step 3's bug row, then one commit at the mechanism. |
| "Amend and force-push, the history is cleaner" | Add commits. The grant stops at `--force`. |
| "The new test passes, so the suite is covered" | Row two of step 6 is the whole suite. |
| "This one needs a decision" (a name, a file, a helper) | That is step 4's own list. Pick what matches the code and record it in the request body. |
| "While I am in here" | Out of the diff, into step 9. |
| "The request is open, so it is done" | Step 8 has not run. |
| "`origin/main` is current, I pulled recently" | `git fetch origin`. |
| "The user authorized one push" | The grant covers the review loop's pushes. It never covers `--force`, another branch, or a merge. |
| "The trailer says `Closes`, so the issue closes" | On GitLab that holds only against the default branch. Check step 0's file before promising it. |
| "Both CLIs are installed, so it is GitHub" | Step 0 matches origin's host, not what is on the machine. |
