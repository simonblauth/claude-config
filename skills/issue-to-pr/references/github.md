# GitHub

Resolved by step 0 of [`../SKILL.md`](../SKILL.md). Everything here drives steps 1, 7 and 8 on a `gh`-authenticated host.

## The grant, on this forge

`/issue-to-pr` authorizes, for this run:

- `git push` of the one branch this run creates, to `origin`, as often as the review loop needs
- one `gh pr create` from that branch, plus edits to that PR's title and body
- with the `copilot` reviewer, up to three Copilot review requests on that PR, one per round, and replies to review threads on it
- one summary comment on that PR, when the loop stops

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

The reviewer defaults to `copilot` on this forge. With `--reviewer subagent`, step 8 runs `review-loop` and this section contributes only its last part, [Either reviewer](#either-reviewer).

### Copilot rounds

Copilot reviews for up to three rounds. Each round requests a review of the current HEAD, works what it returns, and pushes the fixes. Request the first round with the first form that lands:

    gh pr edit <n> --add-reviewer "@copilot"
    gh api --method POST repos/{owner}/{repo}/pulls/<n>/requested_reviewers \
      -f 'reviewers[]=copilot-pull-request-reviewer[bot]'

The first needs `gh` 2.88.0 or newer, and in 2.101.0 its help says it re-requests a reviewer who has already reviewed, so it serves every round. Both fail when the organization has not enabled Copilot review. So does a review whose body reads "Copilot was unable to review this pull request", which is how a spent quota arrives. Report either once, then fall back to the `subagent` reviewer. Do not retry in a loop.

A review usually lands in under 30 seconds, per [the Copilot docs](https://docs.github.com/en/copilot/how-tos/agents/request-a-code-review/use-code-review), so poll for it rather than arming a watch. The round's review is Copilot's review on the HEAD you pushed:

    gh api repos/{owner}/{repo}/pulls/<n>/reviews --jq '.[]
      | select(.user.login | startswith("copilot-pull-request-reviewer"))
      | select(.commit_id == "<head sha>") | {id, body}'

A repository with **Review new pushes** enabled reviews each push without being asked, so poll for that review before re-requesting. Two reviews on one HEAD are one round. Read the round's findings, plus what humans added since the last round:

    gh api repos/{owner}/{repo}/pulls/<n>/reviews/<review_id>/comments   # this round's inline comments
    gh api repos/{owner}/{repo}/pulls/<n>/comments   # every inline comment, humans' included
    gh pr view <n> --json comments                   # PR-level comments

Work each claim as step 8 says. A decline is a reply saying what you checked and what you found, into the thread the comment came from; a fix gets a reply naming its commit and the mechanism it removed:

    gh api --method POST \
      repos/{owner}/{repo}/pulls/<n>/comments/<comment_id>/replies -f body='...'

**Copilot cannot be handed the earlier rounds.** The same docs say it "may repeat the same comments again, even if they have been dismissed". A comment restating a point you declined, with nothing new, gets a reply linking the earlier decline and no fresh work. A comment on a mechanism you already fixed means that fix was a patch at the anchor: go back to the mechanism, and when the same one comes back a second time, take the structure to the user.

Push the round's commits, then request the next round. The loop stops on the first of:

- **A clean round**: the review adds no inline comments, and its body names no finding, or it only restates earlier declines.
- **A round that pushed nothing**: every finding was declined. HEAD did not move, so another review would read the same code.
- **The budget**: three rounds reviewed. Open findings are a result, not a success; the hand-back lists them.

Step 9 names which one it was. Then post the summary comment below: the rounds run, each finding fixed with its commit, each finding declined with its reason.

### Either reviewer

Step 8's CI gate:

    gh pr checks <n>

The one summary comment, whether this section's loop or `review-loop`'s step 6 wrote it:

    gh pr comment <n> --body-file -
