# v35 concept ceiling: can surviving mutants locate the real bug? (CPU only, no model call)

Written 2026-10-20 before computing anything below. Inputs: the frozen v31/v34 tool stage on vibepass_half
(`out/pipelines/v34_ftplacebo/.../vibepass_half/cases/<id>/tool.json`, `tool/phase2/{job,result}.json`: PUT and up to
200 surviving mutants run on the filtered template inputs) and the VibePass references (contract + reference solution),
used here only for this diagnosis. No new data, no LLM.

## Why
v34 post-hoc: the rank-1 fault concept exposes the bug in 6/33 tasks; 5 of 8 wins over placebo use no exposing concept.
Before any further work on ranking or prompts, check whether single-edit surviving mutants can locate VibePass bugs at all.

## Definitions (per task)
- Exposing input: a template input that is contract-valid and on which PUT outcome ≠ reference outcome
  (timeouts / skipped / unresolved excluded).
- Locating mutant: a surviving mutant whose outcome equals the reference on at least one exposing input.
  Locating line = the source line the mutant edits.
- **Ceiling (primary)**: the task has ≥ 1 locating mutant.
- Strict ceiling (secondary): some surviving mutant equals the reference on every exposing input it ran on.
- Top-1 hit: the rank-1 concept's line (tool.json `concepts[0]`, site concepts only) is a locating line.
  Also reported: any selected concept hits; rank of the first locating line in `ranked`.
- Pool coverage (reported): tasks with ≥ 1 exposing template input.

## Go / no-go rule (vibepass_half, 33 PUTs)
1. Ceiling < 17/33 → **stop** the mutant-located fault-concept direction (single-edit mutants cannot represent most
   VibePass bugs; ranking cannot fix that).
2. Ceiling ≥ 17/33 and top-1 hits < ceiling / 2 → ranking is the bottleneck: next step is ranking work on pilot20
   (dev), registered separately, then a check on vibepass_half; an LLM rerun only if top-1 rises clearly.
3. Ceiling ≥ 17/33 and top-1 hits ≥ ceiling / 2 → ranking is not the bottleneck; the loss is on the LLM side.
