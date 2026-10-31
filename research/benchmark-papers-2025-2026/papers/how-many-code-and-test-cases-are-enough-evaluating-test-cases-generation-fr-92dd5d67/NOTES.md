# How Many Code and Test Cases Are Enough? Evaluating Test Cases Generation from a Binary-Matrix Perspective

Reviewed 2026-10-15. Read full 24-page arXiv v3 and appendices (16,339 words). Public author evaluator and Hugging Face dataset verified. No execution or model calls.

## Model fit

This is the strongest own-model evaluation paper found so far for general test-case generation: authors include the exact Qwen2.5-Coder-7B-Instruct model used in the project. On TC-Bench, Qwen-Coder-7B + LCB reports 42.17% HackRate (41.94% PassRate); + HT 21.92% HackRate despite 71.02% PassRate. Dataset includes 877 algorithmic programming problems with correct and diverse wrong C++ submissions; an evaluator measures whether generated input/output pairs distinguish them.

This remains complementary rather than mainline thesis evidence. It is competitive-programming C++, not Java/Python repository repair, issue reproduction, or Defects4J/BugsInPy/SWT-Bench. It has no root-cause labels, though Appendix C manually discusses examples of error patterns.

## Artifact and reproduction

Official author repo: [Luowaterbi/TC-Bench](https://github.com/Luowaterbi/TC-Bench), commit `89883430c3503f206def8c5f92d6b55774ba0472`; archive SHA-256 `2682a8892993923fa3113e1607b99886e9ab14df519131803c0651ee2247c645`. Hugging Face dataset: [Luoberta/TC-Bench](https://huggingface.co/datasets/Luoberta/TC-Bench), API revision `f4d482da2d015b6342a12b9891149dcb00566c92`, 877-row test split, MIT card. Repo README gives required JSONL input/output format and commands for correct-code filtering, wrong-code evaluation, and rank-scaled metrics. It has no end-to-end LLM generator implementation; this can still evaluate a local model’s generated tests by supplying the expected JSONL format. Public model generations are not needed for a custom evaluation.

Exact paper reproduction is conditional: GPT/Claude APIs and method snapshots/prompts are not pinned; repo has no software license, `solve.py` uses an author-specific absolute path, and source dataset must be loaded from HF. Do not conflate with issue-level root-cause study.

The paper’s “matrix rank as test-count upper bound” formulation and claims should be independently scrutinized; no mathematical replication was done. Full text SHA-256 `a1a67164a29ef97071d180ef6d1e142eb8eb05e6a7d2d6e53dbb006772b03219`.
