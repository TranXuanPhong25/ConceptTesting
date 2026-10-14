# v15_mrconcept CHANGELOG

2026-10-14. Status: **GPU smoke complete; proposal gate failed (0/20 tasks with accepted cards)**.
Parent: self-contained copy of `v13_hyp`, excluding out/ and bytecode. Local experimental engine is copied alongside
v14_obgraph; runtime imports are local, neither variant imports the other's experimental modules.
This is a LineFacts adaptation inspired by MR-Coupler/MemoRIA, not a reproduction of either paper.

## Changes

- `experiment_schema.py`: exact clause IDs, conditional relation families, pure D/tau/rho parsing, parameter
  index validation and exact duplicate removal. All applicability claims remain candidates.
- `experiment_worker.py`: paired-input domain/arity/size checking, permutation multiset verification, identity
  rejection, finite base consistency only when both inputs are already base-tested. Relations failing on untested
  buggy PUT behavior are retained. Canonical relation validity and false alarms are checked separately after generation.
- `experiment.py`: three matched strategy slots with mr-strategy/mr-blind/mr-flatfacts/placebo controls;
  original/new-pool toolinput and witness-only references. mr-strategy and mr-blind share D/tau selection filters.
  Pair budget is atomic; at most 12 distinct PUT calls. Main endpoint remains the common saved ref oracle.
- `test_experiment.py`: 14 tests in this copy, including pair validity, false-alarm scoring, capped driver and resume.
- `config.json`: version/method, the same fixed 20 dev tasks and K=1; no endpoint or keys.
- `README.md`, `CPU_VALIDATION.md`, `run_experiment.sh`: scope, evidence and execution/resume instructions.

## Validation and limitations

See [CPU_VALIDATION.md](CPU_VALIDATION.md) for earlier CPU checks. GPU result is in
[the tracked report](../../analysis/v14_v15_gpu_smoke.md): 20 proposals, no accepted semantic cards, full 160-row
fallback/control cohort. MR/blind D_IO 6/7 of 20; the semantic MR treatment was not exercised.
tau operates on input arguments only and may not call the PUT or external APIs. Full multi-API/output-dependent
round-trip testing is outside this initial experiment. Unsupported proposals are rejected rather than replaced
with canned relations. A pure/runnable relation is not necessarily semantically valid; finite canonical checking
does not establish universal validity. Same strategy-call caps do not mean identical consumed token counts.

Implementation commit: `Implement isolated obligation-graph and metamorphic concept experiments`.
