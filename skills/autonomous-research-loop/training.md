# Training runs: selection, levers, diagnostics

The subject file for runs that train a model (SKILL.md, Subjects).

## Slots

- **Run and progress unit:** one training run of one config; epochs.
- **Replicate:** a fresh training seed, with the evaluation seed pinned.
- **Default band and judged statistic:** about 3 %; the endpoint smoothed
  over the window, and the slope over the window with its t-value.
- **Lever classes:** training draw, loss term, model head, input information,
  augmentation, gradient routing, optimizer. **Safe levers:** loss, optimizer
  and schedule, augmentation, sampling or reweighting of the training data,
  regularization, gradient routing, run length, capacity with the same inputs
  and outputs. Changes to the model's inputs, outputs or deployment interface
  wait.
- **Pipeline brief:** inputs, normalization, loss and its reduction, optimizer
  and schedule (and whether the schedule depends on the epoch cap), and which
  weights the evaluation scores.
- **VOID and crash signatures:** NaN or divergence, `CUDA out of memory`, NaN
  in the logged loss.
- **Registration additions:** an added loss term states its share of the
  optimised objective, `weight x E[term] / E[base]` from raw values, with
  every sub-weight set explicitly. Scaled logging is not the objective.
- **Diagnostics:** Diagnostics for a finished run, below.

## Choose the selection signal

Before any run, decide what is allowed to pick checkpoints and stop runs.

Ask what the validation split shares with training. Sharing only rows means
it measures generalization. Sharing the *generators* behind the rows
(simulation seeds, subjects, sites, devices, synthetic parameter sets) means
it cannot see memorization of those generators: checkpoint selection and
early stopping then fail silently while every curve looks healthy.

In that case carve a selection group out of the held-out set, disjoint on
the generator axis, and exclude it from the reported metric. Validate it on
a few finished runs: which checkpoint it picks, and how far the reported
metric sits from its own optimum there. Keep it only if that gap stays inside
the noise band on most runs.

Score the held-out set inside the training loop every N epochs; cost the
pass and reproduce it once against a standalone scoring pass. The checkpoint
monitor must cover the objective's region: a whole-volume monitor keeps
selecting checkpoints after the region the objective cares about has been
traded away.

## Decision rules for training

- **Order levers by evidence.** Big movers for an underfitting net with train
  and val equal: capacity, optimizer steps per epoch, input information the
  net cannot infer (position, identity, a measurement). Dead ends once train
  and val diverge or the metric decouples from the loss: LR annealing, loss
  shape. Before that point, changing what the loss weights across the output
  can still win.
- **A finite set of generators invites memorization (one observed case).**
  When the training set is a fixed number of discrete generators and the
  input identifies which one it sees, the net recalls instead of learning the
  structure. One lever that worked: generator-level interpolation, blending
  two targets and deriving the input from the blend. Valid only where a blend
  of targets is itself a valid target; it delayed the memorization rather
  than removing it.
- **Partial gradient routing (one observed case).** Signature: in a net with
  one shared trunk and many outputs, a subset of outputs worsens on held-out
  data late in training while the rest keep improving, and
  training-distribution validation still improves on that subset. Partly
  scaling down that subset's gradient into the trunk removed the late turn
  and kept its quality; a full or near-full cut cost capacity and slowed
  learning. The level is task-specific: find it with a seed-calibrated sweep.
  Implement it as a training-only change (below).
- **Training-only changes** (gradient masks, stop-gradients) are tested equal
  to their literal definition in float64, run in one pass where possible, and
  must leave the forward, the checkpoint format and the export unchanged.
- **Screening length.** Run the full budget until at least three finished
  runs allow a rank check of a shorter budget against it (Spearman). Shorten
  only if the learning-rate schedule does not depend on the epoch cap (a
  cosine or one-cycle schedule does; then a short run is a different run),
  and only for effects visible by then: effects that appear late in the
  budget need the full budget or an extension of the winner. A
  cap-independent schedule lets any run be extended later by resuming, at no
  loss.

## Convergence phase

Once the recipe is settled: raise the cap, resume from the full checkpoint
(optimizer state included) so the longer run is the same trajectory, and read
every output channel for a late turn (below). Test a fresh-optimizer low-LR
stage once from the converged best; two nulls close the optimizer axis.

## Diagnostics for a finished run

Run them in order; stop when one explains the result.

### 1. Matched-epoch table

The metric of every run at the same epochs plus the endpoint, reference seeds
side by side. Learning speed is the epoch at which a run reaches the
reference's endpoint. Ahead early and level at the end bought speed, not
accuracy.

### 2. Per-class breakdown

The metric per class (each stratum of the headline: category, size bin,
region) at the endpoint.
All classes move together: an optimization change. Classes trade: the change
reweights the objective, net usually noise. One band moves: the change
addressed a mechanism only that band needs. Check the headline's weighting:
a metric weighted by element count (pixels, tokens, points) can hide a
regression on small samples that a sample-weighted per-stratum read shows.

### 3. Fit versus generalization

Train loss, validation loss (same distribution), held-out loss per class.
Compare training curves on per-epoch aggregates, never on one logged step.

- train = val = held-out, flat: capacity or steps limit.
- train = val, held-out higher, growing with a class variable: out of
  distribution on that variable; go to the distribution gap.
- train falls, val flat: overfitting has begun.
- train falls, val falls, held-out flat: loss and metric decoupled.
- train falls, val falls, held-out turns up: val shares generators with
  train; go to the selection signal, generator interpolation, and the
  per-output turn read.

### 4. Per-output turn

For every output channel: the epoch of its held-out minimum, its smoothed
end/min (mean of the last three evaluations over the minimum of the
three-evaluation running mean), and the slope over the last window with a
t-value. A turn confined to some outputs (for example those furthest from
the training inputs) while validation keeps improving on them is
memorization of generator structure, not general overfitting. Decompose
the turning outputs into level and shape, by class, at the minimum and at
the end.

### 5. Group breakdown of the held-out error

Rank groups by their share of the error in the worst class, next to their
share of samples. A few groups carrying most of the error is a data question;
spread error is a model question. Split by region too (inside or outside the
input's coverage, edge or core).

### 6. Loader and step cost

Iterations per second, GPU utilization, worker CPU. Benchmark a new
transform single-threaded first. Benchmark a model change as forward plus
backward on synthetic batches at the training shape, in alternating blocks
against the reference, in a gap. Cost the in-training held-out pass
separately; its loader forks inside a process that already holds workers.
If an intermittent hang tempts you to remove that concurrency, measure what
the removal costs every later pass first.

### 7. Noise calibration

Seed repeats of the reference and of the leading variant, with the evaluation
seed pinned (SKILL.md, Measurement). Re-read TRIED.md against the band:
everything inside it is neutral regardless of sign.

The run report template is in templates.md.
