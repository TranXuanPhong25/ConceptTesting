# v58 queued: executable concepts versus an error-pattern baseline

2026-10-24. User: after v57, assess the supplied UTGen analysis and queue a new version if useful. Status: queued design, not implemented or running. Transport must be the user's ngrok endpoint; never OpenRouter.

Planning update after inspecting the completed v57 artifacts:78responses/79attempts, but0solver witnesses on all6cases due source-support failures. The completion plan is [PLAN_PATHFAULT_COMPLETION_20261024.md](../../PLAN_PATHFAULT_COMPLETION_20261024.md). Its proposed new repair version (v60, name rechecked before implementation) precedes this comparison. Below, the intended v57-method arm means the repaired, explicitly versioned and frozen descendant; the historical v57 package is not modified or retroactively credited with repaired witnesses. Completion plan section7 supplies a concrete budget proposal (4logicalcalls×5arms×6cases=120slots), still requiring prospective preregistration/review before launch. No experiment is launched by this planning update.

## Why this is useful, and what is already tried

UTGen Appendix H already requests hypothesis/error pattern -> input -> expected output. Thus explicit verbal decomposition alone is prior work, not the new contribution. Appendix D separates attack, output accuracy and their intersection; it does not prove the corresponding concept mechanism. Tables1/2/8 support the supplied summary, but gains compare different baselines:32.94->45.29 is No-UT->UTGen debugging, while prompted->UTGen is40.59->45.29 on the hard split.

Prior local work: v31/v34 tests fixed fault templates and hypothesis guidance; v35 bounds that fixed pool. V26 tests exact/property/metamorphic oracles on shared inputs; v27/v28 identify model capability and ceiling. V48/v49 show oracle/common-mode effects. Do not present generic SC or oracle diagnosis as a new concept mechanism. V57's changed hypothesis is executable joint reach/local-infection/propagation construction rather than verbal pattern reasoning or one-position transforms.

## Primary question

Does v57's executable construction improve valid distinguishing-input and joint test yield beyond a generator already asked to reason explicitly about error patterns, at the same model/context/call/test budgets?

Arms to freeze before any v58 response:

- `pattern`: reuse the author's actual unmodified prompt artifact where possible (vendor UTGenDebug utils.py/joint_adv_prompt); preserve its requirement that the target is buggy only if the cohort has that guarantee. Record any unavoidable signature/output-format adapter. This is a prompted baseline, not trained UTGen reproduction.
- `repaired-concept`: repaired v57 descendant (proposed v60), frozen after its real-source support/construction and integration checks; historical v57 remains separate.
- `raw-evidence`: all v57 tool evidence with the same contents/order/budget; changes instruction/framing only.
- `inputs-only` and `witness-only`: distinguish conceptual guidance from concrete solver witnesses. Plain is contextual, not the sole comparator.

Use the same frozen dev cohort and public information as v57; no post-outcome selection of newly hard tasks. Freeze model metadata, all source/config hashes, prompt lengths, call/token/test caps and seed schedule. No larger N/K rescue. A plan reviewer must approve the concrete adapter and budget equality before launch.

Queue-review clarification: v57 charges a shared writer slot plus3generator calls/arm. The pattern baseline must receive equivalent overall model/call/token/test opportunity or the report must explicitly be a package-cost comparison. This concrete budget/format adapter remains to be designed, so v58 is not launch-ready. Reusing the six dev cases is not independent confirmation. Exact vLLM token preflight belongs to v57 transport, not a concept mechanism.

## Measurements and mechanism

Report separately valid-input rate, reach/obligation realization, PUT/reference input discrepancy, correct expected output, joint accuracy-and-attack, false alarms, distinct problems, execution budget and truncation/schema failures. References/hidden tests enter scoring only after generation freeze. Mutant disagreement is not true attack. For valid unequal inputs additionally report conditional oracle accuracy; keep all-task metrics to avoid post-treatment selection hiding yield effects.

The comparison separates methods, not pure concept semantics: v57 can provide extra executable evidence. `raw-evidence` is required to qualify attribution. Neither matching concept names nor self-reported use proves that a generated input realizes the obligation.

## Conditional secondary oracle diagnostic

If the frozen v57 failure decomposition shows revealing valid inputs with wrong expected outputs, assess output SC on a shared frozen input pool with a matched-compute control and an explicit abstention/coverage account. This is an oracle component diagnostic, not a new concept contribution. Do not launch merely because v57 task detection is weak. V26–v28 are the preceding oracle experiments and must be cited.

Backtracking concerns code repair. Current LineFacts discovers bugs; do not add a repair loop or claim debugging gain without a separate task definition. No UTGen training, mutation-data generation or paper reimplementation is authorized by this queue entry. Missing trained checkpoints still block trained-UTGen reproduction.

Sources: [paper v3 Appendix D/H](https://arxiv.org/html/2502.01619v3), [author artifact](../../../research/utgen-debug/vendor/UTGenDebug/README.md), [feasibility audit](../../../research/utgen-debug/REPRODUCTION_FEASIBILITY.md).
