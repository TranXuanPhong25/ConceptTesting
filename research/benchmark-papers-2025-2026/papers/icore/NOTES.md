# iCoRe: An Iterative Correlation-Aware Retriever for Bug Reproduction Test Generation

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: B.

Paper/record: [iCoRe: An Iterative Correlation-Aware Retriever for Bug Reproduction Test Generation](https://arxiv.org/abs/2604.19224)

Year/venue: 2026 FSE

Dataset: SWT-Bench + TDD-Bench

Input setting: correlations among source/test entities + issue

Model: GPT-4o and DeepSeek-V3 settings; exact configuration audit pending

Artifact: https://github.com/ZJU-CTAG/iCoRe

License: No software license verified

Concept hook (research judgment): Retrieval baseline cho cùng concept context; freeze retrieval khi so concept.

Limitation: Contribution mainly retrieval; multi-model encoder/index dependencies, không trực tiếp root-cause taxonomy.

Local reproduction: **not performed**. No author source modified.


## Full-text and public-source audit — 2026-10-15

Đã đọc toàn bộ arXiv v2 (13,873 words; §§1–10, RQ1–RQ5, failure analysis, threats, references và Appendix A/B prompts). iCoRe là retrieval contribution trên SWT-Bench Lite 276 + TDD-Bench Verified 449, không phải Defects4J/BugsInPy. Separate production/test retrieval, iterative sketch BRT, BM25 + weighted function-call-tree similarity, LLM reranking. GPT-4o, DeepSeek-V3 và Qwen3-32B; exact GPT snapshot trong paper/source, retrieval temp=0, generator temp=.7, 3 iterations, top-5 tests.

Repo công khai ở HEAD `4ef1b08a288e519ff5d5a44775b5be8d0afb5626`, có implementation, prompts, benchmark env, cached model-specific retrieval contexts và nhiều kết quả SWT Lite (276 predictions, ablations/baselines). Các GPT retrieval files có 663 issue IDs (union của benchmark tasks). Không tìm thấy final TDD 449 prediction artifact; TDD retrieval context có nhưng reported score chưa thể audit trực tiếp từ cached final outputs. AssertFlip baseline cache có 268/276 rows. `requirements.txt` unpinned, không có license riêng trong repo; CC BY-NC-ND là license paper.

Source inference chạy qua OpenAI-compatible API; GPT-4o 2024-08-06 pin trong mapping, DeepSeek/Qwen endpoint configurable, không có weights. Paper average cost $0.26 TDD / $0.28 SWT, khoảng $194.02 nếu chạy đủ 725 instances (tính theo số liệu paper, chưa chi). Không gọi API/chạy code. Verdict: public implementation, exact full reproduction conditional do API/cost, code license, thiếu TDD output và baseline coverage mismatch. Evidence `audit/reviews/024.json`, `public_evidence/source-audit.json`.
