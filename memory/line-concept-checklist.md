---
name: line-concept-checklist
description: 2026-10-10 tester-style line-level concept checklist; $0 offline result on 132 TrickCatcher PUTs — only OUTCOME-GAP and STMT gaps beat base rate, top-3 hits ~1/5 PUTs
metadata:
  type: project
---
The user's idea, 2026-10-10: a concept is a tester's line-level reasoning. "At line k the behavior is X → which input
change makes it right or wrong." A $0 tool traces the base tests and emits facts about uncovered cells, using the
ConceptCoder BP abstract-value vocabulary. Final doc (scratchpad, ephemeral): session 7ff5ccb6 `scratchpad/loop/FINAL_checklist.md`.

Offline results (132 PUTs, excluding the 6 used for design):
- Best concepts:
  - OUTCOME-GAP, a branch that never took the other outcome: P(fail | fact) 0.52 vs base 0.15.
  - Statement never run: 0.54.
  - Surviving mutants: 60/138 PUTs, P(fail) 0.48.
- Part-gap (sign/zero) and magnitude are noisy: per PUT, the fact beats base in about as many PUTs as it loses.
- Empty/loop-count facts are worse than base (p ≈ 0.01–0.02).
- Type facts (bool/float) are 95% unreachable.
- Top-3 with a frozen ranking hits 26/132, vs 18.8 for random-3.
- About 31 missed bugs are relational bugs inside already-covered classes. A gap concept can't reach them; a relation/metamorphic concept (C13) was proposed.
- Round-1 review corrected [[hybrid-c1-verdict]]. Claim 7 was wrong: the LLM concept list did list [True,False,1] and [-10] as "not determinable", so 22 and 122 are ambiguity cases. 7 of 8 invalid diff units are in task 13. C1 hints always contain a failing input, so C1 is near-tautological.

**Why:** next step choice for the thesis concept.
**How to apply:** propose an LLM pilot only with OUTCOME-GAP + STMT + mutant facts vs covered-cell placebo + tool-input/LLM-oracle arm (~$1 for 20 tasks); setting must be white-box. Related: [[thesis-concept-requirement]], [[api-budget]].

Update 2026-10-10 (repo `trickcatcher_linefacts/`, not committed):
- The fact generator is now deterministic. Wall-clock budgets were replaced by a step budget (`sys.settrace`); two runs agree on all 139 tasks.
- Offline baseline (`offline.py`) on 112 dev PUTs (design and pilot excluded):
  - Coverage: 56% of tasks have shown facts; top-3 strongly points at the bug in 28%.
  - Top-3 PF 0.44 vs placebo-3 0.15 (base 0.17); 79% of facts are reachable by valid inputs.
  - Per-task sign test 36/23 (p = .12).
  - By kind: OUTCOME 0.46, STMT 0.46, MUTANT 0.40 (77 strong), OUTCOME-q 0.25 (weakest).
- Two hypotheses tested and refuted on the dev set (2026-10-10):
  - Down-ranking early-guard branches (raise/return before the first loop) would drop 26 spec-forbidden facts, but also 60 of the 122 strong facts. LLM-written special cases are often the bug. Don't use this rule.
  - OUTCOME-q noise is not caused by loop/index variables: those score PF 0.38 (11 facts), versus 0.21 for data variables (39 facts).
- The 23 tasks whose top-3 is worse than base break down as 5 ranking problems, 13 vocabulary problems (no fact beats base) and 5 in between.
- Ranking agents (2026-10-10, snap_v1, dev 112): the frozen ranking (31) is below random-3 (35.4); ceiling 40.
  - Its fault is "ascending line": it fills the top-3 with facts on the first guard.
  - Agent 1's R1 (one fact per block) plus R2 (boundary mutants last) gives 37, held out in both folds. That is only +1.6 tasks over random.
  - Agent 2's G′ (redundant-guard check) is promising but was designed post hoc.
  - Agent 3: no new $0 signal beats random on held-out. susp_frac (AUC .77) separates facts but cannot rank them, because spec-forbidden inputs are not detectable.
  - Docstring-example pre-check catches 3 bugs.
- Vocabulary v2 (BOUND / REL / SHAPE / NUM, invariant "never/always" facts) raises the ceiling from 40 to 63/112. The 23 new tasks come mostly from SHAPE (17).
  - SHAPE: PF 0.21 vs base 0.20, per task 36/42. Precise enough in aggregate only.
  - BOUND: 0.37 vs 0.17, 21/15. NUM: 0.33 but only 46% valid. REL: 0.26, weak.
  - strong@3 with block dedup: old kinds 36; +BOUND+NUM 37; all kinds 44.6, but tasks below base rise from 24 to 39.

## Codex 49 no-fact audit (2026-10-10, scratchpad rank/codex/REPORT.md)
- Causes: a coarse classes 14, b fuzz miss 4, c operator gap (lib call/string content) 20, d resource/STEP 7, e oracle≠spec 1 (141), f 3 (78 no in-domain bug).
- v1 snapshot: 74 raw facts on these, 65 infeasible OUTCOME-q. Families: string 19, bound 9, coll 6, rel 6, num 5, output-relation 3.
- v2 vocab gives strong fact on 17/49 (SHAPE 13); rel 0/6, resource 0/7. Missing: relation-targeted fuzz (x==y), Unicode, filtered-dup, output-sorted, workload concept.

## v2 ranking + v3 vocab (Codex, 2026-10-10; scratchpad 2dddac78.../codex_rank_v2, codex_vocab_v3)
- Ranking v2 (R1 blocks, R2, seeded tie, G′ tie→adopted): strong@3 37 = random 37.9; gain over v1 is from the pool.
- v3: course-term templates, OUTCOME-q dropped. Gate passed: MUTANT-X (PIT/MutPy SDL/call-removal/SIR/BCR/ZIL/OIL/RIL), DU. Failed: LOOP (PF < base), LOOP-MAX, OUTPUT (≈ base), DECISION, REL, SHAPE.
- v3 strong@3 46/112 (v2 37, random 43.8, ceiling 53); sign 52/20 p=.0002. 12 new tasks: 7 via new mutant ops (5 call-removal), 1 DU.
- The offline mutant hit now compares against the plain PUT, so MUTANT PF rose .40→.49 and v2/v3 are not strictly comparable. DU facts are not deduped per variable (task 64 top-3 = 3×`count`).
- Pilot tasks 108/116/131 have doc_fail. Outputs are out/facts_v3, out/offline_v3, VOCAB.md, human_eval/; all uncommitted.
- v3f (DU one per variable) frozen 2026-10-10: dev strong@3 45/112. One-time OFFLINE pilot confirmation: strong@3 5/20 (random 8.2, ceiling 10), better/worse 7/8 p=1; shown PF .31 vs base .16, placebo .14. Dev gains did NOT replicate at top-3 (n=20). OUTPUT (failed dev gate) looked strong on pilot — not adopted (no post-hoc changes).
- LLM pilot 2026-10-10: Qwen2.5-Coder-7B fp16 on Kaggle 2×T4 (vllm 0.7.3 / transformers 4.48.2 + protobuf>=5.29 fix; the vllm 0.8.4 run failed), 20 pilot × 5 arms × K=3.
  - Detections per sample: plain 6.7, concept 6.7, placebo 6.0, coverage 5.7, toolinput 7.7. Any-of-3: 8 / 11 / 10 / 8 / 10.
  - Concept vs plain 3/3 (p=1); concept vs toolinput 3/5. False alarms: concept 36% vs plain 29%. Delivery: concept 69%, placebo 56%, plain 48%, toolinput 99%.
  - Raw witness inputs (toolinput) were best. Plain wins the doc_fail tasks 108 and 131 by copying the docstring examples.
  - Throughput: 214 out tok/s batched (728 incl. prompt), 366 s generation, 191 s load.

## Gen arms + spec validity (2026-10-11)
- Pilot lesson: 7B can't do the arithmetic to build inputs (task 157 Pythagorean triple) → user chose "LLM writes an input generator": arms plain/concept/toolinput/gen-plain (TrickCatcher EvalPlus `geninput_generator_sys` verbatim, sha-checked, in tc_templates/)/gen-concept/gen-placebo; stage 2 = identical toolinput oracle prompt, no facts. Harness: gen_prompts.py, gen_inputs.py, llm_client.py (env QWEN_BASE_URL), run_gen.py. Serving = ngrok vLLM notebook (user's), fp16 TP2.
- v3f had 29% contract-invalid shown witnesses (dev 44/154) → v3c: fuzz evidence only from EvalPlus-contract-valid inputs (fuzz_validity.py hook, cap 2000 draws). Dev strong@3 45→46 (random 46.4, ceiling 53); 8 dev tasks lose all facts; random fuzz valid rate low on string-format tasks (17: 1 valid, 19: 0).
- v3m (user-approved, Qwen): preconditions mined inline per task from signature+docstring, RBCTest-style (arXiv 2504.17287, ICSE'26: observe→confirm→predicates→verifier on base/docstring inputs). Planned primary fact set for the gen run; v3c = contract upper bound.
