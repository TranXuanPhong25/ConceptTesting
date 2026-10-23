# v49 definitional-concept oracle: brute-force executable spec vs plain spec programs vs TC variants

Written 2026-10-22 (Claude) before any v49 code, model call or output; v48 not yet scored. Plan:
`analysis/v48_e2e_oracle/PLAN_NEXT_v49.md` (branch A; Codex Q2 “algorithm-family independence”).

## Hypothesis
TC-full variants are generated from the PUT and can copy its bug (common-mode); spec programs (v39 DPP) on VibePass
are mostly invalid or memorized. A **definitional concept** of the task — what to enumerate, what condition to check,
how to aggregate — written as a brute-force program that is only required to be correct on small inputs, is a
different algorithm family and should agree with the reference more often on bug-exposing inputs.

## Prior art
v38/v39 (stochastic DPP spec programs; HumanEval memorized, VibePass 84 valid/23 tasks < 3 valid), v46 (TC variants,
mutant-edit guidance), v45 (in-head judge). External: ALGO (NeurIPS 2023, brute-force oracle verifies synthesized
programs, 88% correct oracles), TrickCatcher (PUT-guided variants). New here: definition concept → brute-force oracle
for bug detection in plausible programs, against matched plain spec programs and TC variants on the same inputs.

## Generation (Qwen2.5-Coder-32B endpoint, 1 worker, no PUT code shown)
Per task, k = 5 programs per arm, temperature 0.8, top_p 0.95, max_tokens 1024, seed = sha256(`v49/<task>/<arm>/<i>`)[:8].
Context: problem statement (spec), signature, public tests. Never the PUT code, never references or hidden tests.
- `defn`: “First write the definition concept as comments: `# ENUMERATE:` the candidate objects (all subsets,
  pairs, splits, orders, values …), `# CHECK:` the condition from the statement, `# AGGREGATE:` how the answer is formed.
  Then write a brute-force implementation that follows the definition literally. It only has to be correct on small
  inputs; do not optimise; no shortcuts or clever formulas.”
- `plain`: same context and format, “Write a correct implementation of the function.” (matched calls/tokens budget).
Programs loaded like v46 (PUT preamble, entry wrapper). Concept comments are kept for an accuracy audit (reported,
no gate).

## Validity and inputs
Valid program: on every public base input that finishes within 2 s it returns the PUT's output, and ≥ 1 public input
finishes. Inputs = v48's executed universe per task (all menu inputs ∪ seeded ≤ 600 pool subset); a program's
timeout (1 s) on an input = abstention (brute force is expected to time out on large inputs).

## Oracle rule (per family; same for `defn`, `plain`, and v48 `tc`)
On an input where the PUT returns normally: among valid programs of the family that return normally, if the largest
value group has ≥ 2 programs and > half of the finishing valid programs, and its value differs (typed `same`) from the
PUT's, emit one test with that value. Also reported: v46 tc-full rule (largest differing group, singletons allowed)
for every family, and cross-family `defn∧tc` (emit only if the `defn` majority value equals some valid tc variant).
Cap 20 tests/task, sha256 input order (v48). Scoring = v48/v46 `judge_test` semantics; unconfirmed counts as FA.

## Decision (registered)
Primary (concept effect at matched calls): `defn` confirmed tasks ≥ `plain` + 3 and `defn` FA tests ≤ `plain` FA tests.
Secondary (family effect): `defn` vs `tc` (majority rule) — same thresholds. Both reported on all inputs and on the
`llm_code` (v47 picks) inputs. If neither passes: close the definitional-oracle direction for this cohort.
Diagnostics: valid programs per task/arm, abstention rate, common-mode share on exposing inputs (all finishing valid
programs equal the PUT), `defn` concept-comment presence, AST similarity of programs to the PUT (memorization proxy).

## Amendment 1 (2026-10-22, after an independent read-only Opus review, before any generation beyond the 2-call smoke)
- **Concept vs family (M1):** new arm `brute` = the `defn` instruction without the three concept headings (“Write a
  brute-force implementation that follows the problem statement literally. It only has to be correct on small inputs:
  do not optimise, no shortcuts or clever formulas.”). **Concept effect = `defn` vs `brute`** (primary); family effect =
  `brute` vs `plain` (secondary); `defn` vs `tc` reported. k = 5 per arm, 495 calls.
- **Validity, one rule for all families (M2):** every public base input is run with a 2 s limit; a program is valid iff
  every public input returns normally and equals the PUT (v46 strict rule). Programs rejected only by timeout or
  MemoryError/RecursionError are reported per family. Execution cache lives under `out/analysis/v49_defn_oracle/exec`.
- **Quorum (M3):** primary rule = largest group of valid programs with value ≠ PUT has ≥ 2 members **and > V/2**, V = the
  family's valid program count; timeouts/exceptions on the input count as not agreeing. Secondary: the same over
  finishing programs only (finishing = returns normally within 1 s), and the v46 tc-full rule.
- **One decisive input set, clustering (M4):** decisive inputs = the v48 executed universe (all menu inputs ∪ seeded
  ≤ 600 pool subset); `llm_code` inputs are report-only. A gain counts only if it spans ≥ 3 distinct problems (the 33
  tasks have 24 distinct statements: 3/96, 39/58, 46/75/77, 61/65/66, 69/70, 73/74/161 share one).
  Decision: GO iff `defn` confirmed tasks ≥ `brute` + 3 on ≥ 3 distinct problems and `defn` FA tests ≤ `brute` FA tests.
- **Reporting (S1–S5):** `tc` also at k = 5 (exact mean over all C(10,5) program subsets, same quorum) plus its native
  v48 rule; per family eligible inputs, tests, FA, precision, uncapped counts; paired comparison on inputs where both
  families are eligible; bug-exposing inputs where `defn` abstains; `finish_reason=length` per arm; code extracted with
  `v7.oracle_b01.code_block` (as v46 `dpp`); per-family crashed (`skipped`) programs. A `defn`-only win is attributed to
  the concept only if the winning majority enumerates and its concept comments are correct (manual audit, reported).
- **Version-tree overlap (S6):** v7 B2 oracle (TrickCatcher DPP spec programs, ≥ 3 agree), v26/v27 (model-written
  property oracle, Qwen precision .15), v38/v39 (stochastic spec programs). DPP-only and random-family-label controls
  from the plan are dropped (v39 DPP covers 24 question ids only). v49 generation starts before v48 is scored: generation
  does not depend on v48; v48's decomposition is reported alongside to explain v49, not to choose its gate.

## Amendment 2 (2026-10-23, after an independent read-only Opus code review; before any full execute or reference read)
- **Problem span (rule clarification, M1):** “≥ 3 distinct problems” now means ≥ 3 problems with **positive per-problem
  net** (Σ defn − brute confirmed tasks over that problem's tasks), plus the task margin ≥ 3 and FA ≤ — so one problem's
  duplicated tasks cannot supply the margin while other problems net to zero. Test added.
- `tc` code extracted with `tc_full.source` (joins blocks, as v46/v48), not `code_block`.
- Execution: one process per (program, chunk of 200 inputs), 8 in parallel, process limit scaled to the job; a crashed
  or hung chunk reruns in chunks of 25 and only a failing sub-chunk abstains (`skipped`), reported. Registered rule
  (1 s per call, timeout = abstention) unchanged.
- Official-path reach only on menu ∪ `llm_code` inputs (as v48 Amendment 2); emitted tests of every family are judged
  lazily on the official path. `defn` vs `tc` (k = 10) is report-only; the k-matched view is `defn_vs_tc_k5`.
- v48 code is frozen (Amendment 2) before v49 execute; v49 pins it in its inventory.
