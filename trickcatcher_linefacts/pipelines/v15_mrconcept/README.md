# v15_mrconcept: conditional metamorphic concepts

User requested trying this direction in a separate folder on 2026-10-14. Self-contained copy of v13_hyp with local
experimental modules. Use **`experiment.py`**, not inherited `run.py`, for the new arms.

One cached Qwen call per task proposes at most six `(clause_id, family, parameter, D, tau, rho)` cards. Clause IDs
refer to exact docstring text; interpretation is candidate knowledge. D uses original function arguments; pure
tau(args) returns a full positional tuple; pure rho(args,followup_args,result,followup_result) returns bool.
Families: permutation, monotonicity, multiplicity, idempotence, round-trip. tau is input-only: it cannot call the
PUT or external APIs; full output-dependent/multi-API round trips are outside this initial scope.

Tool checks purity, arity, size and B5 validity of both inputs; identity pairs are removed, and permutation family
must preserve the selected parameter's multiset and other parameters. Candidate relations are discarded for base
contradiction only when *both* inputs were already base-tested. Failures on untested buggy PUT inputs remain useful
candidate counterexamples. 200 domain draws discover pair witnesses; ranking prefers observed candidate violations,
then witnessed/unwitnessed cards. These are not confirmed bugs or proof that the relation is valid.

Three fixed strategy slots each draw <=100 candidates (500-example cap) and select <=2 sources. A pair costs two
PUT inputs and is retained atomically; total <=12 distinct calls/sample, <=20 placeholders. Empty accepted-card slots
use generic singleton input generation, explicitly recorded. Main detection uses the same saved spec-only ref oracle
for all arms. A separate scoring-only check measures rho on canonical/PUT outputs after generation is frozen.

| Arm | Guidance / role |
|---|---|
| mr-strategy | Conditional semantic family, exact spec clause, D/tau/rho |
| mr-blind | Generic strategy; tool still applies the identical D/tau pair filter |
| mr-flatfacts | D/tau/rho/spec without visible concept-family label |
| placebo-strategy | Covered facts; same requests and pair filter |
| toolinput | Original frozen witnesses as strategy seeds |
| new-toolinput | New MR witness pairs as strategy seeds |
| witness-only | Original witnesses; zero generation requests |
| new-witness-only | MR witness pairs; zero generation requests, proposal cost separate |

Primary exploratory contrast: mr-strategy vs mr-blind, common ref D_IO. This isolates relation guidance with fixed
cards/transform/filter; it does not compare MR oracle to ref oracle. Actual server tokens and request ledgers are
reported; no token-equality claim. Pure/runnable/finite-base-consistent relations can still be false positives.

Fixed 20 dev task IDs and K=1 match v14. [CPU evidence](CPU_VALIDATION.md), [changelog](CHANGELOG.md),
[research](../../research/relations_2026-10-14/REPORT.md). The GPU smoke is complete with zero accepted relation
cards; [the tracked result](../../analysis/v14_v15_gpu_smoke.md) documents the format failure and fallback controls.

```bash
# CPU only, from repository root:
CoverUp_concept/.venv/bin/python -B -m trickcatcher_linefacts.pipelines.v15_mrconcept.experiment prepare --workers 2
# Once QWEN_BASE_URL is privately exported:
bash trickcatcher_linefacts/pipelines/v15_mrconcept/run_experiment.sh
```

Output is this folder's `out/humaneval/experiment_smoke/`. Stages: prepare → propose → generate → oracle → score.
No paid router/API or held-out dataset is used. Same-config repeats resume from complete proposal/sample/response
caches. Code/config changes require a fresh output and protocol amendment. Source hashes and exact tasks are frozen.

The `eval.jsonl` adapter collects placeholder inputs, not executed own assertions; it explicitly says `not-scored`.
Interpret only common-ref metrics from `report.json`/REPORT.md and actual executions under `oracle/exec/`. Separate
property diagnostics count candidate/confirmed finite-input reports, false alarms and abstentions; universal validity
and generalization remain untested. Never feed canonical property-score outputs back into candidate selection.
