# Agent-Based Test Assertion Generation via Diverse Perspective Aggregation

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: A.

Paper/record: [Agent-Based Test Assertion Generation via Diverse Perspective Aggregation](https://arxiv.org/abs/2608.05822)

Year/venue: 2026 arXiv

Dataset: Defects4J

Input setting: focal method + test prefix; actual-value construction

Model: DeepSeek-Coder-7B-Instruct (paper label); exact served checkpoint needs config audit

Artifact: https://github.com/LeonYang95/AssertMate

License: Apache-2.0

Concept hook (research judgment): Concept có thể hướng expected-value reasoning và assertion targets; có agent ablations.

Limitation: Chỉ sinh assertions, không phải toàn bộ test. Probability reranking cần kiểm tra logprob support; chưa chạy local inference.

Local reproduction: **not performed**. No author source modified.


### Full-text/source audit 2026-10-15T08:22:01.651017+07:00

Promote oracle-specific candidate, but downgrade claim of immediately runnable exact small-model reproduction. Best pilot requires authors exact model/config/pipeline reconciliation; do not reimplement silently.

Blockers: No local author code/model reproduction performed; Documented entrypoint requires missing config/basic_config.yaml; example schema llm differs from wrapper config.deepseek and lacks eos/response_header; DeepSeek wrapper references self.tokenizer without initializing it; exact vLLM serving/tokenizer setup absent; Documented first_round_speak_up.py defaults debug=True and single-response prefix=False path, not full5sample paper pipeline; Oversampling wrapper default10,completion max_tokens1024 versus paper5/4000; confidence computes exp(mean(logprob)) rather than arithmetic mean token probability illustrated in paper; Public data preparation uses fixed focal code and derives actual values/function categories from target assertions in some routes; reconcile exact final ActVCon experiment path before asserting no oracle assistance; Top-level requirements omit numpy/transformers/vLLM even though wrapper/runtime need them; Paper mutation experiment omits PR/BDR; killed mutant count alone does not establish false-positive-controlled oracle correctness

[Paper](https://arxiv.org/html/2608.05822v1); [source](https://github.com/LeonYang95/AssertMate/tree/3ca2a7e8d3390c6a1d7a3277a6f284bb55b02376). No author model/code run.
