# SWE-Tester: Training Open-Source LLMs for Issue Reproduction in Real-World Repositories

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: C.

Paper/record: [SWE-Tester: Training Open-Source LLMs for Issue Reproduction in Real-World Repositories](https://arxiv.org/abs/2601.13713)

Year/venue: 2026 arXiv

Dataset: SWT-Bench Verified; 41K training instances

Input setting: issue + localization + search/replace test editing

Model: Fine-tuned Qwen2.5-Coder 7B/14B/32B, Llama3.1-8B, Gemma3-12B

Artifact: https://huggingface.co/datasets/adityasoni17/SWE-Tester

License: Dataset/weight license not verified

Concept hook (research judgment): Same-model evaluation hấp dẫn nếu tác giả release exact SFT checkpoints.

Limitation: Đã xác minh dataset public; chưa xác minh released model weights hoặc inference scaffold. Base Qwen2.5-Coder-7B của mình không tương đương SFT checkpoint.

Local reproduction: **not performed**. No author source modified.

## Full-text audit 2026-10-15 08:15

See [review ledger](../../audit/reviews/025.json). Source status: public_implementation; reproduction feasibility: conditional. No local model reproduction.
