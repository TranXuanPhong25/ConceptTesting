# CPU validation — v14_obgraph

2026-10-14. Engineering validation only; no model-effectiveness experiment.
User reports exhausted quota and no Qwen endpoint. No model proposal/generation or held-out run.

| Check | Result |
|---|---:|
| tasks | 20 |
| base_ok | 20 |
| nodes | 193 |
| edges | 428 |
| concepts | 395 |
| clauses | 70 |
| tasks_with_return_edges | 19 |
| protected_source_files_checked | 222 |
| protected_source_changes | 0 |
| tests_in_this_copy | 14 |
| tests_combined | 28 |
| model_requests | 0 |
| heldout_runs | 0 |

Edge types: {"CONTROL": 198, "DATA": 226}.

The 20 task IDs are frozen in config.json. Graph extraction used cached v11 task/mining data,
base traces and selected old fuzz witnesses. These counts measure available structure, not useful
obligations, validated semantic relations, or detected bugs.

14 tests per isolated copy (28 combined) passed: schema/purity/path adversaries, runtime path and
trigger separation, finite base consistency, MR pairing/multiset/identity checks, preservation of
relations failing on an untested buggy PUT, canonical false-alarm separation, and real Hypothesis
draw/driver resume/call/pair budgets. Fixed transport fixtures are scheduler tests, not model results.

Common-ref adapter check: original HumanEval/27 witnesses (2 calls), 10 cached v11 spec-only ref
responses, 2 calls executed/scored in each copied package, no new model calls. This is compatibility
evidence only. Generated-method arms have not been evaluated.

Protected v7/v11/v12/v13 direct source/config/document hashes were unchanged after CPU checks.
Raw CPU artifacts are under this copy's out/humaneval/; tracked summary is CPU_VALIDATION.json.

Reproduce:

```bash
CoverUp_concept/.venv/bin/python -B -m unittest trickcatcher_linefacts.pipelines.v14_obgraph.test_experiment trickcatcher_linefacts.pipelines.v15_mrconcept.test_experiment -q
CoverUp_concept/.venv/bin/python -B -m trickcatcher_linefacts.pipelines.v14_obgraph.experiment prepare --workers 2
```
