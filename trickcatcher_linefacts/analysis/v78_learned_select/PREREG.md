# v78: offline learned concept selection (2026-10-26)

Registered before reconstructing labels or computing any new selector outcome. User: "làm cái 1 đi" following the three-direction feasibility assessment. CPU only; $0 API, no GPU, no new PUT/reference execution, no paper reproduction. Immutable v47 menus and historical caches are the complete material.

## Prior art and scope

v44's reference-informed class choice (20 versus random instance 10.06) is a ceiling, not learnability evidence. v47 Qwen top-3 selection reached 16/33 versus random3 18.25 and perfect23; per-kind random19.07. v74/v75 other LLM selectors were no-go. New here: supervised selection using outcomes of the other 32 tasks, with task-context and context-removed controls. This is not CASCADE, case retrieval, or an online-bandit efficacy test. v47 Part A itself was exploratory after hidden-input inspection; the 33-task cohort has been repeatedly reused, so this diagnostic is exploratory even with prospective controls.

## Material and integrity gate

33 v47 cases; fixed spec+code menu primary (841 rows), spec-only secondary (500 rows). v44/v47 rows are not pooled as independent tasks. Fingerprints are in `research/cascade-dtl/FEASIBILITY_20261026.md`. Reconstruct binary labels for each existing instance from cached batch PUT/contract/reference outcomes plus the cached official per-input confirmation, using the historical typed comparison and tolerance. Never execute cache jobs. Stop on missing/inconsistent cache, source/entry/input mismatch, preparation errors, or any mismatch with each frozen v47 row: menu size, covering-item count, model picked reach, first3, perfect menu, and random3/per-kind random3 expectations (historical four-decimal tolerance).

Read-only inputs and their SHA-256 are recorded and rechecked. Public task source is the PUT source in its v41 batch job, passed through the unchanged v34 `source_view.prepare`. No canonical source, contract, official result, hidden test, or label enters feature extraction. Validate the public source/entry against the batch pair before labels. Parent files never change. Missing official checks are not inferred as negative.

## Fixed estimator and feature vocabulary

Use scikit-learn 1.7.2 `DictVectorizer` and L2 `LogisticRegression(C=1, solver='liblinear', max_iter=5000, random_state=20261026)`. No hyperparameter/feature/model search. Candidate weight = N_train/(number_training_tasks * task_menu_size), so each training task has equal total weight while average row weight is one. No class weighting. A one-class training fold uses its constant empirical probability. A convergence warning is an integrity stop, not permission to tune.

Candidate-only features: kind and normalized subtype (argument index removed; mutation/coverage identifiers collapsed to their kind), argument position, `log1p(distinct bundle inputs)/log(33)`, and the menu-description's fixed punctuation/operator indicators (`==`, `!=`, `<`, `>`, `+`, `-`, `*`, `/`). No menu rank, M-id, case-id, function name, source hash, or task label is a feature. Candidate subtype/operator features are allowed public descriptions, not a fault label.

Task context has a fixed vocabulary: boolean spec keyword groups (order, duplicate, boundary, numeric, string, graph, state, optimization, membership, counting, parity, sequence), normalized `log1p` AST counts capped at 20 (For, While, If, Compare, BoolOp, BinOp, Subscript, ListComp, Dict, Set, Return, Call), and boolean calls to sorted/sort/set/dict/sum/min/max/len/range plus recursion and nested loops. Spec-only omits code AST/call features. For each context value include interactions with kind and normalized subtype; no task-text vectorizer, embeddings, or task identity. The context-removed model uses exactly the candidate-only features with the same fit settings. All vectorizers fit inside each training fold.

## Evaluation and controls

Leave one task out: train on all items from the other 32, rank only the held-out menu. One PUT per distinct problem; assert unique case IDs and public spec hashes. If duplicate specs exist, stop and amend to leave-problem-out before predictions. Both arms use the same task splits but are fit separately.

Controls: exact uniform random3; exact one-instance-per-kind random over three distinct random kinds (v47); first3; training-fold-only beta(1,1)-smoothed global kind prior; training-fold-only subtype prior (beta-smoothed, falls back to kind for unseen subtypes); and the same logistic model with task context removed. Priors use task-balanced means, one observation per task for each present kind/subtype, not individual correlated rows as independent tasks. Historical Qwen selections and the perfect menu are references, not learners.

Pick three distinct items. Round scores to 12 decimals. All strictly higher-scoring items than the boundary are retained, and selection at the boundary is uniform over tied items; compute exact expected reach and cost across all boundary-tie subsets. This expectation is the main policy score. Also save a reproducible label-blind SHA-256 tie-break realization for inspection (not the decision rule).

For each policy/task report candidate count, sum of bundle sizes, and distinct input count after union. Enumerate all menu triples. A cost-conditioned random3 control is uniform over triples whose distinct-input count is <= that policy's count; average this control over the policy's boundary-tie subsets. Report ordinary random3 mean input cost too. This conditions on execution cost but does not equalize CPU runtime or preprocessing cost. No new input/reference observations are generated.

Primary endpoint: sum over 33 tasks of expected confirmed exposure reach@3. This is not valid assertion generation. Paired differences use tasks as units. Report a 10,000-resample paired task bootstrap (seed20261026) for context model minus context-removed and each prior; these intervals describe the fixed cross-validated predictions, not full refit/population uncertainty. No candidate-level significance test or best-of-seeds/model selection.

## Prospective decision

Primary spec+code is **promising** only if all hold:

1. Expected reach >= uniform random3 + 3 tasks (therefore >=21.25; an integer realization would need22).
2. Expected reach >= its own cost-conditioned random3 + 3 tasks.
3. Expected reach >= max(first3, global-kind prior, subtype prior, context-removed logistic, per-kind random3) + 2 tasks.

Otherwise **NO-GO for this feature/menu/estimator package**. Spec-only and bootstrap intervals are secondary; do not substitute a winning secondary arm or tune/retry after seeing results. A positive result authorizes no paid follow-up, new benchmark, wider data, or training automatically. A negative result does not rule out every possible learned selector.

## Review and execution boundary

Implement and test with synthetic labels first. An independent read-only Codex review is required by the user's recorded review rule (`memory/working-rules.md`; Codex reviews remain permitted by `memory/subagents-sonnet-only.md`). Apply must-fixes as a dated appendix before reconstructing outcomes. Then freeze source/protocol hashes and run once. Engineering cache/integrity failures may be repaired transparently before any policy outcome; methodological changes after outcomes are not allowed in this run.

### Pre-outcome engineering clarification (2026-10-26)

Public menu metadata shows that nine spec-only tasks have fewer than three available kinds. As in v47, the historical per-kind random control uses one instance of each available kind there (one or two picks); primary spec+code always has at least three kinds. Report the candidate count, and keep the learned/uniform policy at three picks in both arms. This clarifies the existing historical control; no labels or new policy outcomes were computed.

### Independent-review must-fix amendment (2026-10-26, before outcomes)

Restore the original v42 loader's SHA-256 check of `json.dumps(pool_inputs)` against each v41 `ceiling.json` row's `inputs_sha256`, in addition to the existing v47 fingerprints and batch-pair/replay checks. Reviewer found that aggregate menu replay alone did not enforce the historical pool identity. Also reject parent files that change between repeated reads; pin installed dependency versions in `requirements.lock` and include that file in the source freeze. These are integrity fixes; estimator, features, controls, and decision rule are unchanged.

### Pre-label integrity stop and grouped-split amendment (2026-10-26)

The first approved invocation stopped at the unique-spec guard, before the label-reconstruction loop and before any new policy fit/prediction. Public PUT docstrings show 24 distinct exact-spec groups in 33 PUTs. Shared groups: {3,96}, {39,58}, {46,75,77}, {61,65,66}, {69,70}, {73,74,161}; remaining PUTs have unique specs. No empty specs occur. Preserve the original approval and stop record.

As prospectively required by the original duplicate-problem stop rule, replace the original assumption of 33 independent problems with leave-one-specification-group-out: every held-out PUT excludes all variants in its exact-spec group. There are 23 training problem groups, containing 30–32 PUTs. LR weights give each problem equal total weight and each PUT within a problem equal weight: N_train / (N_groups * PUTs_in_group * menu_size). Priors give each problem one observation per present kind/subtype, averaging within PUT and then across that problem's PUTs. Uncertainty resamples the 24 problem groups, summing their PUT-level paired differences, not individual PUTs/items. Continue reporting reach summed across the same 33 PUTs, so historical baselines and the prospective decision thresholds remain unchanged. Model, feature vocabulary, hyperparameters, tie rules, and primary arm are unchanged. Require a fresh independent review/freeze before continuation.
