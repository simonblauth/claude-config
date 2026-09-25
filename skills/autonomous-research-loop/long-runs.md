# Long runs

Read when a run takes longer than 10 minutes (SKILL.md). A unit is one run,
the review follows every run, and the live run's files stay frozen while you
prepare the next one.

## While a run is live

- **Exit watcher,** armed at every launch: a background shell loop that waits
  for the process to start, then for it to exit. `pgrep -f "<pattern>"`
  matches the watcher's own shell, so anchor it on the interpreter as the
  launcher writes it (`^python <entry>`). A restart of the agent process
  kills watchers: check the job directly (pgrep, the log's last progress
  point) and re-arm; check-ins never rely on a watcher.
- **An idle node is the expensive state;** the analysis gap after a run is the
  only planned idle, and it stays short (read-out, review, launch).
- **Monitor from files,** matching the signatures you would act on
  (Traceback, the subject's crash signatures, the log silent for more than
  three progress intervals), not benign lines that contain `nan` or `Error`.

## tmux

```bash
tmux new-session -d -s research -x 220 -y 50 -c <repo>     # once
[ "$(tmux display -p -t research '#{pane_current_command}')" = bash ] \
  && tmux send-keys -t research '<launcher> <config>' Enter  # per run
```

- One session, one window, runs in sequence in that shell. The user attaches;
  agents never do.
- Never send keys to a pane whose shell is not at a prompt: keys typed while a
  process holds the foreground run when it exits.

## Worktree for code during a run

`git worktree add` copies only committed files. Create it with the
uncommitted state:

```bash
git worktree add --detach <scratch>/wt HEAD
git diff HEAD -- <package> <tests> <configs> | (cd <scratch>/wt && git apply)
cp <untracked files the change needs> <scratch>/wt/...
```

- An editable install imports the main tree. Run tests in the worktree with
  `PYTHONPATH=<scratch>/wt` and confirm `python -c "import <pkg>;
  print(<pkg>.__file__)"` points into the worktree.
- Run the linter and formatter inside the worktree only; a repo-wide format in
  the main tree rewrites files a live job reads.
- Copy changed files back only while no job runs (the analysis gap), re-run
  their tests in the main tree, then launch from the main tree. Save any
  change not yet copied back as a patch in the research folder, since the
  scratch directory ends with the session.

## Common mistakes

| Mistake | Fix |
|---|---|
| Tests in a worktree importing the main tree | PYTHONPATH and a `__file__` check |
| Launching before the tested change is in the main tree | Copy it in during the gap, re-test, check `git diff` |
| Formatting the repo during a live run | Lint inside the worktree only |
| Watcher that never fires | Anchored pgrep; wait for start |
