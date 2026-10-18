# CHANGELOG v28_codexflow

Parent: `pipelines/v27_codexoracle` (PARENT.json).

## 2026-10-18 — Codex without tools; full pipeline with Codex

- `codex_client.py`: disables shell/code-mode/browser/computer-use/apps; records `tool_executions` per response.
- `flow_run.py`: `--model qwen|codex`; Codex output under `flowrun/codex/<cohort>`.
- `config.json`: VERSION, `codex.disable_features`. Tests 30/30.
- PREREG: "v28_codexflow preregistration". Results: `analysis/v28_codexflow_results.md` (all arms 16–17/20 with Codex, no concept gain; oracle conclusion holds without tools).

### Operational note (2026-10-18, before freeze/score of the Codex flowrun)
One call (pilot20 task 77, placebo+input, round 2) timed out 3× (300 s each); the runner raised instead of
recording the failure, so the run did not freeze (199/200 arm jobs done). Resumed with a scratch wrapper that
applies the registered rule (exhausted call = arm error with 0 tokens; the arm continues to its final call).
Pipeline sources and PREREG unchanged (protocol.json hashes them); this note lives here for that reason.
