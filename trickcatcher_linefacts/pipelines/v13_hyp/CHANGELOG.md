# v13_hyp CHANGELOG

2026-10-14. Implementation of the registered **B4 v13_hyp: spec-violation hypotheses** (root `PREREG.md`).
Parent: `pipelines/v12_rel` (copied without `out/`; v12's own history is in `../v12_rel/CHANGELOG.md`).
Started by Codex (proposal parser, CPU checks, partial arm wiring), finished by Claude. No commit/push, no LLM or
network call, no GPU run. All four fairness flags stay on; caps 8 calls / 20 assertions per sample.

## Changes vs v12_rel

- `hypotheses.py` (new): proposal prompt (spec + numbered PUT + base tests + v12 relation chains of ALL candidate
  sites, each marked executed / NOT executed by base tests; no witnesses), one call per task (seed
  `seeds.hypotheses + task`, temperature 0, cached in `<out>/hypotheses/<task>/summary.json`, shared by K samples
  and both hyp arms). Robust parsing: first JSON array or `{"hypotheses": [...]}` in the reply (fences/prose
  ignored); each row checked alone, failures recorded with a reason: R must be a docstring quotation ('exact' =
  contiguous words, case/punctuation ignored; 'near' = difflib >= 0.9, for typo fixes like task 3 'fallls'); chain
  lines must be candidate lines; T = function, lambda or expression, compiled through the B5 purity checker
  (`preconditions.predicate`); rows beyond 6 rejected. Ranking + `slim()` view for generation.
- `hyp_worker.py` (new, runs only in the isolated v4 worker): `candidates` (v12 relations for every executable
  line + def lines, coverage.py base coverage, v4c frozen mutant pool 80+80 with the facts seed, survivors rechecked
  on base tests); `check` (T re-checked for purity in the sandbox; dropped as "already tested" if any base input
  satisfies T; dropped if T raises on every base input; witness search = v4c domain strategy filtered by T, 200
  seeded draws, validated by the mined B5 validator; the first of the first 20 witnesses on which the PUT differs
  from >= 1 surviving mutant (shared scorer `outcome_equal`), else the first witness; unwitnessed kept, marked);
  `classify` (inherited classification + T hits; counts use valid inputs only); `filtered_draw`; `attribution`.
- `hyp_prompts.py` (new): visible block = R, chain, T only (never witness/search/mutant data). Budget = v12 rule per
  unit: round one fitted to the task's rel-hybrid round-one block; a round-two hypothesis i fitted to the rel rendering
  of hint i (whole rel block if the task has no hint i). LLM strategy request uses the rel/flat template (`FACT:`).
- `hyp_generation.py` (new): `hyp-hybrid` round 1 (top-3), round 2 for each shown hypothesis whose T no valid round-1
  input satisfies: T-filtered domain draw (100 inputs, cap 500, per-sample seed, <= 2 kept); LLM strategy (<= 1
  retry, verified by T) only if the T-filter yields no valid T-satisfying input; strict expected-value request for
  exactly the kept inputs (skipped when none). `hyp-witness-only`: witnesses of the shown hypotheses, no LLM,
  `== None` placeholders (as witness-only).
- `run_v4.py`: hyp arms selectable via `--arms`/config; they enable B3 budget equalization; proposals prepared after
  relation extraction (`hypotheses.prepare_tasks`); manifest gets `hypothesis_version`, `hypothesis_proposal_calls`.
  Rows record `hypothesis_proposal` (calls_per_task = 1, `counted_in_llm_calls: false`), `t_filter_requests`,
  `missed_hypothesis_indices`, `shown_hypotheses` (order/witnessed/mutant_diff/covered_site) and
  `hypothesis_input_records` (T hits of every final assertion). With no hyp arm selected nothing changes.
- `v4_prompts.py`: hyp arms in `ARMS`; own seed range (400000 + 2*task + arm index). `v4_runtime.py`: new files in
  source hashes. `v4_worker.py`: `hyp_*` modes; `draw` accepts an optional `trigger_src` filter.
- `config.json`: VERSION v13_hyp, `seeds.hypotheses = 20261014`, default arms hyp-hybrid, hyp-witness-only,
  flat-hybrid, rel-hybrid, plain-hybrid, toolinput, witness-only.
- `rel_report.py`: B4 pairs added (hyp vs flat, toolinput, rel, plain, witness-only; hyp-witness-only vs
  witness-only). `hyp_report.py` (new): ref-only attribution of D_IO inputs to shown hypotheses (with T hit, from
  unwitnessed, from covered-site, from witnessed+mutant-diff). `run.py oracle-score` calls it for hyp runs.
- `eval_longtimeout.py` (new): evaluate with the 3600 s sandbox (same patch as analysis/v12_eval_longtimeout.py).
- `v4_evaluation.py`: MemoryError guard present (identical to v12_rel, checked).
- `test_hyp.py` (new), `TEST_RESULTS.txt`, `HYPOTHESES.md`, this file.

## Tests

`PYTHONPATH=<repo> python3 -B -m unittest trickcatcher_linefacts.pipelines.v13_hyp.test_hyp
trickcatcher_linefacts.pipelines.v13_hyp.test_rel trickcatcher_linefacts.pipelines.v13_hyp.test_fair` -> 44 tests OK
(11 new + 15 rel + 18 fair). test_hyp: parsing variants/failures and cap, rank order, proposal prompt (all sites, no
witness), real-sandbox checks on a synthetic PUT (purity re-check, base satisfaction, witness + mutant difference,
unwitnessed kept, determinism, classify/draw/attribution), fake-client flow (strict round 2 only for missed
hypotheses, T-filter vs LLM fallback, one shared proposal per task with fixed seed, no witness values in any prompt,
caps <= 8 calls / <= 20 assertions, equal budgets per unit), and with hyp arms disabled the requests, cache keys,
seeds and rows equal v12_rel (rel arms and legacy arms). CLI `--help` checks pass.

## Status

Implementation and offline checks done; GPU proposal stage and the registered dev run not done (HYPOTHESES.md has
the commands). Limits: see HYPOTHESES.md (budget truncation of hypothesis blocks is the main one).
- 2026-10-14 05:20 (Claude, before any run): budget per unit = max(rel rendering, hypothesis rendering)
  (rel_prompts.unit_target, used by hyp_prompts.block): the hypothesis block is never truncated (PREREG B4 amendment 1).
  test_hyp + test_rel + test_fair: 44/44 OK.
