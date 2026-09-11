# GitHub

Resolved by step 0 of [`../SKILL.md`](../SKILL.md). Everything here drives steps 1, 7 and 8 on a `gh`-authenticated host.

## The grant, on this forge

`/issue-to-pr` authorizes, for this run:

- `git push` of the one branch this run creates, to `origin`, as often as the review loop needs
- one `gh pr create` from that branch, plus edits to that PR's title and body
- one Copilot review request on that PR, and replies to review threads on it
- one summary comment on that PR, when the run reaches `review-loop`'s step 6

Nothing else. Resolving threads stays with the humans.

## Step 1. Read the issue

    gh issue view <n> --json title,body,state,labels,url,comments

Then check whether someone is already on it:

    gh pr list --search <n> --state all

## Step 7. Open the PR

    gh pr create --base <base> --title '<title>' --body-file -

`--body-file -` reads the body from standard input. Pass both flags: without them `gh pr create` prompts for the title and body, and the agent's shell has no TTY to answer with.

The closing trailer is `Closes #<n>`.

## Step 8. Work the review

Request the Copilot review with the first form that lands:

    gh pr edit <n> --add-reviewer "@copilot"
    gh api --method POST repos/{owner}/{repo}/pulls/<n>/requested_reviewers \
      -f 'reviewers[]=copilot-pull-request-reviewer[bot]'

The first needs `gh` 2.88.0 or newer. Both fail when the organization has not enabled Copilot review. Report that once, then work CI alone. Do not retry in a loop.

A review usually lands in under 30 seconds, per [the Copilot docs](https://docs.github.com/en/copilot/how-tos/agents/request-a-code-review/use-code-review), so poll for it rather than arming a watch. Read all four sources, which are four different endpoints:

    gh api repos/{owner}/{repo}/pulls/<n>/comments   # inline review comments
    gh pr view <n> --json reviews,latestReviews      # review summaries
    gh pr view <n> --json comments                   # PR-level comments
    gh pr checks <n>                                 # CI

Work each claim as step 8 says. A decline is a reply saying what you checked and what you found, into the thread the comment came from; a fix gets a reply naming its commit and the mechanism it removed:

    gh api --method POST \
      repos/{owner}/{repo}/pulls/<n>/comments/<comment_id>/replies -f body='...'

A run that reaches `review-loop`'s step 6 posts its one summary comment with:

    gh pr comment <n> --body-file -
