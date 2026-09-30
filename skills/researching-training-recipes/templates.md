# Templates for a research loop

Copy these and fill the angle brackets. They are the starting shapes; keep what
the program actually uses.

## Environment rules file

SKILL.md stops unless this file exists with every section filled. Save it as
`RESEARCH_RULES.md` in the working directory, or pass its path.

```
# Research environment rules

## Storage
<every shared or network mount: what may be written there, how much may be
read (e.g. training through local caches, analyses on metadata or small
slices, never bulk copies)>

## Cost
<what may add cost beyond running this machine, if anything>

## Node busy
<the checks that show the node is busy, e.g. a process in
nvidia-smi --query-compute-apps, or a training driver in ps>

## Paths
- Python: <env python>
- Writable data root: <path>

## Project rules
<the repo's hard rules, e.g. precision, data and output policy>
```

## Subagent rules block

Put it at the top of every subagent prompt, reviewers included, with the
environment rules file and STATE.md's rules pasted verbatim into their slots.

```
HARD RULES (binding):
- CPU only: prefix python with CUDA_VISIBLE_DEVICES="". A training job owns
  the GPU and its RAM: load no dataset, cache or checkpoint beside it, and
  edit nothing it reads.
- Read-only on the repo and every data path; scratch only under
  <scratchpad>/<task>/.
- <For an edit task only:> edit only inside <worktree>.
- No git commits, pushes or remote writes. Launch no training.
- Never propose a lever the rules below forbid.
- Reply with your report as your final message (under <N> words); do not write
  a report file.

ENVIRONMENT RULES (<rules file path>):
<the environment rules file, verbatim>

RULES AND HOLDS (STATE.md):
<STATE.md's Rules and holds, verbatim>
```

## STATE.md skeleton

```
# State of the <module> <topic> research

Read this first at the start of a session, after a context compaction and at
every check-in. Rewrite it (do not append) whenever the state changes.

Updated <date>.

## Objective
<the user's goal in one paragraph, the headline metric with its strata>

## Where it stands
- Best so far: <run, setting, key numbers vs reference with the noise band>
- Running: <run, what it tests, pre-registration heading in HISTORY.md, ETA>
- Next candidates (chosen only after the review): <list>

## Rules and holds (binding)
- Environment rules: <path>; re-read at every check-in.
- The loop runs autonomously and never waits for the user; it stops only when
  the user says so or on the stop rule.
- <every rule the user gave, verbatim, with date>

## Check-ins
- <CronCreate, four entries | loop skill>, prompt
  `/researching-training-recipes check-in <research folder>`, created <date>.
  Session-only: recreate at the start of every session.
- Review in progress: <none | agent, started time>

## Decisions logged for the user (never blocking)
- <question, the default taken, when>

## Next actions
- <what the next check-in does>

## Map of this folder
Environment rules file: <path>. Topics and the folder's rules: the root README.md.
This folder (<loop>/llm/):
| File | What it is | How it changes |
The loop's human pages: ../human/CURRENT.md, MODELS.md, FINDINGS.md.
```

STATE.md lives in `<loop>/llm/`, the loop folder.

## Root README skeleton

```
# <Module> <topic> research

<one paragraph: what the program is for, and where the project background is>

Every topic has two parts: `human/` (the pages a person reads to decide)
and `llm/` (the complete record for agents).

## Topics
| topic | read first | what it answers | full record |
|---|---|---|---|
| <loop> | <loop>/human/CURRENT.md | <the loop's question> | <loop>/llm/ (STATE.md is the entry point) |
| <study> | <study>/human/<page>.md | <its question> | <study>/llm/ |

## Rules for this folder
- One source of truth: a human/ page summarises and links; every number it
  shows is in a file under llm/.
- Self-contained: every report, script, config and derived table the work
  rests on is in this folder; bulk raw outputs outside it are listed in the
  manifest in <loop>/llm/data/.
- human/ holds only decision pages and the dated galleries; everything else
  is in llm/, next to the script that made it.
- Every llm/ folder has a README (what, how made, how to reproduce).
- No symlinks; real paths only.
- Run the link checker in <loop>/llm/tools/ after editing any page.
- The hard rules are in <loop>/llm/STATE.md, "Rules and holds".

## Moved paths
| old path | new path |
```

## Human page skeletons

Each page answers one question; its first paragraph is the answer. Keep a
status page to about one screen and a study report under about 150 lines.

`<loop>/human/CURRENT.md`:

```
# Where does the <topic> loop stand?

<Date>. <Two sentences: the current best and the state of the loop.>

## While you were away            (only after an unattended stretch)
| run | what changed | verdict | details |

## Current best
<model, one line of what it is, the two or three numbers that make it the
best, each against the reference with the noise band and a link>

## Running now
<run, what it tests, the result that would change the plan, ETA>

## Decisions for you
- <question, why it matters, the default taken meanwhile>
```

`<loop>/human/MODELS.md` (training loop; training.md):

```
# Which model should be used?

<The answer in one paragraph: the current choice, and whether a candidate
beats it.>

| | <current best> | <candidate> | noise band |
|---|---|---|---|
| <deciding metric> | | | |

## What is missing for a decision
- <one line each>
```

`<loop>/human/FINDINGS.md` (or one page per finding):

```
# What must a reader know?

## <Finding, as a statement>
<Two to four lines: what was measured, against what, what it means for how
results are read or what to do. Link to the evidence.>
```

## Pre-registration header (in HISTORY.md, before launch)

```
### <id>: <run name> (pre-registered; <epochs> epochs; <class>, <explore|exploit|calibration|diagnosis>)

Change against <reference run>: <the one knob>. Mechanism: <why it should
move the target>. Reachability: <the CPU check and its result, if the change
alters what the model emits or the data>. Cost: benchmark <x> % per step.
Judged at <epoch> against <reference> at the same epoch (and at matched
progress if the change alters speed):
- VOID (check first): <does not reach the epoch; eval seed or sample set
  differs; NaN; relative cost cap>.
- SUPPORTED: <convergence clause>; <headline clause>; per-stratum guards:
  <small-stratum metric <= x * reference>, <shape metric <= x * reference>.
- REFUTED: <clauses that can fail given what is known>.
- Otherwise INCONCLUSIVE: next is <the calibration or follow-up run>.
- Reported, not judged: <...>.
```

## Reviewer prompt (after every run)

```
<subagent rules block>
You are a fresh, independent reviewer. Be adversarial and evidence-driven.
Work fast: the GPU is idle until you report.

CONTEXT. Read <folder>/<loop>/llm/STATE.md, DEFINITIONS.md, and in HISTORY.md the
sections <pre-registration and result of the run>. Data: <per-channel CSVs,
decompositions, TB paths, family map>. Prepared candidates: <list with paths>.

TASKS
1. Verify the result: reproduce the judged numbers; judge every
   pre-registered clause literally in a table (VOID first).
2. Check the traps: sample sets, stratum weighting, matched progress, trade
   versus turn, seed noise.
3. Grade each claim measured / inferred / speculative / unverified; name what
   the program is biased toward.
4. Propose the next run BEFORE reading the prepared candidates; then judge the
   candidates. One knob, explore/exploit with its mechanism, a pre-registered
   criterion with stratum guards and VOID first; flag closed experiments.
```

A design review at a new objective uses the same shape with tasks: verify the
premise from existing data, judge the mechanism, rank candidate levers with
their reachability, say whether the test bed can show the effect.

## Run report to the user

```
Report: <run>, <epochs>
| epoch | reference seed 1 | reference seed 2 | run |
- Verdict against the pre-registered clauses (VOID first)
- Per stratum and per output: what moved, by how much
- Cost: relative step cost vs reference
- Next run and the evidence for it (from the review)
```
