# GitLab

Resolved by step 0 of [`../SKILL.md`](../SKILL.md). Everything here drives steps 1, 7 and 8 on a `glab`-authenticated host. Commands verified against `glab` 1.116.0.

## The grant, on this forge

`/issue-to-pr` authorizes, for this run:

- `git push` of the one branch this run creates, to `origin`, as often as the review loop needs
- one `glab mr create` from that branch, plus edits to that MR's title and body
- one summary note on that MR

Nothing else. No approve, no merge, no `--force`. Resolving threads stays with the humans.

## Step 1. Read the issue

    glab issue view <n> --comments -F json --per-page 100 --page <p>

`--comments` is what populates the `Notes` key; without it that key is `null` and you read a body with no discussion.

**Page it, or you read a stale half of the thread.** `--per-page` defaults to 20 and notes come back oldest first, so the default drops exactly the recent comments that carry the decisions. On `gitlab-org/cli#7473`, the default returns 18 notes ending 2024-06-17; `--per-page 100` returns 96 ending 2024-09-30, and page 2 returns a further 92 with no overlap. Walk `--page` up from 1 until a page returns zero notes. A page shorter than `--per-page` is not the last page: `glab` drops system notes from the page it fetched, so a short page says nothing about whether more follow.

Then check whether someone is already on it:

    glab mr list --search <n> --all

## Step 7. Open the MR

    glab mr create --source-branch <branch> --target-branch <base> \
      --title '<title>' --description-file - --yes

`--description-file -` reads the body from standard input. `--yes` skips the submission confirmation prompt, which an agent cannot answer. To edit the MR afterwards:

    glab mr update <n> --title '<title>'
    glab mr update <n> --description-file -

The closing trailer is `Closes #<n>`, and on GitLab it is conditional: the [closing pattern](https://docs.gitlab.com/user/project/issues/managing_issues/) fires only when the commit or MR is merged into the project's **default** branch. When the invocation named a non-default base, the trailer is inert. Write it anyway, and say in the step-9 hand-back that the issue will not close on merge.

## Step 8. Work the review

GitLab has no Copilot review, so this run supplies its own reviewer. Read the loop at:

    ~/.claude/skills/review-loop/SKILL.md

Read it rather than invoking it: both skills are user-invoked, so no skill path reaches another. Run its rounds against the MR step 7 opened, then come back to step 9 with the rounds it ran and what each finding got.

Step 8's CI gate reads the pipeline for the MR's source branch:

    glab ci status --branch <branch> --compact

The summary note that loop writes is the one note this grant covers:

    glab mr note create <n> --resolvable=false < <file>

`glab mr note` subcommands are flagged EXPERIMENTAL in 1.116.0 ("might be unstable or removed at any time"), so a break here is visible and non-fatal: report it and put the summary in the hand-back instead. `--resolvable=false` keeps the note from blocking merge on projects that require all threads resolved. It takes the body from standard input or a redirected file; there is no `--description-file` on this subcommand.

To read an MR's notes back, whether to confirm that note landed or to read a reply:

    glab mr view <n> --comments -F json

**The key is `Discussions`, and an MR has no `Notes` key at all.** Step 1's issue command returns a flat `Notes` list, so the habit does not carry over: `glab mr view` nests the bodies at `Discussions[].notes[]`, and leaves `Discussions` null without `--comments`. An MR read for `Notes` comes back empty, and a run that trusts that reports a live discussion as no discussion. System notes arrive alongside the human ones, marked `"system": true`.

**Drop step 1's paging flags here.** This command returns every discussion by itself: `gitlab-org/gitlab!252827` comes back with all 269, the same count the discussions endpoint gives across three pages of 100. `--page` only subtracts, skipping `(page - 1) * --per-page` discussions and returning the rest, so on an MR holding fewer than 100 of them step 1's `--per-page 100 --page 2` returns an empty list.
