# Learned concept selection and CASCADE: feasibility, 2026-10-26

Status: feasibility audit of source and existing artifacts only. No selector was trained, no new policy outcome was computed, and no LLM/API/GPU job was launched. This report does not reproduce CASCADE.

## Decision

A CPU-only supervised ranking diagnostic on the frozen v47 menu is technically feasible at $0 API cost. It is the most economical first check among the three proposed directions. Its scientific scope is narrower than adaptive retrieval: it asks whether public task/menu features predict which existing input bundles expose a bug on an unseen task.

The preceding assessment overstated the evidence when it moved directly from a perfect selector's advantage to a learnable advantage. A reference-informed maximum does not establish that observable features contain transferable selection signal.

## Prior work and available material

- [v44 results](../../trickcatcher_linefacts/analysis/v44_concept_matrix/RESULTS.md): one perfectly selected class instance reaches 20 tasks versus random-instance 10.06; input-kind union 21 versus budget-matched random 21.36, registered no-go.
- [v47 results](../../trickcatcher_linefacts/analysis/v47_concept_select/RESULTS.md): choosing three menu instances, Qwen spec+code 16, random3 18.25, first3 18, per-kind random3 19.07, perfect menu 23. Spec-only: 15 / 17.96 / 18 / 17.02 / 22 respectively. v74 and v75 also failed to beat the menu-random baseline with other LLMs; changing the selection model alone has already been tried.
- Local v47 `prepared.json` contains 33 cases without preparation errors, 841 spec+code menu items (9–40/case), and 500 spec-only items (5–40/case). v44 and v47 are overlapping measurements of the same cohort, not 66 independent tasks.
- The relevant files exist under `trickcatcher_linefacts/out/analysis/{v41_iorel,v44_concept_matrix,v47_concept_select}/`. v47 prepared data records kinds, instance names, descriptions, input bundles, and frozen menus. Generated PUT/contract/reference job/result files and official reference-check caches also exist. The score file stores aggregate menu coverage, not each item's label; a replay must reconstruct item labels from caches and reproduce the frozen score before fitting anything.
- The maximum gain over v47 spec+code random3 is 23 - 18.25 = 4.75 tasks. Ten tasks are outside the frozen menu's reach: 6, 39, 48, 58, 69, 70, 73, 74, 168, 171. Ranking alone cannot repair those missing input structures. The random baseline's 18.25 is an expectation, not an integer outcome.

The checked default Python has NumPy, but not scikit-learn/SciPy; use an existing suitable environment or prepare a standard-library ML environment before an experiment. No installation was attempted during this audit.

## What would make a diagnostic interpretable

1. Register the diagnostic and obtain the independent review required by `memory/working-rules.md` before computing policy outcomes. Freeze menus, features, estimator, tie rules, and decision rule. Do not tune against the already-read 33-task aggregate.
2. Group all rows from one underlying problem together in the outer split. For these 33 single-PUT tasks this is leave-one-task-out; if adding variants, leave the entire problem out. Train preprocessing and any feature selection only inside the training fold. If hyperparameters are chosen, use an inner task-grouped split.
3. Make learner input from public spec/code, public examples, menu text/kind, and allowed tool observations only. Case ID, reference/contract outcomes, `covered`, `perfect`, hidden tests, and post-hoc bug labels are evaluator/training-target material, never held-out features. v44 labels for the held-out v47 task must also be excluded.
4. Compare with uniform random3 (exact expectation/distribution), first3, per-kind random3, a training-fold-only global kind/instance prior, and a context-removed control. A learned selector beating uniform random but losing to a fixed prior has not established useful context dependence. Fit/evaluate both controls without held-out labels.
5. Use top-3 from the same frozen menu and report input-execution cost too: each instance has up to 32 inputs, variable duplicates and bundle sizes. Matching three concepts alone does not exactly match execution work.
6. Primary cached metric is confirmed exposure reach@3. It is not end-to-end valid assertion generation, oracle correctness, or real bug detection under an unknown oracle. Bootstrap/permutation units must be tasks, not the 841 correlated items.
7. Treat the result as exploratory on a heavily reused VibePass subset. A positive result still needs genuinely untouched evaluation; a negative result stops this feature/menu package, not all possible learned selection methods.

## Why this cannot be called a CASCADE or online-bandit replay

The relevant paper is [CASCADE: Case-Based Continual Adaptation, arXiv:2605.06702](https://arxiv.org/html/2605.06702), with [author code](https://github.com/guosyjlu/CASCADE). The separate code-documentation consistency paper also named CASCADE (arXiv:2604.19400) is a different method. The root note correctly points to the former.

CASCADE retrieves successful cases, generates a new solution, observes reward, and updates retrieval. A frozen input-bundle matrix cannot determine what a generator would produce after retrieving a different case. It can support full-information supervised ranking, but cannot establish adaptive memory growth or contextual-bandit benefit.

The author environment interface requires an evaluable reward. Hidden references can supply labels in training/offline evaluation, but exposing them for updates while claiming deployment without an oracle would change the setting. Public-test pass and mutant kills are observable proxies; they do not certify correctness against the specification. The paper's asymptotic guarantees also assume recurring similar queries and nonzero success probability; they give no finite-sample guarantee for 33 diverse tasks.

## Artifact fingerprints checked

| Artifact below `trickcatcher_linefacts/out/analysis/` | SHA-256 |
|---|---|
| `v44_concept_matrix/matrix.json` | `3fe4296b8e7a8405be9892db1564d5a8b1e5897054e4cb0cc9cc2a6b272a3faa` |
| `v44_concept_matrix/instances.json` | `e8a890a7682bcdab4047c06186c56974f53bd736e923e78d68b0825cc22581ce` |
| `v47_concept_select/prepared.json` | `5c829119ce1cb04e968f885339132e7a94b68dacb68d09e1999f6d077f82a696` |
| `v47_concept_select/score.json` | `e22d87677fb5d1efbf32ffadd944120696f920f495bd50e2d0af87ddec1f5826` |
