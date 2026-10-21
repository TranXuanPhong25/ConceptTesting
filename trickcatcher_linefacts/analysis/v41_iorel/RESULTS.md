# v41 observed I/O relations — CPU ceiling results (2026-10-21)

Output `out/analysis/v41_iorel/ceiling.json` (+ `packages.json`). Rule: PREREG.md with Amendment 1 and the re-review
note, all committed before the run (4b23280). Independent review: two read-only passes, GO after fixes.

| measure (vibepass_half, 33 PUTs) | value |
|---|---|
| C1: sampled inputs (x or T(x)) expose the bug, batch + official | **22/33** (template pool v35: 17; plain Qwen3.5 discovery v31: 19) |
| C2: the shown relation package (≤ 32 inputs) exposes | **11/33** |
| expected C2 of k random executed inputs (same k per task) | 8.94 |
| median per-task lift (tasks with C1; empty package = 0) | **0.38** |
| tasks with C1 but no relation passing the minority/majority rule (empty package) | 8/22 |
| validity of sampled inputs / of shown inputs | 53% / 63% |
| batch vs official agreement on re-checked inputs | 733/733; 0 timeouts |

**Verdict by the registered rule: no-go** (C2 11 < 17, median lift 0.38 < 2; C2 > random-k holds, 11 > 8.94).

## Reading
- Inputs are no longer the binding limit: type-inferred Hypothesis sampling from the public examples reaches a
  bug-revealing input in 22/33 tasks, more than the template pool or plain Qwen3.5. But it needs ~1–5k inputs per task,
  and the base exposure rate varies from 0.05% to 74%.
- The relation package does not pick the bug-revealing ones reliably. Where a package exists (14 tasks) it exposes in
  11, often in tasks where most inputs expose anyway (96, 132, 164, 85). It enriches strongly in a few tasks
  (87: lift 35, 124: 8, 161: 4, 141: 2), and 8 tasks get no relation at all (all transformations either change the
  output most of the time or leave it unchanged).
- So the open problem moves from "reach a bug-revealing input" to "recognise which executed input is wrong", which is
  the oracle side. Observed metamorphic minorities alone do not solve that.
