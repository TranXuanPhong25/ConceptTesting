# LLM Test Generation via Iterative Hybrid Program Analysis

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: A.

Paper/record: [LLM Test Generation via Iterative Hybrid Program Analysis](https://arxiv.org/abs/2503.13580)

Year/venue: 2026 ICSE; preprint 2025

Dataset: Defects4J; 130 complex classes

Input setting: current project source + CFG paths + coverage

Model: Llama 3.3 70B, Mistral Large 2, GPT-4o-mini, Claude 3.5 Haiku

Artifact: https://github.com/PANTA-TestAutomation/Panta

License: No software license verified

Concept hook (research judgment): Thay path guidance bằng obligation/behavioral abstraction; có basic/cov ablations.

Limitation: Primary objective là coverage/mutation. Phải kiểm tra version và failure filtering trước khi dùng làm baseline cho bug detection từ buggy input.

Local reproduction: **not performed**. No author source modified.


### Full-text/source audit 2026-10-15T08:20:10.332644+07:00

Promote as public artifact baseline for path-guided coverage research with exact model IDs. Keep separate from core bug-revealing Defects4J papers; historical-bug adaptation would require a new evaluation.

Models: Primary: bedrock/us.meta.llama3-3-70b-instruct-v1:0; bedrock/mistral.mistral-large-2407-v1:0; gpt-4o-mini-2024-07-18; claude-3-5-haiku-20241022; Author invocation max_tokens4096 temperature0.2 for paper models

Blockers: No local author evaluator or model execution; AWS Bedrock credentials/region access or closed-model API required for identical author route; Full benchmark averages53minutes/class, roughly115hours sequential for130classes; paper only one run/class; No standard historical-bug detection evaluation; fixed-code validation removes runtime/assertion failures; Comex paths are structural approximations, no solver proves path feasibility or intended semantic oracle; README result-html-parse.py differs from distributed result-html-parser.py; exact class manifest and summary script paths require reconciliation

[Paper](https://arxiv.org/html/2503.13580v2); [author source](https://github.com/PANTA-TestAutomation/Panta/tree/e8e0c679263b27b9e5bf590110827f4beadc52ce). No model/evaluator run.
