# v41 observed input→output relations: CPU ceiling before any LLM (go/no-go)

Written 2026-10-21 before any code output. User requirement: a concept/relation must carry information the model
cannot get by reading the code (or only after a non-trivial computation that a static tool does not give).

## Prior art (version tree)
Coverage gaps v7 OUTCOME/STMT; observed data/control dependence v12/v14; invariants over the test set v7 REL/SHAPE
(dev gate); path conditions with CrossHair (`analysis/crosshair_gaps_report.md`: witnesses exposed no bug); spec→property
written by the LLM then checked v15/v26 (19% unsound with Qwen 7B); surviving mutants v7/v31–v35 (ceiling 14/33);
LLM localization with static CFG v36 (no-go). New here: relations **measured on the PUT by execution** (metamorphic
transformations of many sampled inputs), so the model only judges an observed behaviour against the spec; directly
aimed at the v35/v36 bottleneck (reaching a bug-revealing input).

## Material
vibepass_half (33 PUTs, v31/v34 cases). Generation side sees only the PUT and its public examples. References and the
evaluator contract are used only for the ceiling measurement below.

## Tool (no reference, no LLM)
1. Sampling: per argument, a Hypothesis strategy inferred from the public example values (type, element type, int
   range widened around observed values with the public sign bound kept, length range from 1×min to 2×max+2 capped at 30,
   string alphabet from the examples). N = 300 inputs per task, `derandomize=True`, no database.
2. Transformations T of a sampled input x (each on one argument position, applied when type-compatible):
   list: reverse, sort, seeded shuffle, append max+1, append min (or the public lower bound), prepend max+1, drop last
   (if length stays ≥ the public minimum), duplicate (x+x, capped length); int: +1, −1 (if ≥ public lower bound);
   str: reverse, append an example character, drop last character.
3. Outcome relation per pair (f(x), f(T(x))): equal / increase / decrease (numbers, or lengths of sequence outputs) /
   changed (other values) / exception-differs; pairs with a timeout are skipped.
4. A relation = (argument, T) with its category distribution over the pairs. Minority category = share ≤ 25% and ≥ 1
   pair. Shown package (what an LLM would see): relations ranked by smallest minority share, ≤ 8 relations, ≤ 2 witness
   pairs per minority category → at most 16 witness pairs (32 inputs) per task.

## Ceiling measurements (references only here; an input exposes if contract-valid and PUT ≠ reference)
- C1 input ceiling: tasks with any exposing sampled input (x or T(x)).
- C2 shown ceiling: tasks where some input in the shown package exposes.
- Lift: exposure rate among shown package inputs ÷ exposure rate among all executed inputs, pooled over tasks with C1.
- Reported: C2 over all minority witnesses (uncapped), validity rate, template-pool comparison (v35: 17/33).
Reference execution is batched (one process per task) for speed; a fidelity check compares it with the official
`flow_run.Reference` on 100 random inputs (must agree on all, else the official path is used).

## Go / no-go
GO to an LLM judgement step (separately registered) iff **C2 ≥ 17/33 AND lift ≥ 2**. Otherwise no-go for observed
I/O relations as the concept.

## Amendment 1 (2026-10-21, after an independent read-only review, before any reference/exposure was computed)
Review findings adopted (tool-side smoke on case 96 only had been run; its cache is deleted):
- Package cap enforced as registered: ≤ 8 relations × ≤ 2 witness pairs **per relation** (rarest minority first) →
  ≤ 16 pairs / 32 inputs. A relation needs a majority category (≥ 50%); minority = ≤ 25%. Witnesses = first pairs in
  Hypothesis order (simplest inputs).
- Size-matched random baseline: per task, exact hypergeometric chance that k random executed inputs (k = that task's
  package size) contain ≥ 1 exposing input; E[random-k C2] = sum over tasks. Per-task lift reported (median over tasks
  with C1), plus valid-only lift and the valid share of the package.
- **Gate (replaces the original): GO iff C2 ≥ 17/33 AND C2 > E[random-k C2] AND median per-task lift ≥ 2.**
- Official re-check: every shown input and up to 20 exposing inputs per task are re-run through the official per-input
  path (flow_worker via `flow_run.Reference._run`, for both PUT and reference/contract); C1 and C2 use only officially
  confirmed exposures. Agreement between batch and official values is reported. The batch path is used for pair
  categories, base rates and lift.
- Timeouts: `max_timeouts` 200 (a timed-out call no longer skips the rest of the batch), batch limit 3600 s;
  timeout/skipped counts recorded per case. Cache keyed by the job content.
- Hypothesis local-constant pool frozen with the repo's `hypothesis_replay.freeze_local_constants()`; Hypothesis
  version and an input-set hash recorded. Max size never below the public minimum length.
- Samples and T(x) filtered by the repo's public-example domain filter (`ft_concepts.in_domain`, as in the v35 pool).
- Category rule: numerically equal int/float → equal; bool or other non-numeric, non-length-changing differences →
  changed. N = 300 is an upper bound (dedup can give fewer; reported). A per-case failure is recorded, not fatal.
- Re-review (before any output): C2/C1 count an input only if batch AND official paths both mark it exposing
  (official-only exposures reported separately), so C2, random-k and lift use the same inputs; a task with C1 but an
  empty package has lift 0 (kept in the median). C1 is a lower bound (shown + first 20 batch exposures re-checked).
  Official scoring additionally requires ordinary/traced agreement (`put_observation`); not applied here, noted.
