# v14_obgraph CHANGELOG

2026-10-14. Status: **GPU smoke complete; proposal gate failed (0/20 tasks with accepted cards)**.
Parent: self-contained copy of `v13_hyp` (v7/v11 foundation, B3/B4 tooling), excluding out/ and bytecode.
This is a LineFacts method adaptation, not a reproduction of PromeFuzz. Frozen best and active runs are untouched.

## Changes

- `experiment_schema.py`: tool concept nodes, exact spec-clause IDs, observed DATA/enclosing CONTROL edges;
  schema/purity validation, connected edge IDs, concept-to-path anchors and RETURN endpoint, duplicate-card rejection.
- `experiment_worker.py`: isolated graph extraction, T/O checks, finite base consistency, 200 domain draws;
  candidate ranking with PUT-obligation failures and surviving-mutant repair evidence; runtime path observations.
  A base input satisfying T does not exhaust its obligation. Unwitnessed obligations remain candidates.
- `experiment.py`: dedicated experimental runner; same-evidence graph/cards, concept-label removal, matched
  strategy controls, original/new-pool toolinput and zero-generation-call witnesses. Three strategy slots, <=12
  input calls, no generated expected-value requests, shared saved spec-only refs. Resume/config/source checks;
  canonical material enters only a separate final scoring stage, not proposal or generation.
- `test_experiment.py`: 14 tests in this copy, including real sandbox/draw/driver and property-scoring checks.
- `config.json`: version, fixed 20-task dev cohort, K=1, caps/seeds/arm list; no endpoint or keys.
- `README.md`, `CPU_VALIDATION.md`, `run_experiment.sh`: method scope, evidence, execution/resume instructions.

## Validation and limitations

See [CPU_VALIDATION.md](CPU_VALIDATION.md) for the earlier CPU checks. GPU result is in
[the tracked report](../../analysis/v14_v15_gpu_smoke.md): 20 proposals, no accepted semantic cards, full 180-row
fallback/control cohort. Graph/card D_IO 6/6 of 20; no graph-treatment effectiveness claim is supported.
Graph dependence is observed/approximate, not a complete PDG or event-level causal proof. Spec interpretation and O
are candidates until independently checked. Controls report actual server tokens; they are not tokenizer-equal.
This experiment uses fixed strategy slots rather than the legacy round-1 assertions/round-2 schedule. Its toolinput
arm is a matched strategy adapter, so it must not be equated with the historical one-call toolinput score.

Implementation commit: `Implement isolated obligation-graph and metamorphic concept experiments`.
