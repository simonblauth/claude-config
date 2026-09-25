# Performance runs: an implementation against its reference

The subject file for runs that time an implementation, such as a GPU kernel,
against a trusted reference implementation (SKILL.md, Subjects). Correctness
is a gate; speed is the objective.

## Slots

- **Run and progress unit:** one variant on the whole case set: the
  correctness check against the reference, then timed repeats per case. The
  progress unit is the repeat.
- **Replicate:** a fresh process with the same build, cases and inputs, which
  redraws clocks, caches, allocation and scheduling.
- **Default band and judged statistic:** none until measured. Replicates are
  cheap, so measure the band before the first comparison. The statistic is
  the median over timed repeats after warm-up, per case; DEFINITIONS.md names
  it and the repeat count.
- **Lever classes:** algorithm (search or traversal strategy, its
  complexity), data layout and memory access, parallel decomposition (work
  per thread, block shape), precision, pruning and early exit, host-device
  transfer and batching. **Safe levers:** every lever that keeps the output
  within the tolerance and the interface unchanged. A change to the
  interface, the accepted inputs or the tolerance waits.
- **Pipeline brief:** the reference implementation with its inputs and
  outputs; the case set and how it relates to deployment inputs; the
  tolerance and where it comes from; one profile of the reference that shows
  where its time goes (transfer, device compute, host).
- **VOID and crash signatures:** an output outside the tolerance on any case;
  a timing taken while the node was busy; a timer stopped before the device
  finished. Crash signatures: `CUDA error`, `illegal memory access`, out of
  memory.
- **Registration additions:** the tolerance and the case set, unchanged from
  the reference; the profiler metric the mechanism should move (bytes moved,
  occupancy, kernel count, transfer time).
- **Diagnostics:** Diagnostics for a finished unit, below.

## Decision rules

- **Correctness gates every timing.** Before a variant is timed, its output
  matches the reference on every case within the tolerance. Test the check
  itself first: the reference against itself passes (ideal case), and a
  perturbed output fails (null case). A faster wrong result is VOID, and the
  wrong result is a bug for the systematic-debugging skill.
- **Time what the device does.** Kernel launches are asynchronous (CUDA C++
  Best Practices Guide, Using CPU Timers): synchronize immediately before
  starting and before stopping a host timer, or time with device events.
  Exclude warm-up (first-call compilation, allocation, context creation) and
  report it separately when deployment pays it.
- **Budget the time before tuning it.** Time the reference end to end and in
  its parts (transfer, device compute, host). A lever that shrinks a part
  worth 5 % of the total cannot win more than 5 %.
- **Strata are cases.** Guard the largest or slowest case and the worst-case
  error; an average speed-up can hide a case that got slower.
- **Precision is a trade.** A lower-precision variant reports its error
  distribution beside its speed, and enters RECIPE.md only inside the
  tolerance on every case.
- **Scaling shows the mechanism.** Time each leading variant over a range of
  input sizes; the curve's shape matches the complexity the design claims, or
  the claim is wrong.
- **Close a class at a bound.** A class is closed when the profile shows its
  part at a hardware bound (memory bandwidth, compute throughput) or at the
  target the user set.

## Diagnostics for a finished unit

Run them in order; stop when one explains the result.

1. **Correctness table:** per case, the maximum and the distribution of the
   error against the tolerance.
2. **Timing table:** per case, the median and the band for every replicate,
   the reference beside it.
3. **Profile of the leading variant:** which part moved, and whether it moved
   through the registered metric.
4. **Scaling** over input size.
5. **Speed against accuracy,** when a lever trades one for the other.
