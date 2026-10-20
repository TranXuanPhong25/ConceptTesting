# v35 concept ceiling — results (2026-10-20)

Output: `out/analysis/v35_concept_ceiling/ceiling.json`. Rule in PREREG.md (committed 49881d8 before computing).

| measure (vibepass_half, 33 PUTs) | tasks |
|---|---|
| pool coverage (≥ 1 exposing template input) | 17 |
| **ceiling** (≥ 1 surviving mutant equals the reference on an exposing input) | **14** |
| strict ceiling (one mutant equals the reference on every exposing input) | 8 |
| any selected concept on a locating line | 11 |
| rank-1 concept on a locating line | 6 |
| median rank of the first locating line (when one exists) | 2 |

**Verdict by the registered rule: ceiling 14 < 17 → stop** the mutant-located fault-concept direction.

## What limits it (diagnosis, not a rule change)
- The cap is mostly the **template input pool**, not the mutants: templates expose the bug in only 17/33 tasks, and
  where they do, a surviving mutant locates it in 14/17 and some selected concept hits it in 11/14.
- So single-edit mutants represent most of the bugs that the inputs reveal; what fails is reaching a bug-revealing
  input with public-example edits (filtered to the public-example domain). Plain Qwen alone reaches PUT ≠ reference
  in 19/33 tasks (v31), more than the template pool.
- Implication for any next concept: it must come with, or lead the model to, bug-revealing inputs; locating a site
  after the fact is not where the loss is.
