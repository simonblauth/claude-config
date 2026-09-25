---
name: researching-training-recipes
description: Autonomous research loop of long compute runs on one node, one run at a time, each chosen after an independent review. Runs only on /researching-training-recipes.
argument-hint: "[environment rules file] | check-in <research folder>"
disable-model-invocation: true
---

# Researching with long runs

## Overview

One compute node, one live run at a time, one change per run, every verdict
measured against the noise band and the cost. You pick the next run from the
finished ones after an independent review; code changes happen in a scratch
worktree so the live run's files stay frozen. The loop runs on its own.

**Core principle:** never predetermine the queue. Each launch is the single
most informative run given everything finished so far, and every claim is a
number with its comparator until someone has tried to break it.

Training-specific material (selection signal, levers, convergence, per-run
diagnostics) is in training.md; copyable prompts and skeletons in
templates.md.

## Arguments

- `check-in <research folder>`: a scheduled check-in; go to Check-in.
- Anything else is the path of the environment rules file (Environment
  rules); then go to Before the first launch.

## Definitions

- **Reference:** the run a change is compared against, named in its
  pre-registration (usually the current best; the baseline for a new lever).
- **Noise band:** the per-metric spread between two seeds of the same
  configuration with the evaluation draw pinned, |seed B / seed A - 1|, at the
  judged epoch and averaged over the last window. One pair is a provisional
  band (a single draw); two or more pairs make a width. Until it is measured,
  every difference smaller than about 3 % is unreadable.
- **Lever class:** a family of changes that act through one mechanism
  (training draw, loss term, model head, input information, augmentation,
  gradient routing, optimizer).
- **VOID:** a run whose result cannot be read (did not reach the judged epoch,
  wrong evaluation seed or sample set, NaN, cost over its cap, a crash). A VOID
  run neither supports nor refutes.
- **Design leak:** what the loop learns about the held-out set by choosing runs
  on it.
- **Mode:** a run's label: explore, exploit, calibration or diagnosis
  (Explore and exploit).
- **INCONCLUSIVE:** a readable run that meets neither its SUPPORTED nor its
  REFUTED clauses; its registration names the follow-up.
- **Judged epoch and window:** the epoch the registration reads (the run's
  last evaluation unless stated), and the last ten evaluations before it for
  smoothed values and slopes.
- **Calibration run:** a seed repeat with the evaluation pinned: of the
  reference while it has fewer than two seeds, otherwise of the current best.
- **Reference validity:** a reference trained with older code or another
  evaluation is re-run before it anchors a comparison.

## Environment rules

The site's rules (storage, cost, what makes the node busy, paths, project
rules) live in an **environment rules file**, never in this skill: the path
given as the argument, else `RESEARCH_RULES.md` in the working directory.
Its skeleton in templates.md names the required sections.

- **No file, or a required section missing or empty: stop.** Name the missing
  file or section, show the skeleton's headings, and launch nothing, create
  no research folder. At a check-in the same finding stops launching; log it
  in STATE.md.
- Restate the file's rules at the start and record its path in STATE.md.
- Every subagent prompt starts with the subagent rules block from
  templates.md, which carries the file verbatim.

The loop's own rules, on top of the file:

- One job per GPU, busy as the file defines it. The job owns its RAM
  (`free -g` before anything else runs). Anything it reads (package, entry
  point, configs, input data) is frozen until it exits.
- Reviewers are fresh general-purpose agents, never forks: a fork inherits
  your reading.

## Autonomy

The loop is fully autonomous and never waits for the user. It stops only when
the user says so, or on the stop rule (Explore and exploit).

- Restate the task and the plan, then proceed without waiting for a go.
- A question that only the user can answer is logged in STATE.md under
  "Decisions logged for the user" with the default you took, and never blocks
  a launch. A proposal to change the user's objective is logged the same way
  and not adopted.
- A rule the user adds mid-run goes into STATE.md verbatim at once, and into
  the next pre-registration; check-ins and the subagent rules block read it
  from there.
- While the user is away, reports go to STATE.md and HISTORY.md.

## Before the first launch

1. **Restate** goal metric and its strata, budget per run, fixed decisions and
   the hard constraints (from the environment rules file, not memory). If the
   user named no metric, take the one the project docs use on real data and
   log it.
   Ask which levers are feasible in deployment. Until answered, run only
   training-side levers (loss, optimizer and schedule, augmentation, sampling
   or reweighting of the training data, regularization, gradient routing, run
   length, capacity with the same inputs and outputs); changes to the model's
   inputs, outputs or deployment interface wait, logged.
2. **Set up the research folder** (Documentation) with STATE.md from the
   skeleton. If earlier work on the topic exists, extend its folder instead
   of starting a second one.
3. **Tooling:** reuse the repo's launcher if it has one and it refuses to start
   when the node is busy (else wrap it); otherwise write one that refuses a
   busy node, runs one config, tees a per-run log, and has a dry-run mode whose
   exit code is not hidden behind a pipe; every launch passes a dry run first.
   Add a compare script (metric at matched epochs, per stratum) and the
   runs.csv generator.
4. **Pipeline brief** from a read-only subagent: inputs, normalization, loss and
   its reduction, optimizer and schedule (and whether the schedule depends on
   the epoch cap), what the evaluation scores on which weights and sample set,
   where every series is logged.
5. **Check the instrument.** The evaluation logs every quantity the objective
   is judged on, per stratum. Define each statistic once, in code. Test every
   read-out statistic on an ideal case and a null case before it may promote
   or demote a run.
6. **Design review** by a fresh reviewer: verify the premise from existing
   data, judge the mechanism, rank levers with their reachability.
7. **First run:** if the reference has fewer than two seeds with the evaluation
   pinned, the first runs calibrate it (a second seed); otherwise the design
   review's top lever.
8. **Check-ins:** create them (Unattended operation) before the first launch.

## Unattended operation

- **Check-ins every 45 minutes** with the session cron tool (`CronCreate`,
  recurring; not the `schedule` skill, whose cloud agents cannot reach this
  machine), prompt `/researching-training-recipes check-in <research folder>`.
  The session's prompt cache lives an hour (per the ScheduleWakeup tool
  description), and recurring jobs fire up to 15 minutes late (per the
  CronCreate tool description); 45 minutes stays within the hour. Cron cannot
  say 45 minutes in one line: use four entries, `7 0-23/3 * * *`,
  `52 0-23/3 * * *`, `37 1-23/3 * * *`, `22 2-23/3 * * *`. The jobs are
  session-only and expire after 7 days (per the CronCreate tool description):
  recreate them at the start of every session. Without `CronCreate`, run the
  same prompt through the `loop` skill in self-paced mode; record which one
  runs in STATE.md.
- **One review at a time:** before ending a turn with a reviewer in flight,
  write "review in progress: <agent>, started <time>" into STATE.md. A
  check-in that finds that line waits for the report instead of starting a
  second review; clear the line when the report is filed. A line older than
  60 minutes, or one whose agent no longer exists (a restart kills it), is
  stale: clear it and start a fresh reviewer.
- **Exit watcher:** a background shell loop that waits for the process to
  start, then for it to exit. `pgrep -f "<pattern>"` matches the watcher's own
  shell, so anchor it on the interpreter as the launcher writes it (`^python
  <entry>`). A restart of the agent process kills watchers: check the job
  directly (pgrep, the log's last epoch) and re-arm; check-ins never rely on a
  watcher.
- **An idle node is the expensive state;** the analysis gap after a run is the
  only planned idle, and it stays short (read-out, review, launch).
- **When no run can be read against the noise,** spend the node on calibrating
  the reference, not on another variant.

### When a run has crashed or hangs

1. Classify first, from the log tail, `dmesg`, `df`, `nvidia-smi` and the
   process list: out of memory (GPU, or the host OOM killer ending this run
   because of its own memory), NaN or divergence, a code error, killed from
   outside (a reboot, or `dmesg` showing another process's memory caused the
   kill), an environment fault (disk full, a GPU error, `nvidia-smi`
   failing), or a hang (process alive, log silent for more than three
   epoch-lengths, GPU utilization flat).
2. A hang or a dead run is the loop's own run, not someone else's job: stop it
   (SIGINT, then SIGTERM) and kill leftover data-loader workers whose command
   line is this run's entry point and config, so the GPU frees. Never touch a
   process the loop did not launch.
3. Killed from outside with the configuration unchanged: resume from the last
   checkpoint, once. Out of memory, NaN or a code error: do not retry
   unchanged. A code error goes through the systematic-debugging skill and is
   fixed in the worktree with a test; the fixed run is a new run under a new
   name with its own registration.
4. File the crashed run VOID in HISTORY.md and STATE.md with the log lines
   that show the cause. If no fix is ready, launch the calibration run.
5. An environment fault, or a second crash in a row, stops launching: log it
   in STATE.md for the user, leave the node idle, and re-check at every
   check-in; resume the loop once the fault is gone. This is the one idle the
   loop allows, and it is not waiting for a decision.

### Check-in

1. Read `<research folder>/STATE.md`, then the environment rules file it
   names (Environment rules). Its rules, holds and next actions override this
   list.
2. Check the job directly: `nvidia-smi`, pgrep for the entry point, the log's
   last epoch.
3. Crashed or hanging: When a run has crashed or hangs.
4. A review in progress and not stale: wait for its report.
5. A run ended: The loop, from filing its numbers to the launch.
6. Reply with two lines of status.

## tmux

```
tmux new-session -d -s research -x 220 -y 50 -c <repo>     # once
[ "$(tmux display -p -t research '#{pane_current_command}')" = bash ] \
  && tmux send-keys -t research '<launcher> <config>' Enter  # per run
```

- One session, one window, runs in sequence in that shell. The user attaches;
  agents never do.
- Never send keys to a pane whose shell is not at a prompt: keys typed while a
  process holds the foreground run when it exits.
- Monitor from files, matching the signatures you would act on (Traceback,
  CUDA out of memory, NaN in the logged loss, the log silent for more than
  three epoch-lengths), not benign lines that contain `nan` or `Error`.

## The loop

```
run exits -> file its numbers (HISTORY entry, TRIED row, runs.csv, STATE)
          -> fresh reviewer analyses it and recommends the next run
          -> you choose, pre-register, and file the choice with its reason
          -> implement and test in the worktree; the node is idle now, so
             copy the change into the main tree and re-run its tests there
          -> diff the resolved config against the reference; dry run
          -> launch from the main tree; arm the exit watcher
          -> report
```

- **Review gate.** The next run is chosen only after the review; during a run
  you prepare candidates and pick none. Use the reviewer prompt from
  templates.md; save the prompt and the report in reviews/ as soon as the
  report arrives.
- **Every reviewer finding gets an outcome** before the next launch: adopted,
  or declined into TRIED.md with the condition that would reopen it.
- **Let runs finish.** Stop early only on collapse or when the user says so.

### Worktree for code during a run

`git worktree add` copies only committed files. Create it with the
uncommitted state:

```
git worktree add --detach <scratch>/wt HEAD
git diff HEAD -- <package> <tests> <configs> | (cd <scratch>/wt && git apply)
cp <untracked files the change needs> <scratch>/wt/...
```

- An editable install imports the main tree. Run tests in the worktree with
  `PYTHONPATH=<scratch>/wt` and confirm `python -c "import <pkg>;
  print(<pkg>.__file__)"` points into the worktree.
- Run the linter and formatter inside the worktree only; a repo-wide format in
  the main tree rewrites files a live job reads.
- **Every code change sits behind a config knob whose default reproduces the
  reference**, so a refuted change stays inert for every later run; if a knob
  is impossible, revert the change in the gap after a REFUTED or VOID
  verdict. Before a calibration or reference run, check `git diff` that no
  unreferenced change is active.
- Copy changed files back only while no job runs (the analysis gap), then
  launch from the main tree; a config diff does not show a code change, so
  check `git diff` for the code too. Save any change not yet copied back as a
  patch in the research folder, since the scratch directory ends with the
  session.

## Pre-registration

Before launch, the run's entry in HISTORY.md follows the header in
templates.md: hypothesis, lever class and mode with the mechanism, the one
changed knob, the reference, the clauses.

- SUPPORTED, REFUTED and VOID clauses, each able to fail given what is already
  known. Check VOID first. Write one-sided clauses one-sided; check that
  conjunctions can be met together.
- **Every registration has a per-stratum guard:** the headline metric on the
  smallest or hardest stratum and a shape or structure metric, against the
  reference. An aggregate-only registration passed a run that was worse where
  it mattered.
- A clause decided inside the noise, or inside the disagreement of two
  estimators, is marginal, never robust. A narrow miss is a miss.
- The cost clause is relative: benchmark the changed step against the
  reference in a gap and cap at that plus a margin.
- **An added loss term states its share of the optimised objective:**
  `weight x E[term] / E[base]` from raw values, every sub-weight set
  explicitly. Scaled logging is not the objective.

## Explore and exploit

- **Label every run** explore (the first run of a lever class), exploit (a
  refinement inside one), calibration (a seed repeat) or diagnosis, with the
  reason.
- **Every run needs a mechanism.** "Untried" is not a case for an explore run;
  exploit needs a measured slope of the metric against the knob, or a named
  missing combination.
- **Keep the lever-class table in TRIED.md current:** untried, explored,
  exploited, closed, with evidence and runs; declined levers carry their
  reopen condition.
- **Cap the streak.** After three or four exploit runs in one class without a
  new mechanism, the next run explores, or the reviewer justifies staying.
- **Close a class by its fitted response law:** fit on all qualifying runs,
  compare the remaining gain with the noise in the same units, record the law
  and its residual.
- **Check reachability by the kind of change,** not by mode: any run that
  changes what the model emits or transforms the data first gets a cheap CPU
  check that it can move the target at all.
- **Stop rule:** stop the search when no class has a reachable gain above the
  noise, or each further run mainly adds design leak; spend the node on
  calibration or on extending the winner instead.
- **A lever outside the fixed decisions** is logged for the user as soon as
  the evidence names it (it may be the largest gain).

## Measurement

- **Both ends are noisy.** Seed the reference as well as the variant before a
  comparison enters the result; one reference seed can be the lucky one, and a
  drifting reference compared at one epoch is a moving target.
- **Seed nulls:** one difference is a single draw, not a width. Use fresh seeds
  for each pair, measure at the operating point, run to the full budget on
  every judged series. A result that breaks a band cannot recalibrate it.
- **Evaluation randomness** (sampled inputs, masks, crops) is seeded
  independently of the run seed, or seed repeats change the test too.
- **Criteria wider than jitter:** judge on a smoothed endpoint and the slope
  over the last window with its t-value, not on one raw value.
- **Matched progress, not only matched epoch:** a change that slows learning
  looks converged at an epoch where the reference had not turned yet either;
  compare it where it reaches the reference's state.
- **A rising aggregate can be a trade:** decompose by stratum before calling it
  a turn; one stratum can improve while another loses.
- **A control must run past the effect's onset.**
- **Weighting hides strata:** check how the headline weights subgroups; keep
  outputs the input already reveals out of the headline.
- **Every number names its comparator, checkpoint, epoch, definition and
  sample set.** Check any superlative against the whole table.
- **When a read-out is added,** re-rank every finished run on it and backfill
  the reference.
- **Endpoints and matched epochs, not "best of N evaluations":** the best of N
  noisy passes is biased upward. A checkpoint picked by a validated selection
  group (training.md) is a different thing and allowed.

## CPU analyses in the gaps

- **Distribution gap:** compare train and test composition on the axis the
  errors concentrate on; error on classes absent from training is a data
  ceiling.
- **Target-noise ceiling:** score two independent realizations of the
  ground truth against each other with the production metric (a second
  simulation seed, a repeat measurement). Smooth versus raw is not a ceiling.
- **A proxy analysis shows what information exists, not what to build.** Audit
  where every feature comes from and whether the deployed model can compute it
  without the target. Simulate through the real code path, compare at equal
  row counts, report the spread over seeds and proxies. Prefer robust
  estimators over linear fits.
- **Per-sample side files** (weights, labels) get a structure test and a
  fingerprint.
- **Count the design leak:** report where a chosen value sits against the
  held-out statistic; a growing leak is a reason to stop.
- **A deliberately leaky diagnosis run** is allowed when labelled so; build the
  legal variants from it.

## Documentation

Everything the program produces goes into one folder in the repo, named for
the module and topic (`<module>_<topic>_research/`): notes, configs,
scripts, reviews, derived data, patches. Nothing a document cites may live
only in a session's temporary directory. When an existing folder is renamed
into it, leave a symlink under the old name.

| File | Holds | Changes |
|---|---|---|
| STATE.md | objective, running job, rules and holds, check-ins, logged decisions, next actions, folder map; under about 100 lines | rewritten after every step; read first at every check-in and after compaction |
| RECIPE.md | current best: config, numbers against the reference with the noise band, open points | rewritten when the best changes |
| FINDINGS.md | findings that outlive any run, each with evidence and strength | rewritten when a finding changes |
| TRIED.md | lever classes, one row per run (class, mode, change, corrected verdict, key numbers), declined levers, errata | a row per run or review |
| DEFINITIONS.md | every term, statistic and index, with the code that computes it | when a term is added |
| HISTORY.md | pre-registrations, interims, results, review summaries, decisions, user rules | append only; a correction is a new entry plus a pointer on the wrong one |
| runs.csv | one row per run, measured facts, from a script | regenerated, never typed |
| reviews/ | every subagent prompt and report, reviewer scripts | a file per report, saved on arrival |
| tools/, data/, patches/ | read-out scripts; derived CSVs and noise bands; code not yet in the main tree | as needed |

- After every run or review: append HISTORY, add the TRIED row, regenerate
  runs.csv, rewrite STATE; rewrite RECIPE and FINDINGS when they change.
- Numbers first; an interpretation is a hypothesis until a review has tried to
  break it. A correction reaches the entry, the TRIED row, STATE, RECIPE and
  FINDINGS.
- File a review in HISTORY as a summary (ten lines, a disagreement table, the
  corrections); the full report lives in reviews/.
- If the loop reads the held-out set to choose runs, state the bias where
  numbers are reported.
- Analysis scripts keep their work under `main()`, and log realized values
  after any quantization.

## Common mistakes

| Mistake | Fix |
|---|---|
| Starting without the environment rules file | Stop; the file comes first |
| Waiting for the user's go | Proceed; log the question in STATE.md |
| Queueing runs up front, or picking before the review | One at a time, after the review |
| Calling a gain from one seed of either end | Seed both; two-seed means |
| Registration without a stratum guard | Guard the smallest stratum and the shape |
| Judging a slower change at the same epoch | Compare at matched progress |
| Many exploit runs in one class | Cap the streak; explore needs a mechanism too |
| A loss term that dominates the objective | State its share before launch |
| Trusting a read-out statistic untested | Ideal and null case first |
| Proxy fit used as a design | Audit feature sources; label it an information check |
| Correction only in prose | The TRIED row, STATE, RECIPE, FINDINGS too |
| A cited file left in the session's temp dir | Copy it into the research folder |
| Check-ins lost with the session | Recreate the crons at every session start |
| Tests in a worktree importing the main tree | PYTHONPATH and a `__file__` check |
| Launching before the tested change is in the main tree | Copy it in during the gap, re-test, check `git diff` |
| A second reviewer started by a check-in | "Review in progress" line in STATE.md |
| Retrying an OOM or NaN unchanged | Classify first; a fix is a new run |
| Formatting the repo during a live run | Lint inside the worktree only |
| Absolute cost cap | Relative, from a benchmark |
| Watcher that never fires | Anchored pgrep; wait for start |
| Adopting a slower variant for a small gain | A RECIPE open point, not the base |
