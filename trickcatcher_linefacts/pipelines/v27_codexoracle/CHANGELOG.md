# CHANGELOG v27_codexoracle

Parent: `pipelines/v26_proporacle` (PARENT.json). Question: model vs prompt as the cause of the v26 oracle failure.

## 2026-10-18 — Codex client + strict prompt variant

- New: `codex_client.py` (codex exec, empty read-only cwd, cached prompt-digest slots), `oracle_run.STRICT` +
  `instruction()`, CLI `--model qwen|codex --variant original|strict`, output root `oracle/<model>_<variant>/<cohort>`.
- `config.json`: VERSION, `codex` block, `oracle.variants`. Tests 30/30 pass.
- PREREG: "v27_codexoracle preregistration" appended before registered outputs.
- Results: `analysis/v27_codexoracle_results.md`. Model effect large (Codex ≫ Qwen at same prompt); strict prompt
  makes Codex property oracle precision 1.00 (0 FA, 0 unsound checks) on pilot20 but does not help Qwen.
