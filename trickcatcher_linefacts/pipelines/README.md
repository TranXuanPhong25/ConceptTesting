Latest: [v18_modelselect](v18_modelselect/README.md), completed selection-only pilot (no MCTS).
Retained/menu sampled consistency12/20; LLM11 vs rule12 vs uniform expected9.17. Tool evidence
has119 canonical-confirmed input discrepancies across12 tasks; no generation/D_IO comparison.
[Full report](../analysis/v18_modelselect_results.md). Earlier checkpoints below are historical.

Latest (2026-10-15): [v17_templates](v17_templates/README.md), CPU 44 tests / representation
17/20, but concept gate **2/20**, threshold 10: generation stopped, D_IO unmeasured.
Separate synthetic interface probe: model selection 6/6; parameter construction + schema +
example correctness 1/6. [Full results](../analysis/v17_template_results.md). Historical notes below.

GPU checkpoint (2026-10-15): v16_behavior_ready proposal gate **0/20**, threshold 10/20;
40 new requests, 0 generation rows, D_IO unmeasured. See
[proposal report](../analysis/v16_behavior_gate_results.md). Earlier CPU-ready notes below are historical.

Current runnable copy: [v16_behavior_ready](v16_behavior_ready/README.md), format-hardened
before model outputs. Fresh CPU gate 17/20, 29 tests pass; 0 model calls, awaiting live Qwen.

Current behavioral MVP (2026-10-15): [v16_behavior_compact](v16_behavior_compact/README.md),
CPU representation gate 17/20, 26 tests pass; model stages await live user Qwen. Original
[v16_behavior](v16_behavior/README.md) is preserved after oversized trace IPC failure.

# Frozen experiment pipelines

New isolated trials (2026-10-14): [v14_obgraph](v14_obgraph/README.md), grounded obligation paths, and
[v15_mrconcept](v15_mrconcept/README.md), conditional metamorphic concepts. Both use a dedicated `experiment.py`
runner, fixed 20 dev tasks/K=1, and have passed CPU validation; online runs await Qwen availability.
Their controls use fixed strategy slots rather than the legacy hybrid schedule. See the local
[version tree and status](EXPERIMENTS-2026-10-14.md).

v7 is B5 precondition mining and v4c Hypothesis domain strategies, followed by v6 code facts (the original fact extractor with mined validity), then specification input-class facts only for tasks without code facts. The hybrid bundle runs seven arms at K=3: plain, concept, toolinput, gen-plain, concept-hybrid, placebo-hybrid, and plain-hybrid. Evaluation uses v4 scoring; oracle scoring uses B1, reference programs, postconditions, and the mutant judge. The run of record is `out/gen2_qwen7b_v7hyb_v4_r2` with `out/oracle_v7hyb`. The optional strict construction keeps only the selected Hypothesis inputs in round 2, as in v8-strict.

Stages, in order:

1. `mine`: B5 preconditions and v4c domain strategies.
2. `facts`: v6 code facts, `facts.py --validity mined --precond-dir ...`.
3. `specfacts`: CPU input-class facts for tasks without code facts.
4. `bundle`: standard and v4-compatible hybrid task bundles.
5. `arms`: seven arms, K=3 by default.
6. `evaluate`: v4 assertion, validity, coverage and input scoring.
7. `oracle-collect`: collect distinct calls.
8. `oracle-llm`: B1, reference and postcondition responses.
9. `oracle-score`: execute oracle programs, replay/ask judges, and write the report.
10. `strict` (optional): CPU construction of round 1 plus selected round-2 inputs.
11. `report`: evaluation metrics; the oracle report is written by `oracle-score`.

From the repository root:

```bash
python -B -m trickcatcher_linefacts.pipelines.v7.run mine --reuse-from trickcatcher_linefacts/out
python -B -m trickcatcher_linefacts.pipelines.v7.run facts
python -B -m trickcatcher_linefacts.pipelines.v7.run specfacts
python -B -m trickcatcher_linefacts.pipelines.v7.run bundle
python -B -m trickcatcher_linefacts.pipelines.v7.run arms
python -B -m trickcatcher_linefacts.pipelines.v7.run evaluate
python -B -m trickcatcher_linefacts.pipelines.v7.run oracle-collect
python -B -m trickcatcher_linefacts.pipelines.v7.run oracle-llm
python -B -m trickcatcher_linefacts.pipelines.v7.run oracle-score
python -B -m trickcatcher_linefacts.pipelines.v7.run strict
python -B -m trickcatcher_linefacts.pipelines.v7.run report
```

`config.json` pins VERSION, dataset files, model, seeds, K, workers, and V4_PYTHON. `--python`, `--workers`, and `--k` override runtime settings. Use the dedicated interpreter with Hypothesis 6.169.0, mutmut 3.8.0, coverage 7.16.2 and libcst 1.9.0. Worker scripts resolve within the copied package, including when launched with `-I`. Frozen templates, task selection and a PREREG snapshot live inside that package; dataset files and installed Python dependencies remain external read-only inputs.

All experiment outputs are under `trickcatcher_linefacts/out/pipelines/<VERSION>/<dataset>/`. `humaneval` uses the original HumanEval/PUT/EvalPlus paths. Normalized MBPP+ roots from `heldout/dataset.py` are accepted directly:

```bash
python -B -m trickcatcher_linefacts.pipelines.v7.run mine --dataset trickcatcher_linefacts/out/heldout_mbpp_real12/he
```

Pass the same `--dataset` to every stage. Held-out output names include the root name and a short path digest to avoid collisions between different roots. Their task IDs and split come from their own `tasks.json`; HumanEval design exclusions never apply to MBPP+. No held-out preparation or source files are modified.

The default is offline replay: a missing response raises `CacheMiss`. No endpoint or credentials are read by the offline client. `mine`, `arms`, `oracle-llm`, and judges in `oracle-score` need the GPU endpoint only on uncached requests; explicit `--online` enables the original copied transport. All other stages are CPU-only. The equivalence suite is always offline, blocks parent network connections, and launches generated-code workers in network namespaces.

`--reuse-from` is repeatable. It accepts the original `out/`, a packaged dataset output directory, an original generation/oracle directory, or a component directory (`precond_qwen7b_v4`, `strategy_qwen7b_v4c`, `facts_v6`, `spec_facts_v7`). It copies response caches and mined data/facts, preserving sources; it never adopts old generation results or source manifests. Different existing destination files cause a collision error. Reused mining is checked against the current specification, PUT, base tests, model and mining seed, and fact validators must match. Reusing generation caches avoids GPU calls while recomputing sandbox work. Validate reused facts after changing a method; reuse is intended for unchanged stages.

From `trickcatcher_linefacts/`, to try something new: `cp -r pipelines/v7 pipelines/<new>`, set VERSION in config.json, register in PREREG.md, edit only the copy. Run that copy with `python -m trickcatcher_linefacts.pipelines.<new>.run`. The copy's local PREREG snapshot records its method; follow repository registration rules for the central PREREG when authorized. Original top-level modules and historical results remain frozen.

CPU equivalence checks:

```bash
PYTHONDONTWRITEBYTECODE=1 python -B -m trickcatcher_linefacts.pipelines.v7.test_equivalence --checks a,b,c
```

The suite writes `out/pipelines/<VERSION>/humaneval/equivalence/equivalence.json`. Check a rebuilds both bundles from mined artifacts and facts. Check b recreates the first actual request for every task/arm/sample (including shared plain/concept round-1 requests, generator requests and the toolinput oracle), checks its full cache hash and recorded first-call key, and replays all seven arms for tasks 0, 4 and 16 at K=1. Check c re-evaluates all generation rows, regenerates B1/ref/post responses from cache, recomputes every oracle execution task and cached judge request, then compares the oracle report. Two toolinput samples in the run of record (task 63, samples 1 and 2) timed out in the classifier; first-request verification replays those recorded errors through the copied fallback and separately reports that fresh classification succeeds. `--checks a`, `--checks b`, or `--checks c` run stages separately. Saved evaluation/oracle worker results are never seeded by this suite. A fresh `--output-name` forces fresh sandbox work. `--resume` may reuse CPU evaluation/execution results already produced by this suite, while still comparing every row and rebuilding the report; it never seeds those results from historical outputs.

Copied module mapping (all import dependencies are package-relative):

| Copied module | Original |
| --- | --- |
| `v7/evaluate.py` | `trickcatcher_linefacts/evaluate.py` |
| `v7/facts.py` | `trickcatcher_linefacts/facts.py` |
| `v7/fuzz_validity.py` | `trickcatcher_linefacts/fuzz_validity.py` |
| `v7/gen_evaluation.py` | `trickcatcher_linefacts/gen_evaluation.py` |
| `v7/gen_inputs.py` | `trickcatcher_linefacts/gen_inputs.py` |
| `v7/gen_prompts.py` | `trickcatcher_linefacts/gen_prompts.py` |
| `v7/generate.py` | `trickcatcher_linefacts/generate.py` |
| `v7/generator_worker.py` | `trickcatcher_linefacts/generator_worker.py` |
| `v7/llm_client.py` | `trickcatcher_linefacts/llm_client.py` |
| `v7/offline.py` | `trickcatcher_linefacts/offline.py` |
| `v7/offline_metrics_v3m.py` | `trickcatcher_linefacts/offline_metrics_v3m.py` |
| `v7/oracle_b01.py` | `trickcatcher_linefacts/oracle_b01.py` |
| `v7/precond_prompts.py` | `trickcatcher_linefacts/precond_prompts.py` |
| `v7/preconditions.py` | `trickcatcher_linefacts/preconditions.py` |
| `v7/prompts.py` | `trickcatcher_linefacts/prompts.py` |
| `v7/run_gen.py` | `trickcatcher_linefacts/run_gen.py` |
| `v7/run_v4.py` | `trickcatcher_linefacts/run_v4.py` |
| `v7/run_v6.py` | `trickcatcher_linefacts/run_v6.py` |
| `v7/spec_facts.py` | `trickcatcher_linefacts/spec_facts.py` |
| `v7/tracer.py` | `trickcatcher_linefacts/tracer.py` |
| `v7/v4_evaluation.py` | `trickcatcher_linefacts/v4_evaluation.py` |
| `v7/v4_facts.py` | `trickcatcher_linefacts/v4_facts.py` |
| `v7/v4_offline.py` | `trickcatcher_linefacts/v4_offline.py` |
| `v7/v4_prompts.py` | `trickcatcher_linefacts/v4_prompts.py` |
| `v7/v4_runtime.py` | `trickcatcher_linefacts/v4_runtime.py` |
| `v7/v4_strategies.py` | `trickcatcher_linefacts/v4_strategies.py` |
| `v7/v4_tools.py` | `trickcatcher_linefacts/v4_tools.py` |
| `v7/v4_worker.py` | `trickcatcher_linefacts/v4_worker.py` |
| `v7/v8_strict_est.py` | `trickcatcher_linefacts/v8_strict_est.py` |

Added orchestration/support modules: `run.py`, `paths.py`, `offline_client.py`, `hypothesis_replay.py`, `freeze_constants.py`, `explain_differences.py`, `test_equivalence.py`, and package `__init__.py` files. `config.json` is new configuration; `selection.json` retains only task IDs/splits and cohort metadata from `out/tasks_v3m2_all.json`. `tasks.txt`, `PREREG.md`, and all six `tc_templates/` files are frozen copies of their top-level counterparts. `module_map.json` contains the machine-readable mapping above. The historical Gemini route in `generate.run` is replaced by a pointer to the unified runner because it is unused by v7 and would import external pipeline clients.

Hypothesis replay pins the original worker’s local literal pool in `hypothesis_constants.json`, restored by `hypothesis_replay.py`. Hypothesis 6.169.0 otherwise mines literals from the refactored source and changes seeded string draws. This resource was checked against the recorded worker’s `.hypothesis/constants` snapshots. Set `freeze_hypothesis_constants` to false only in a new version when intentionally changing this behavior.

`B0_VARIANTS` configures the optional released GPT-3.5 baseline programs required to reproduce the historical report’s dpp/tc columns. These are read-only inputs; held-out datasets do not use HumanEval baseline variants. The main v7 reference/judge/full oracles use the version-scoped response cache.

Measured equivalence results and every known difference are documented in [v7/EQUIVALENCE.md](v7/EQUIVALENCE.md). The strict comparison reports environment-dependent differences in c; `python -B -m trickcatcher_linefacts.pipelines.v7.explain_differences` verifies the copied scorer exactly reproduces the report on identical observations and attributes all changes in the fresh report.
