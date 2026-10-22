# v46 mutant-concept oracle with the pipeline oracle (program variants) and a repaired judge — diagnostic

Written 2026-10-22 before any v46 model call or score. User (after the v45 audit): "đồng ý, với cái phần sai hoặc thiếu
thì sửa đi". v45 (ex-v43_mutjudge) asked Qwen to judge in its head with an "unsure" exit and 300 tokens; it did not use
the pipeline oracle. v46 repairs exactly the audited gaps on the same frozen questions.

## Prior art
TrickCatcher tc-full (10 PUT-guided variants, public-test filter, largest differing group = expected value; `tc_full.py`,
`tc_full_worker.py`), v39 (10 DPP spec programs per question, Qwen-32B, on the evaluator pool), v42 (mutant-disagreement
questions, CPU no-go for selection), v45 (in-head judge, invalid instrument). New here: the pipeline oracle on the
concept-selected questions, and the mutant fault concept given to the variant generator (concept on the oracle side).

## Material (frozen)
The 607 v42/v45 questions (`out/analysis/v45_mutjudge/questions.json`, sha256 3b4f4837…cabca); input, surviving
mutant, PUT and mutant outcomes. 31 tasks have questions. Tool side never sees references.

## Oracles / arms
Program oracles (each program runs on the task's public base inputs and on all its question inputs):
- `dpp`: the existing v39 programs (10 per question, TrickCatcher DPP prompt, Qwen-32B). No new calls.
- `tc`: 10 TrickCatcher PUT-guided variants per task with the verbatim templates (`tc_full.templates`/`messages`, SHA-
  checked), function_and_docstring = the PUT source; Qwen2.5-Coder-32B, temperature 1.0, top_p 1.0, max_tokens 2048
  (tc-full PARAMS), seed = sha256(`v46/<task>/<arm>/<i>`)[:8]. Code parsed with `tc_full.source`.
- `tc_concept`: the same call with one block appended to the user message: "Possible fault concepts (from automated
  analysis of this code; each may be wrong):" and, per distinct mutant edit of the task's questions (package order,
  ≤ 5): fault type + meaning (`ft_concepts.TYPE_TEXT`), the code line, and `before` → `after`.
Program loading (all three arms, harness-side, arm-neutral): the program is executed after the PUT's import header; if
it does not define the entry function at module level, the PUT's entry wrapper is appended (VibePass PUTs are a
`Solution` class plus a module-level wrapper).
Valid program: loads and returns the same as the PUT on every public base input (the PUT passes the public tests).
Vote rule (tc-full, primary): on a question input where the PUT returns normally, the valid programs whose outputs
differ from the PUT's form groups by value; if any group exists, a test is emitted with the largest group's value
(ties: first program order). Also reported: consensus rule (≥ 3 valid programs, all agree, differ from the PUT).

Judge (repaired v45, arms `binary`, `code`, `concept` with the same content as v45 otherwise):
- input shown as a call with parameter names (`entry(name=value, ...)`);
- schema `{"analysis": ..., "expected": ..., "choice": "A|B|neither|invalid"}`: work out the correct result first,
  then choose; no "unsure"; max_tokens 2048; temperature 0, seed 20261022, JSON mode;
- a test is emitted on choice = mutant label (expected value = mutant output) or on "neither" with an `expected`
  literal that parses and differs from the PUT output (expected value = that literal).

## Scoring (references only here; v41/v42 reference batch + official re-check as in v42)
For every emitted test: confirmed if the input is contract-valid, PUT ≠ reference (official), and the expected value
`same` as the reference; otherwise a false alarm (invalid input, PUT right, or wrong expected value).
Per arm: confirmed tasks (ceiling 15 = v42 D1, or more for `neither`/program values), emitted tests, FA tests, FA
tasks, precision; for program arms also valid programs per task and tasks with ≥ 1 / ≥ 3 valid programs.

## Decision (diagnostic)
Concept pairs: `tc_concept` vs `tc`; judge `concept` vs `code` and vs `binary`. The mutant concept on the oracle side
is worth a registered follow-up iff for at least one pair the concept arm has **confirmed tasks ≥ 8, precision ≥ 0.5,
confirmed tasks ≥ its counterpart(s) and FA tests ≤ its counterpart(s)**. Otherwise close it (with v42 for selection).
`dpp` and the v45 numbers are context only.

## Amendment 1 (2026-10-22, after an independent read-only review, before any scoring; only a 3-call smoke existed and is deleted)
- Decision rule: in addition, the concept arm must be strictly better than each counterpart on confirmed tasks or FA
  tests, and have ≥ 2 confirmed tasks its counterpart does not have (ties / seed noise do not pass).
- Program execution follows tc-full: every question input gets its 1 s call (no skipping after timeouts); a crashing
  batch is rerun one process per program, a program crashing alone is skipped.
- Program loading: PUT preamble (all top-level statements before the first class/def, except `if` blocks, plus later
  imports, i.e. including `sys.setrecursionlimit`), then the PUT entry wrapper if the program lacks a module-level entry,
  then the program. Same for all arms. Invalid reasons (load error / exception / timeout / mismatch) are reported.
- Concept block wording: "possible alternative: `before` -> `after`" (neutral, as registered).
- Judge `expected`: "None"/null/empty → no test; "true"/"false" → bool when the PUT returns bool.
- An emitted test whose value equals the reference but whose exposure the official path does not confirm is a false
  alarm (as registered), counted separately as `unconfirmed`.
- LLM cache records carry a digest of messages + params and are rejected on mismatch; generate asserts the served
  max_model_len is 8192; context overflows (task 75 TC prompt, ~30k chars) are recorded once per call and reported.
- Stated deviations from tc-full: typed `same` (int ≠ bool/float, list ≠ tuple), unparsable/truncated outputs excluded
  from groups, 2 s load timeout, 1 GB memory. DPP programs get the PUT preamble, so their validity is not comparable with
  v39 (context only).
