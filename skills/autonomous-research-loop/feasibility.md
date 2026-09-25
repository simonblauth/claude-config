# Feasibility: decide whether an idea works

Read when the goal is a decision (does the idea work well enough to pursue?)
instead of the best configuration. This file replaces SKILL.md's stop rule
and deliverable; the subject files still say what a run is.

## Register the question first

Before any unit, write the program's registration at the top of HISTORY.md:

- **Question:** one sentence, and the decision it feeds.
- **Success bar:** the result that means go, in the headline metric with its
  stratum guards, against a named baseline.
- **Kill criteria:** results that mean no-go, each able to occur given what
  is known.
- **Budget:** units or wall time. When it is spent, the answer is "not shown
  within budget".

The bar and the criteria change only through a new HISTORY entry that says
why, and the verdict lists every change.

## Bound it before building it

- **Order probes by cost.** The cheap bounds come first: an upper bound that
  shows whether the needed information exists at all (an oracle input, a
  best-case setting, a linear or classical method such as PCA before a
  learned representation), and a trivial baseline the idea must beat.
- If the upper bound misses the success bar, the answer is no-go without
  building the idea. If the trivial baseline already meets the bar, the idea
  is not needed; log that for the user.
- The target-noise ceiling and the proxy analyses (SKILL.md, Analyses in the
  gaps) count as probes.

## Explore wide, exploit only to rule out bad tuning

- Every lever class the question depends on gets an explore unit before any
  class is exploited.
- Exploit a class only to rule out that it failed from poor tuning: a small
  sweep of its most sensitive knob, then close it.
- Reduced scale (less data, shorter runs, smaller models) is allowed when a
  rank check against full scale holds (training.md, Screening length);
  otherwise the verdict labels those results indicative.

## Stop rule and verdict

Stop when the success bar is met (go), a kill criterion is hit (no-go), or
the budget is spent (not shown within budget). A go ends the program:
optimizing the idea is a new program with its own objective.

VERDICT.md replaces RECIPE.md; its skeleton is in templates.md. Report a
no-go as fully as a go: what was tried, what bounded the answer, and what
would reopen it.
