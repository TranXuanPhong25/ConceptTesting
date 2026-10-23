# v51 latent concept oracle — PREREG

Registered 2026-10-23 (Claude), before any hidden state is extracted. User approved the direction ("đồng ý") after the
literature search in `memory/latent-concept-oracle-proposal.md`. CPU only, $0, no API call, no Kaggle notebook.

## Question

Can a frozen code LLM's hidden states tell which executed input gives a wrong output (the oracle/selection bottleneck
from v41), and does routing that signal through human-defined **discrepancy concepts** (a concept bottleneck) carry
information beyond a direct correctness probe?

Prior art. In this repo: v45 asked the model in words (it abstained 66–83%), v27 used a verbal Codex oracle, and
`concept_sft_harness` (concept-head SFT) stopped for compute without results. No probing or steering work exists here.
In the literature: program-level correctness probes exist (2512.07404 LAT on Qwen2.5-Coder-7B; 2606.14530; ICML'26
activation steering on Qwen2.5-Coder-1.5B/7B; 2609.13975 line level; SAE 2505.10375, 2510.02917). None judges single
(input, output) pairs, and none uses a behavioural concept bottleneck for code.

## Model and features

- Qwen2.5-Coder-1.5B-Instruct (HF transformers, fp32, CPU), frozen. Chat-template prompt, spec only (the PUT code is
  never shown, so the oracle stays independent of the code under test):
  `Specification:\n{spec}\n\nCall: {entry}{args}\nObserved result: {returned <literal> | raised <Exception>}\n\nDoes the
  observed result satisfy the specification? Answer Yes or No.` followed by the assistant turn start.
- Features: last-prompt-token residual stream at layers {4, 8, 12, 16, 20, 24, 28}. The spec prefix is cached per task;
  a unit test checks cached = uncached hidden states (max abs diff < 1e-3) on 3 prompts.
- Also from the same forward pass, two zero-training baselines: verbal `logit(No) − logit(Yes)` at the last position,
  and minus the mean log-probability of the observed-result tokens given the prefix (intrinsic likelihood).

## Training data (MBPP+, tool-labelled; VibePass and HumanEval never used for training)

- EvalPlus MBPP+ v0.2.0 (378 tasks): spec = prompt text, canonical solution, base + plus inputs (literal ≤ 300 chars;
  up to 30 inputs per task, seed 20261023).
- Mutants of the canonical solution from mutmut 3.8's own operators (`create_mutations`), up to 8 compiling mutants per
  task (seeded choice). Canonical and mutants run on the inputs in the existing sandbox worker (v34 `ft_worker`).
- Examples: per (task, input) one correct example (canonical output) and up to 2 wrong examples (mutant outputs that
  differ by `same()`); at most 25 correct + 25 wrong per task.
- **Discrepancy concepts** (human-defined vocabulary, computed by the tool from correct output y* and wrong output y,
  first matching rule): `EXC` (exception vs value, either way), `TYPE` (different type, incl. bool vs int, None),
  `BOOL_FLIP`, `ORDER` (same multiset, different order), `SIZE` (sized values, different length), `NUM_NEAR`
  (|y − y*| ≤ max(1, 0.1·|y*|)), `NUM_FAR` (other numeric), `CONTENT` (everything else). Correct examples have all
  concepts 0.
- Split by task: 80% train / 20% validation (seed 20261023). Validation picks the layer and the L2 strength for each arm.

## Evaluation data (VibePass, saved v41 pool, no re-execution of new inputs)

- 33 PUTs of `vibepass_half`, inputs/PUT outcomes/reference outcomes from `out/analysis/v41_iorel/cases/*/{put,ref}`.
  Label as in v41 `exposure()`: contract-valid, both outcomes parseable; exposing = PUT ≠ reference (`same`).
- Per PUT: all exposing inputs (cap 40) + random non-exposing valid inputs (cap 120), seed 20261023. PUTs without an
  exposing or without a non-exposing input are not evaluable (reported).
- Clusters for sign tests: problem (identical docstring), so PUTs of the same problem count once (mean AUC).

## Arms (scikit-learn logistic regression on standardized features)

- **A direct**: h → wrong.
- **B concept bottleneck** (sequential CBM): one logistic probe per concept h → c_k; aggregator logistic on the 8
  concept probabilities → wrong. The aggregator is trained on 5-fold out-of-fold concept probabilities (grouped by task).
- **C placebo bottleneck**: B with concept labels permuted among the wrong training examples (seed 20261023); the union
  still equals the wrong label, so C differs from B only in concept identity.
- **D baselines**: verbal logit difference, intrinsic likelihood, and a surface logistic model on output features only
  (literal length, exception flag, output type one-hot), trained on the same MBPP+ data.

## Metrics

Per evaluable PUT: ROC AUC with "wrong output" as positive. Report macro mean over problems, per-problem AUCs, pooled
AUC, and top-3 hit on the sampled subset (descriptive). Validation AUC on MBPP+ held-out tasks also reported.

## Decision rule (fixed now)

- **GO (concept-centric):** B macro AUC ≥ 0.60 on VibePass; B > every D baseline in macro AUC with more problem wins
  than losses against the best D baseline; B ≥ A − 0.02; and B − C ≥ 0.02 with more wins than losses.
- **SIGNAL ONLY:** A or B ≥ 0.60 and beats every D baseline, but the B-vs-A or B-vs-C conditions fail. A latent
  correctness signal exists, but the concepts add nothing; no concept claim.
- **NO-GO:** otherwise.
- A GO justifies writing a separate plan for 7B (Kaggle) and a HumanEval TrickCatcher confirmation; it does not
  authorize them. HumanEval stays unused here.

## Review

Independent read-only review of this PREREG and the code before any VibePass score is computed (user rule 2026-10-21);
must-fixes become a dated amendment here.

## Amendment 1 — 2026-10-23, after independent review, before any probe is fitted or any VibePass score

Reason: structural facts only (no labels per eval row, no scores). The saved v41 pool has **no exception outcomes** on
contract-valid inputs (neither PUT nor reference raises), while 48% of the wrong training rows were `raised …`. Probes
and the surface baseline would mostly learn an exception detector that cannot fire on eval, and the global placebo
would not control for routing by output type.

1. Training uses value outcomes only: mutant outcomes that raise are dropped; concept `EXC` is removed (7 concepts).
   Also dropped: mutmut string-literal mutants (`XX…XX` artifacts absent in eval), wrong rows whose truncated text
   equals the correct row's, and calls equal to the MBPP prompt's own `assert` example. Rebuilt train: 291 tasks,
   13,810 examples (6,644 wrong): TYPE 915, BOOL_FLIP 1056, ORDER 78, SIZE 974, NUM_NEAR 774, NUM_FAR 2086,
   CONTENT 761. Eval file unchanged (same SHA-256).
2. Surface baseline: literal length + returned type (no exception flag).
3. **Placebo = type-stratified permutation**: concept labels permuted among wrong examples with the same returned type,
   3 seeds; C's per-problem AUC is the mean over seeds. B − C now measures discrepancy semantics, not routing by type.
4. One shared "beats every D" predicate (macro AUC above all D and more problem wins than losses vs the best D) for
   both GO and SIGNAL ONLY.
5. Recorded deviations: the layer is chosen by the direct probe's validation AUC and shared by A/B/C (L2 strength per
   arm; the placebo's L2 is chosen on seed 0). Eval keeps v41 labels but skips calls longer than 300 characters.
6. Intrinsic NLL uses the tokens overlapping the output literal (not the word `returned`), so closing tokens count.
7. Interpretation: GO needs only B ≥ A − 0.02, so a GO with B ≈ A reads "the concept bottleneck keeps the signal and
   beats a type-matched placebo", not "concepts improve the oracle". B − A wins/losses are reported.
