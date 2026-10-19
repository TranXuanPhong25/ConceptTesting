# Plan: explicit fault-type concepts + input templates (v31_faulttemplate)

Date 2026-10-19. User request: split the implicit LLM reasoning into explicit steps — (a) locate possible fault sites
and fault types from code relations and rank concepts by fault hypothesis; (b) per-fault-type input templates based
on bug patterns. To save cost: compare with **plain only**. Model: `qwen/qwen3.5-35b-a3b` via OpenRouter
(key in gitignored `scripts/openrouter_env.sh`).

## Why now
v29 (Codex on VibePass): the oracle was good (wrong expected 2–6 inputs per arm) but only 7–9/66 tasks ever got an
admissible bug-exposing input → the input step is the bottleneck. Earlier versions left fault localization / fault
type to the LLM (v13, v21) or ranked tool facts by coverage (v7); none had a fault-type taxonomy with templates.

## Steps (all tool, deterministic, no LLM, no reference)
1. **a1 sites + fault types.** Mutants of the PUT with mutmut (standard library, `v4_tools.enumerate_mutants`). Each
   mutant → site line + fault type from a fixed table following ManySStuBs4J / PySStuBs simple-bug families:
   BOUNDARY (comparison boundary / ±1 literal in compare, index or range), OPERATOR (relational, arithmetic, boolean,
   negation, break/continue), VALUE (variable, constant, assignment), CALL (function, method, argument), plus
   MISSING_CASE (input class not handled; not expressible as a PUT mutant).
2. **a2 survivors.** Keep mutants with the same outcome as the PUT on every public base input: the public tests cannot
   tell them from the PUT, so under the competent-programmer assumption they are plausible fixed versions.
3. **b templates.** Task-agnostic operators per fault type, each one edit of one public example at one position:
   BOUNDARY v±1, site constants c−1/c/c+1 (path-condition literals of surviving BOUNDARY sites), length ±1 / = c;
   OPERATOR zero, negate, ties, all-equal, sorted, reversed; VALUE ±2, swap ends, min−1 / max+1, swapcase;
   CALL upper/lower/padding, rotate, sort desc, dedupe/duplicate; MISSING_CASE empty, single, two, all-equal, 0/1/−1.
4. **a3 rank + select.** Concept = (line, fault type). Rank by number of surviving alternatives that some template
   input distinguishes, then survivors, then type priority, then line. Take ≤ 3 concepts on distinct lines × ≤ 2
   inputs (PUT runs without exception first), fill to 6 inputs with MISSING_CASE inputs.

## Arms (VibePass 66 primary, pilot20 secondary)
- `plain`: spec + code + base tests; 2 probe rounds (inputs replayed on the PUT) + final; 3 calls.
- `fault-template`: identical loop and budget, plus the ranked concepts as guidance (site, fault type, alternatives,
  inputs with PUT output and alternative output; both marked "not an expected value").
- `template-only` (no LLM): the ≤ 6 selected inputs; discrepancy only. `witness-only` (no LLM): public inputs.

## CPU checks done before any model output
- 36 tests pass (30 inherited flowtools + 6 new). Mock client end-to-end: 3 tasks × 2 arms × 3 calls,
  freeze and score OK.
- pilot20 (dev, reference allowed): site concepts in 10/20 tasks; selected inputs expose PUT ≠ canonical in 8/20
  tasks (15/98 inputs) — same task count as the v7 fuzz witnesses (8/20).
- VibePass (tool only, no reference): mutants 9,520, survivors 2,892, site concepts in 65/66 tasks, 395 inputs.

## Decision rule
`fault-template` is "promising" on VibePass if paired task detection wins > losses vs `plain` AND its false alarms
≤ plain's. Descriptive: discovery tasks (PUT ≠ reference on an admissible final input), template-only vs witness-only.
Limitation (accepted by the user to save cost): no toolinput / placebo control, so a positive result cannot separate
the fault-type concepts from the extra concrete inputs; the next step would add an "unlabeled template inputs" arm.

## Cost
≈ 2 arms × 3 calls × 86 tasks = 516 calls; estimated ≈ $2 (prices $0.15/M input, $1/M output); hard cap
`OPENROUTER_MAX_USD` (default 5) in the env script.

## Amendment 1 — MVP half (2026-10-19, before outputs)
Run only `vibepass_half`: 33/66 PUTs, stratified by question (24/24 kept) and difficulty (hard 22 / medium 11 vs
45 / 21), seeded and outcome-blind (`half_split.py`). 198 calls, ≈ $0.8. pilot20 skipped. Default of `run_openrouter.sh`.
With n=33 only a large difference is readable; a promising MVP would be followed by the other half / full set.

## Amendment 2–3 (2026-10-19, before valid outputs)
- Leak fix: VibePass prompt-visible base tests from `humaneval_mbpp.jsonl` (the `_plus` `test` embeds the reference).
- Review fixes: public-example domain filter for templates, kills only where the PUT returns normally, survivor cap 200,
  robust client, extra free baseline `template-random` (random inputs from the same template pool). Details in PREREG.
