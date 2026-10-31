# TDD-Bench-Java / Java issue-reproduction source audit

Checked 2026-10-15 against the paper's linked [IBM/TDD-Bench-Verified](https://github.com/IBM/TDD-Bench-Verified) repository.

- Pinned source inspected: commit `3df8be066e486789d0b8e0d2865a3a4422b4560f` (2026-07-21); repository declares Apache-2.0.
- The paper's data availability statement says the benchmark is open source but the reproduction-test generator code is proprietary. This is not a public e-Otter++ reproduction package.
- The `TDD-Bench-Java` folder contains `java.csv` (4,575,886 bytes), `id_list.txt` (250 lines), `tdd_java.diff`, `setup.sh`, `command_run_gold.sh` (250 commands), and a README with a test-patch prediction schema and evaluation invocation.
- Parsed the public CSV read-only: 250 rows, 250 unique IDs, all 250 match `id_list.txt`; 250/250 have nonempty issue text, base commit, code patch, test patch, test command and Dockerfile fields; 13 repositories.
- The Java setup script clones `amazon-science/SWE-PolyBench`, checks out commit `1963184`, applies the public `tdd_java.diff`, then installs the evaluator. The Java README invokes `src/poly_bench_evaluation/run_evaluation.py` on model prediction JSON. The parent repository also contains the Docker-based `tddbench` evaluator.
- Statically inspected repository README, Java README, setup script, evaluation/grading modules, CSV fields and cohort IDs. No benchmark task was built/run and no authors' generation code was modified.
- Article: [arXiv:2605.04320 v2](https://arxiv.org/abs/2605.04320), 7 May 2026, CC BY 4.0. It reports Claude-Sonnet-4.5/GPT-5.2 results, but exact generator APIs/revisions are not pinned.
- Full verdict: `../../../../audit/reviews/098.json`.
