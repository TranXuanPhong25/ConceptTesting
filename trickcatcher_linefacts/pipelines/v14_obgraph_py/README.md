# v14_obgraph_py: Python/JSON format repair

Separate copy of [v14_obgraph](../v14_obgraph/README.md), preserving its method, controls, validator and scope.
The original smoke had zero accepted cards. This copy supplies an explicit Python/JSON example and stops before
full generation when the proposal-stage gate remains empty. A surviving card is not proof of semantic validity.

User order: B3 → B4 → v14_obgraph_py. Model stages are queued after both old runs. No paid API or held-out run.

```bash
CoverUp_concept/.venv/bin/python -B -m trickcatcher_linefacts.pipelines.v14_obgraph_py.experiment prepare --workers 2
bash trickcatcher_linefacts/pipelines/v14_obgraph_py/run_experiment.sh
```

Output is local out/humaneval/experiment_smoke/. mechanism_gate.json records whether generation was enabled.
Only raw response cache files for identical requests may be copied from the parent; proposals/samples/results stay
fresh. Original 20 dev tasks/K=1 and three-slot budgets are unchanged. Report accepted-card coverage before claiming
that graph/MR treatments were exercised. Source changes require fresh outputs; see root PREREG and CHANGELOG.md.
