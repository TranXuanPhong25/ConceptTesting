# SWE-Doctor source audit

Checked 2026-10-15. Paper: [arXiv:2607.00990 v1](https://arxiv.org/abs/2607.00990).

- The paper's Data Availability reference [10] links <https://github.com/SWE-Doctor/SWE-Doctor>.
- Checked official repo HEAD / only commit `90ed1d949cae8345b6571394454dd59ec12dc7b2` (2026-10-02), with MIT LICENSE. The repo includes BRT generation, runtime-debugger diagnosis (PDB and Delve), patch generation, benchmark evaluation wrappers, README and pipeline scripts.
- README documents four stages and dataset/model setup; static inspection covered `reproduction_test_agent/run_batch_verified.py`, `debug_agent/run_debug.py`, `repair_agent/run_repair_verified.py`, `repair_config_verified.yaml`, `run_verified_test/run_rca_verified.py`, `run_verified_test/run_repro_trace_verified.py`, `swebench_verified_eval/run_eval_verified.py`, `pipeline_run/run_pipeline_verified.sh`, and `pyproject.toml`.
- Scripts load standard SWE-bench datasets and require an explicit issue-ID list. No paper-specific 436/107/50 issue ID lists or raw result/trajectory cache are in the current tree. The code repo README describes itself as a research artifact for an FSE 2027 submission; its only commit postdates the July 2026 arXiv paper and includes additional Go implementation. Exact paper-version equivalence should be confirmed before claiming a faithful rerun.
- Model calls use LiteLLM and model names are configurable via CLI/config; a local OpenAI-compatible Qwen endpoint appears possible with endpoint configuration, but this was not tested. The paper tests GPT-5.4, GPT-5.4-mini, Claude Sonnet 4.6, DeepSeek-V4-Pro, and MiMo-V2.5-Pro.
- The diagnosis schema captures suspected location, symptom, propagation, patch impact, fix direction and runtime evidence. Paper evaluates final patch resolution; it does not measure diagnosis accuracy against ground-truth root-cause labels.
- No source execution, Docker build, benchmark run, or model/API call. Full verdict: `../../../../audit/reviews/092.json`.
