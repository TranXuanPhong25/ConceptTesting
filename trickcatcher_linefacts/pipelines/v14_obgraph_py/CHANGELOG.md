# v14_obgraph_py CHANGELOG

2026-10-14. Parent: v14_obgraph, copied without out/ or bytecode. Status: CPU preparation; model run queued AFTER B3/B4.

- experiment_schema.py: Python/JSON FORMAT example, code-source strings and actual ID/parameter reminders; no target
  test inputs, gold outputs or semantic rule changes. Original schemas/grounding and all tool validation stay intact.
- experiment.py: proposal-stage mechanism gate; zero accepted cards stops generation rather than evaluating fallback.
- config.json: new VERSION, proposal guidance marker; same frozen 20 dev IDs/K=1, seeds, budgets and controls.
- Original failure and results remain in ../v14_obgraph/ and analysis/v14_v15_gpu_smoke.md.
- No protected pipeline/vendor edits. Explicit toy example teaches serialization only; no paper reproduction.

Run from repository root: bash trickcatcher_linefacts/pipelines/v14_obgraph_py/run_experiment.sh
Do not start model stages until B3/B4 are complete. Read root PREREG format-repair entry.
