# Validation — 2026-11-01

- **15 engineering checks passed**: first14fixture tests, then a targeted15th check
  for the toolinput-only context-budget edge. Independent review reproduced14 and
  inspected the final targeted fix; no remaining architecture/safety blocker.
- Tests cover exact arm prompts, input parsing, standalone writer/base-filter parity,
  full outcome/statistics/accounting parity, cache identity, safe read-only failure,
  stage insertion/dependency rejection, custom arm config drift, zero-model witnesses,
  task-definition drift and the all-task input-generation/oracle barrier.
- Default CLI `final/.venv/bin/python -m final.modular.run` completed read-only replay
  of **all164tasks /2296stage events**. Every reconstructed input/oracle/result JSON
  equals its historical artifact; **the complete summary matches**, including all
  comparison rows, p-values, valid input counts, usage and rejection diagnostics.
- Same raw totals:plain78,classical74,contrastive78,placebo86,toolinput140,witness53.
  This is equivalence validation, not a new benchmark or evidence of concept gain.
- Replay constructed no live model, called no API, and did not execute native PUTs.
  Engineering fixtures separately use the sandbox on tiny synthetic programs.
- Hash verification passed for23original experiment source/cohort/summary/freeze
  files recorded before implementation. Original v1/recovery source, PUT cohort
  and completed results remain unchanged. Snapshot lives in ignored
  `final/out/modular_validation/original_hashes.json`.
- New runtime code has no1–2character local binding names. Syntax compilation and
  diff whitespace checks pass. Source remains uncommitted per user instruction.

## 2026-11-02 — V11 concept-only arm

- **26 engineering checks passed**: the original15 plus11new checks. New checks
  cover one modern inputs-only generation call, exact shared settings/seed/common
  prompt, witness/mutant/reference exclusion, immutable imports, wrong PUT/spec/
  model/source rejection, cache-only/read-only execution bans, mining/facts-only
  dispatch, location translation, visible-owner selection, dependency order,
  checkpoint reuse and propagation of model/cache/CPU-idle infrastructure failures.
- A read-only upstream-cache integration check imported **525selected V11 cards
  from264PUTs/28complete task caches**, without inference, native work or scoring.
  All selected locations with a method line mapped to raw source in that sample.
- Historical **164task/2296stage-event** replay still reconstructs the full saved
  summary. This validates the default six-arm behavior; it is not a benchmark
  result for the new arm. Default CLI remains read-only replay.
- All23original snapshot hashes and4533completed artifacts from the user-stopped
  full-V11 run remain unchanged. That service is inactive/MainPID0, with STOP marker
  and user_stopped statuses;288durable results remain available as checkpoints.
- No model request, new benchmark input suite or outcome was produced for the
  new arm. No independent review of this new arm or efficacy claim is asserted.
  Changes are local and uncommitted for user review; no automatic launch.
