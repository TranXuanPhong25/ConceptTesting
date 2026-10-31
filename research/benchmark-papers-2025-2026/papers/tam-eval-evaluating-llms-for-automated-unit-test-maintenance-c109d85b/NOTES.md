# TAM-Eval: Evaluating LLMs for Automated Unit Test Maintenance

Reviewed: 2026-10-14. Evidence: metadata_only_not_confirmed_suitable. Grade: U.

Paper/record: [TAM-Eval: Evaluating LLMs for Automated Unit Test Maintenance](http://arxiv.org/abs/2601.18241)

Year/venue: 2026 (discovery metadata; venue/year not primary-verified)

Dataset: Unknown: search hit does not prove experimental use

Input setting: Unknown; not checked

Model: Unknown; not checked

Artifact: Not verified

License: Unknown; not checked

Concept hook (research judgment): Not assessed

Limitation: Metadata-only candidate; may cite benchmark without using it; cannot claim reproducible.

Local reproduction: **not performed**. No author source modified.

Discovery record: https://openalex.org/W7125877429

Discovery query: SWT-Bench; keyword hit is not dataset-use verification.


## Full paper and source review — 2026-10-15 (#38)

Read full arXiv v1 (6,464 words). TAM-Eval defines 1,539 whole-test-file tasks over 192 Python/Java/Go repos: Create, Repair, Update. Metrics are pass rate, line coverage delta, and mutation coverage delta. Repair defects include syntax/execution faults, artificially weak assertions, and low-value coverage. Update uses a historical test-file commit paired with current focal code. This is broad test maintenance, not issue-linked buggy/fixed reproduction; Defects4J, BugsInPy and SWT-Bench are not task datasets.

Public Apache-2.0 code and benchmark TOMLs at `trndcenter/TAM-Eval` commit `8de039...`; mirror `Tech871/tameval` commit `269cf23...`. Static inspected pipeline, prompt, evaluator and API adapter. It can evaluate an OpenAI-compatible model through OpenRouter. Critical exact-reproduction issue: paper Table II models (GPT-5, GPT-OSS-120B, Gemini 2.5 Flash, etc.) differ from current public `run_model_evals.sh` (Qwen2.5 Coder, Gemma3, Qwen3-235B, o4-mini-high, DeepSeek R1); model snapshots are not pinned. The script plus README are public, but documented outputs/results directories were absent from visible package listing and no raw outputs were verified. Thus easy to adapt for our model, but exact published figures remain conditional. No code/model call.
