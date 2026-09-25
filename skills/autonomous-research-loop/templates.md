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
- CPU only: prefix python with CUDA_VISIBLE_DEVICES="". A live job owns the
  node's GPU and RAM: load no dataset, cache or checkpoint beside it, and
  edit nothing it reads.
- Read-only on the repo and every data path; scratch only under
  <scratchpad>/<task>/.
- <For an edit task only:> edit only inside <worktree>.
- No git commits, pushes or remote writes. Launch no runs.
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

## Program
- Goal: <optimize | feasibility (feasibility.md)>
- Subjects: <subject files, or "slots in DEFINITIONS.md">
- Runs: <long (long-runs.md) | short>; the reference run takes <time>

## Where it stands
- Best so far: <run, setting, key numbers vs reference with the noise band>
- Running: <unit, what it tests, pre-registration heading in HISTORY.md, ETA>
- Next candidates (chosen only after the review): <list>

## Rules and holds (binding)
- Environment rules: <path>; re-read at every check-in.
- The loop runs autonomously and never waits for the user; it stops only when
  the user says so or on the stop rule.
- <every rule the user gave, verbatim, with date>

## Check-ins
- <CronCreate, four entries | loop skill>, prompt
  `/autonomous-research-loop check-in <research folder>`, created <date>.
  Session-only: recreate at the start of every session.
- Review in progress: <none | agent, started time>

## Decisions logged for the user (never blocking)
- <question, the default taken, when>

## Next actions
- <what the next check-in does>

## Map of this folder
| File | What it is | How it changes |
```

## VERDICT.md skeleton (feasibility)

```
# Verdict: <question>

Updated <date>. Answer: <go | no-go | not shown within budget>.

## Registration
<question, success bar, kill criteria, budget; every change with its
HISTORY entry>

## Bounds
- Upper bound: <probe, result against the bar>
- Trivial baseline: <probe, result against the bar>

## Evidence
| Probe | Class | Result against the bar | Noise band | Scale |

## What would change the answer
<...>

## Next step
<go: what an optimization program starts from | no-go: the reopen condition>
```

## Pre-registration header (in HISTORY.md, before launch)

```
### <id>: <unit name> (pre-registered; <length>; <class>, <explore|exploit|calibration|diagnosis>)

Change against <reference run>: <the one knob, or the sweep of one knob>.
Mechanism: <why it should move the target>. Reachability: <the off-device
check and its result, if the change alters what the system outputs or the
data>. Cost: benchmark <x> %. Subject additions: <the subject's registration
additions>. Judged at <point> against <reference> at the same point (and at
matched progress if the change alters speed):
- VOID (check first): <does not reach the point; evaluation or sample set
  differs; the subject's VOID signatures; relative cost cap>.
- SUPPORTED: <convergence clause>; <headline clause>; per-stratum guards:
  <small-stratum metric <= x * reference>, <shape metric <= x * reference>.
- REFUTED: <clauses that can fail given what is known>.
- Otherwise INCONCLUSIVE: next is <the calibration or follow-up unit>.
- Reported, not judged: <...>.
```

## Reviewer prompt (after every unit)

```
<subagent rules block>
You are a fresh, independent reviewer. Be adversarial and evidence-driven.
Work fast: the node is idle until you report.

CONTEXT. Read <folder>/STATE.md, DEFINITIONS.md, and in HISTORY.md the
sections <pre-registration and result of the unit>. Data: <per-stratum CSVs,
decompositions, log paths>. Prepared candidates: <list with paths>.

TASKS
1. Verify the result: reproduce the judged numbers; judge every
   pre-registered clause literally in a table (VOID first).
2. Check the traps: sample sets, stratum weighting, matched progress, trade
   versus turn, replicate noise.
3. Grade each claim measured / inferred / speculative / unverified; name what
   the program is biased toward.
4. Propose the next unit BEFORE reading the prepared candidates; then judge
   the candidates. One knob, explore/exploit with its mechanism, a
   pre-registered criterion with stratum guards and VOID first; flag closed
   experiments.
```

A design review at a new objective uses the same shape with tasks: verify the
premise from existing data, judge the mechanism, rank candidate levers with
their reachability, say whether the test bed can show the effect.

## Run report to the user

```
Report: <unit>, <length>
| point | reference replicate 1 | reference replicate 2 | unit |
- Verdict against the pre-registered clauses (VOID first)
- Per stratum and per output: what moved, by how much
- Cost: relative cost vs reference
- Next unit and the evidence for it (from the review)
```
