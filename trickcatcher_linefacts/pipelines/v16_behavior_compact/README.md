# v16_behavior_compact

Own LineFacts MVP for abstract behavior and semantic concepts. This is not a paper reproduction.
Foundation copied from v11_fair; original preparation v16_behavior is preserved after an IPC size failure.
See [CPU_VALIDATION.md](CPU_VALIDATION.md), [CHANGELOG.md](CHANGELOG.md), and root PREREG.

Run this method through `behavior_experiment.py`; inherited `run.py` is foundation code, not the new treatment.

```bash
python3 -B -m trickcatcher_linefacts.pipelines.v16_behavior_compact.behavior_experiment prepare --workers 2
# After source scripts/research_env.sh and configuring a live user Qwen environment:
python3 -B -m trickcatcher_linefacts.pipelines.v16_behavior_compact.behavior_experiment all --online --workers 2
```

Stages: prepare → representation gate → spec-only proposal → binding/check → concept gate →
seven-arm generation → saved spec-only ref collection/scoring. No paid fallback. Sources/tasks/config
freeze before output; do not edit a frozen method and reuse outputs. Offline client consumes exact caches
only; CPU tests do not count as LLM results.

Artifacts under `out/humaneval/behavior_smoke/`: per-task source IR, pseudocode, observed FSM,
retained replay state snapshots, typed implementation mutations/witnesses, concept/rejection records,
generation prompts/request ledger, shared-ref report. Guards and mutable state stay source-mapped.
FSM is an observed finite projection, not a complete program model. Predicate DSL is JSON, not Python strings.

Primary: behavior+concept vs behavior. All six LLM arms use the same domain-only filter and random-valid
selection; semantic activation is measured after selection. Witness-only uses the same bounded common
old+mutant witness pool without model generation. D_IO is evaluated only after generation freezes.
Neither killing a model mutant nor passing a representation gate establishes detection improvement.
