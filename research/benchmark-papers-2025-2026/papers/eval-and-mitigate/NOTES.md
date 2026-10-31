# Evaluating and Mitigating the Misguidance Effect of Buggy Code in LLM-Generated Unit Tests

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: A.

Paper/record: [Evaluating and Mitigating the Misguidance Effect of Buggy Code in LLM-Generated Unit Tests](https://arxiv.org/abs/2607.22883)

Year/venue: 2026 ISSTA

Dataset: Defects4J v3.0; 318 methods / 233 defects

Input setting: buggy code or specification inferred from buggy code

Model: Gemini 2.5 Flash/Pro, GPT-4.1, DeepSeek-V3/R1, Qwen3-Coder-Plus and others; 11 models / 13 configurations

Artifact: https://github.com/drixs2050/EvalAndMitigate

License: MIT + third-party notices

Concept hook (research judgment): Tách behavioral obligation khỏi implementation để giảm misguided assertions.

Limitation: Notebook pipeline; API cells default to GPT-4.1. Closed-model names in paper do not establish immutable snapshot availability. Plus API endpoints are not interchangeable with arbitrary local Qwen weights.

Local reproduction: **not performed**. No author source modified.

## Full-text audit 2026-10-15

[Verified source/model review](../../audit/reviews/001.json). Default docstring/test APIs differ; configure actual models, not filename labels. No local paper reproduction.
