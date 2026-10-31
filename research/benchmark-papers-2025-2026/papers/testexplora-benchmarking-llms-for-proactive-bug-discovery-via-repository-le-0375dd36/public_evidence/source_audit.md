# TestExplora public-source audit

Checked 2026-10-15. Paper: [arXiv:2602.10471](https://arxiv.org/abs/2602.10471).

- Author-linked repository: <https://github.com/microsoft/TestExplora>
- Checked commit: `11e6952261f58d3ceb9f4d2571e03aa35dad9523` (2026-03-11).
- GitHub API identifies the repository license as MIT; the tree includes `LICENSE`.
- README calls this the official implementation of the exact paper and documents `testexplora/harness/inference.py`, supported API/local vLLM model routes, and Docker evaluation.
- Statically inspected README, `requirements.txt`, inference, local vLLM caller, Docker evaluator, prompt preparation, data manager, and the repository tree. No source was executed or altered.
- Substantive files include `testexplora/build_benchmark/process_data.py`, `parse_repo.py`, `build_dependency_graph.py`, `harness/inference.py`, `harness/call_pipeline/call_vllm.py`, `harness/utils/eval_docker.py`, and prompt/evaluation helpers.
- The public tree does **not** contain the benchmark JSONs, raw test patches, or experiment output cache. README asks users to supply `--data_path` and gives no dataset download URL. `data_manager.py` with its default `subset=True` opens `/home/superbench/jiaxiang/my_tddbench/my_tdd_bench/pr_results/sweagent-gpt5mini_merged_passing_prs.json`; `lite=True` additionally expects `data_flitered4_test.json` alongside the supplied data.
- The paper evaluates Qwen3-Coder-30B-A3B, but `call_qwen_coder_30b` in the checked source configures `Qwen/Qwen2.5-Coder-32B-Instruct`. Verify whether this is stale code or a model mismatch before comparing results.
- No data/model calls or reproduction were run. Full verdict and limits: `../../../../audit/reviews/063.json`.
