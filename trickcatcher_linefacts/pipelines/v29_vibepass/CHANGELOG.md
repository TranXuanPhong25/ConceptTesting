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
