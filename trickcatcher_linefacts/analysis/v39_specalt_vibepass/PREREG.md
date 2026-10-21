# v39 spec-alternative gate on VibePass half (Qwen2.5-Coder-32B DPP programs)

Written 2026-10-20 before generating or computing anything below. v38 found the pilot20 (HumanEval) spec programs
memorized (182/183 canonical-equivalent), so the CASCADE / TrickCatcher-style "second version from the spec" could not
be judged there. VibePass tasks are LeetCode problems from LiveCodeBench (HumanEval-style format only), far less likely
to be memorized. Correction to v38 RESULTS: VibePass was wrongly listed with the memorized sets.
Prior art: B2 ref oracle, v7_mutref, tc-full, v35 (template pool on the same 33 PUTs), v37/v38.

## Data
- Cohort `vibepass_half` (33 PUTs, 24 questions), as v31/v34/v35. Used here as a dev diagnosis set, like v35.
- Programs: 10 per question with TrickCatcher's DPP prompt (verbatim `tc_templates/genprog_dfp_*`, SHA-checked by
  `oracle_b01.dpp_templates`), spec = the task `prompt` (signature + docstring). Model qwen2.5-coder-32b-instruct
  (user's vLLM endpoint), temperature 0.8, top_p 0.95, max_tokens 2048, seed 20261021 + 100*question + sample, one
  attempt each (a failed call = no program). Parsed with B2's `code_block`.
- Valid program: loads and equals the PUT on every public base input (the PUT passes the public tests).
- Pool U (evaluation only): the task's `base_input` + `plus_input`, kept when the VibePass contract accepts it.
  Reference = silver solution. Comparison as v37 (atol, exception type, timeouts excluded).

## Measures (per task)
- Memorization share: valid programs equal to silver on every completed input of U (all tasks pooled).
- C': some valid program P with P(x) = silver(x) != PUT(x) for some x in U.
- Consensus witness: some x where all valid programs (>= 3) agree, differ from the PUT and equal silver.
- Consensus precision: over x where the consensus (>= 3, all agree) differs from the PUT, share where silver agrees
  with the consensus (PUT wrong).
- H': C' and the v31 template pool exposes nothing on this task (v35 `exposing_inputs` = 0).

## Go / no-go rule
Interpretable only if the memorization share < 0.5 (else report "untestable" as in v38). Then go to a model run of a
Mokav-style DET search between the PUT and spec programs only if
- G1: C' >= 17/33, and
- G2: H' >= 3.
Descriptive: consensus witness tasks, consensus precision (false-alarm risk), valid programs per task, call failures.

## Amendment 1 — 2026-10-21 00:40, after reading the first-pass output (stated openly)
1. Transport: the endpoint went offline at about 23:58 (ngrok page; 121 NotFound, 11 InternalServerError, 8 timeouts),
   so only 100/240 calls returned and 12/24 questions have programs (the 12 with lower question ids). Transport
   failures are retried once when the endpoint is back (same messages and seeds, 4 workers). Model-side outcomes
   (empty / unparsable / length) are not retried. The first-pass gate is reported as transport-incomplete.
2. Criterion flaw: "valid program equals silver on the whole pool" measures correctness, which a good spec program
   should have; it cannot separate skill from memorization. The memorization condition is dropped from the verdict.
   G1/G2 stay as registered on all 33 tasks. Correct-program share is reported descriptively, split by question id
   (< 3300 vs >= 3300, a rough proxy for problems published before / after mid-2024; Qwen2.5-Coder released 2024-09).
