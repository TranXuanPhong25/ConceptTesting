# Plan: fixing step a (fault site / fault type) of the v31 fault-concept line

Date 2026-10-20. User request: after the fault-localization review, plan a fix for step a. Plan only: nothing here is
implemented or run. Evidence: `analysis/fault_localization_review_2026-10-20.md`, v35 (VibePass half), v37/v38 (pilot20).

## What is wrong with step a now (measured)
1. **Survivors are not a fix space.** A surviving mutant witnesses the bug on some exposing input in 3/20 pilot20
   tasks (v37, EvalPlus pool) and is regression-free on the valid pool in 4/33 VibePass tasks (review). Median 3
   survivors per HumanEval PUT. "Line where a one-token edit fixes the output" is rarely true.
2. **No failure evidence.** The ranking uses unresolved behaviour (survivors distinguished by templates), which is test
   adequacy, not MBFL suspiciousness (Metallaxis/MUSE need failing tests). Ranking ≈ random (11 vs 9).
3. **Labels are loose.** Template type matches concept type in 62/143; hits are scored by line only; MISSING_CASE is
   appended past the 3-concept cap; equivalent / duplicate survivors inflate counts.
4. **Benchmark contamination.** Qwen-7B spec programs equal canonical in 182/183 cases on pilot20 (v38): any
   spec-derived alternative or spec-reading LLM is near an answer key on HumanEval/MBPP-based sets.

## Fix, in order (each step is CPU-checkable before any model call)
**A1 — Two-phase localization: localize only after a failure candidate exists.** Phase 1 = any input source (plain
LLM probes, templates, fuzz) produces candidate discrepancy inputs (PUT ≠ oracle consensus, B2/full oracle). Phase 2 =
standard fault localization with that failing input versus the passing public inputs: spectrum (Ochiai on line
coverage from coverage.py) plus MUSE-style mutant scores on the same passing/failing set. The concept handed to the
next round is then a *failure-associated* site, which v31 never had. Prior art: none in the repo (v7/v31 localize
before any failure). Library: coverage.py (already pinned); Ochiai/MUSE are formulas, no new dependency.
- CPU gate (dev113 minus pilot, reference used only for scoring): with the failing inputs plain Qwen already found
  (v7/v11 runs), does the Ochiai/MUSE top-3 contain a line on the PUT/canonical first-divergence path in >= 50% of tasks?

**A2 — Use mutants as adequacy probes, not fault claims.** Keep "unresolved behaviour at line L" as a concept for
test adequacy (honest wording in the prompt: "public tests cannot tell these versions apart"), drop the "fault type"
claim unless A1 supports it. Collapse survivors into behaviour classes on the probe pool before counting.

**A3 — Code fixes found by the review** (new folder copied from v34, CHANGELOG): enforce the concept cap including
MISSING_CASE; survivors must agree with the PUT on every public input (timeouts → not a survivor); score hits by
(line, type); hash the tool cache in the generation manifest.

**A4 — Evaluate on non-memorized tasks.** Any step that uses spec-derived programs or spec reading must be checked on
data Qwen has not memorized: the self-written diag16 fixtures, or a post-cutoff set from the benchmark audit
(`research/benchmark-papers-2025-2026/`). HumanEval/MBPP numbers are reported but not used for go/no-go.

## Out of scope / already tried
- More mutation operators or a smarter mutant ranking (v7_mutref, v31, v35, v37: the fix space is the limit).
- Mokav over survivors (v37 no-go). Java/C artifacts (UnitCon, NeuroTestGen, CASCADE, HGFuzzer): not eligible (v38).
- Step b input reach remains the main bottleneck (v35, v38: 9/20 tasks exposed by EvalPlus inputs but not by templates);
  A1 only helps once some input already fails.

## Decision rule (to register before running A1's gate)
Go to a model run only if the A1 CPU gate passes (>= 50% top-3) on dev and the failing inputs it needs come from the
method's own outputs, not EvalPlus. Otherwise stop the fault-site line and keep mutants as adequacy probes only (A2).
