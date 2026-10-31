---
name: concept-coder-note-directions
description: 2026-10-26 feasibility correction — offline ranking feasible but oracle headroom is not learnability; PBT v4 model-specific taxonomy ablation; generator training lacks validated labels
metadata:
  type: project
---

User asked (2026-10-25) whether all directions in root `concept coder.md` can be tried. Assessment only, no run.

Already tried (core idea → version, result): data/control-flow relations, PDG/slicing → v12_rel, v13_hyp, v14_obgraph
(0/20 cards), v20, v21_flowtools (negative); concept picks tool/strategy → v18, v43, v44 (union 21 vs random 21.4),
v47/v74/v75 (≈ random, 3 models); input/behavioral/fault kinds → v44, v16, v26, v31; rule-corpus bug-concept templates →
v17, v31/v34/v35 (template pool 17/33 < plain 19); RIP reach/infect/propagate → v57–v63, v66, v68 (not promising);
execution feedback → v9_callfb dropped, v11_fair (gain = extra requests); spec obligations vs PUT facts → v23/v24, v50;
mutation feedback (MUTGEN/Meta ACH) → v7 MUTANT, v42/v46, v54; test-aware mutants → v37, v54; KITE → no code, loop
repeats v7/v31; oracle family (DeCon/AugmenTest/TrickCatcher/property) → v26/v27, v48/v49, v64; structured scenario
(KTester) → v19/v23/v24 format bottleneck; latent/hidden-state concepts → v51 NO-GO. MCTS excluded by user (v18).
Not applicable: RBCTest (REST API). FailMapper: Java, public code not confirmed → would be reimplementation.

2026-10-25 proposed follow-ups: learned/adaptive selection, PBT-Bench, and concept-supervised generator training.
The earlier perfect-pick argument and the blanket label "untried training" need the qualifications below.

2026-10-26 (Codex), user asks feasibility and known warnings for all three. Assessment only; no learned replay,
paper reimplementation, API calls, training or GPU job. Reports:

- [Learned selection / CASCADE](../research/cascade-dtl/FEASIBILITY_20261026.md): caches exist for 33 tasks, 841
  spec+code menu items. Ranking diagnostic feasible at $0 API cost; full per-item labels must be reconstructed and
  frozen v47 score reproduced. Perfect class 20 vs random instance 10 is a reference-informed ceiling, not evidence
  of learnability. Relevant top-3 headroom is 23 vs random18.25 (per-kind random19.07); 10 tasks unreachable. v44/v47
  share tasks; split by task/problem, no held-out reference features, control global prior, count input cost.
  Exposure reach is not valid assertion generation. Fixed-menu supervised ranking cannot establish CASCADE online
  adaptive retrieval; unknown-oracle deployment still lacks trusted real-bug reward. Correct CASCADE here is
  arXiv2605.06702 / guosyjlu/CASCADE, distinct from code-doc CASCADE2604.19400.
- [PBT-Bench](../research/pbt-bench/FEASIBILITY_20261026.md): public author harness, conditional technically feasible;
  current source/docs checked, no smoke run. v4 Table2 common-problem full-PBT minus framework-only: Opus4.8 +0.2pp
  CI[-3.4,+3.7], Qwen3.6Plus +6.7[2.2,11.6] (latter cross-time/infra indicative). Compare against framework-only AND
  full PBT, not only no-guidance. Historical .orig leaks/container cleanup bugs repaired by authors; pin fixed
  harness. Agentic-pbt's observational flat patterns do not prove PBT-Bench no-go or supply its pilot cost.
- [Training / CB-LLMs](../research/cb-llms/FEASIBILITY_20261026.md): research adaptation possible, not GPU-ready.
  ConceptCoder = VD/BP; CB-LLMs generation = sentiment/topic control, not tests. Missing correct/applicable concept
  → failed executable translation training population. NVC auxiliary-supervision control needed. v51 frozen-probe
  no-go is a warning, not a test of end-to-end generator fine-tuning. GPU memory/time not estimated from a smoke.

**Why:** the three proposals differ in readiness, and the previous summary overstated what oracle selection and
prior negative results establish. **How to apply:** prioritize a preregistered, independently reviewed $0 ranking
diagnostic; use source-specific controls before any PBT budget or training. Do not claim a learned selector was run.
Related: [[check-version-tree-before-proposing]],
[[v44-concept-matrix]], [[v47-concept-select]], [[kite-vs-template-paper]], [[conceptcoder-paper-facts]].

2026-10-26 follow-through after user "làm cái 1 đi": [[v78-learned-select]] COMPLETE/NO-GO. Context18 vs
random18.25/subtype prior20.5; spec-only21 equals context-free. Initial guard corrected 33 PUTs to 24 problem groups
before labels; grouped holdout and independent review. The feasibility-only status above describes the earlier audit,
not this completed follow-through. No API/GPU/new program execution or automatic expansion.
