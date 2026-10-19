# CHANGELOG v29_vibepass

Parent: `pipelines/v28_codexflow` (PARENT.json).

## 2026-10-18 — VibePass adapter for the Codex full pipeline

- `flow_cfg.py`: `solution_method()` — CFG/trace of the `Solution` method the VibePass wrapper delegates to.
- `flow_run.py`: `vibepass` cohort (66 PUTs, public base inputs as witnesses, silver reference, contract only at
  scoring); `Reference.contract_valid`; contract-invalid claimed bugs counted as false alarms.
- CPU check: CFG 39/66, 190 witnesses contract-valid, reference ok 190/190, 0 witness discrepancies, traces proven 93/190.
- PREREG: "v29_vibepass preregistration". Status: running.
- Launch uses the same scratch wrapper as the v28 resume (an exhausted Codex call = arm error, arm continues), applied
  from the start so one timeout cannot block the freeze. Pipeline sources unchanged.

## 2026-10-19 — results
- Relaunch after amendment 1 completed: 66/66 shared, 660/660 arm jobs, 0 failures, tool_executions 0.
- Confirmed /66: concept+input+hyp 9, flow+input 8, toolinput 8 (FA 1), plain 7, others 5–6, witness-only 0.
  Rule not passed (more FA than toolinput/plain). Bottleneck = input discovery. Report `analysis/v29_vibepass_results.md`.

## 2026-10-19 — INVALID: reference leak in prompts
- Found during v31: the `vibepass` cohort used `humaneval_mbpp_plus.jsonl` `test` as prompt-visible `base_tests`. That
  field embeds the canonical (silver) solution, the contract and all hidden inputs. 1848/1980 Codex requests contained it.
  All v29 numbers are invalid (model saw the reference). Fixed in v31 (`humaneval_mbpp.jsonl` public asserts). Folder kept frozen.
