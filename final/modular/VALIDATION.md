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
