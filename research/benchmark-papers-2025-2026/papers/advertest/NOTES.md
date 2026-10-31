# Test vs Mutant: Adversarial LLM Agents for Robust Unit Test Generation

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: A.

Paper/record: [Test vs Mutant: Adversarial LLM Agents for Robust Unit Test Generation](https://arxiv.org/abs/2602.08146)

Year/venue: 2026 ISSTA

Dataset: Defects4J; later paper also has Python SWE-bench study

Input setting: fixed/current source; mutants provide iterative feedback

Model: DeepSeek-V3.2 in paper; repository uses deepseek-chat/OpenAI-compatible wrappers

Artifact: https://github.com/jmueducn/AdverTest

License: No software license verified

Concept hook (research judgment): Bug-mechanism concepts có thể thay generic survivor feedback.

Limitation: Generation on fixed versions trong artifact; không cùng setting buggy-input detection. CPU mutation loops và legacy Defects4J dependencies đáng kể; model alias needs pinning.

Local reproduction: **not performed**. No author source modified.


### Full-text/source audit 2026-10-15T08:23:17.584672+07:00

Keep as close mutation-guided prior work and conditional reference-version base. Downgrade exact reproduction readiness until algorithm/evaluator/data discrepancies are reconciled; do not silently patch author source.

Blockers: No local model/code run; README/paper fixed five T-M-T-M-T actions differs from generate.py: MS threshold70 chooses each action,4actions plus conditional finalTC; Python evaluator uses buggy_set != fixed_set plus timeout/collection-error branches, rather than paper nonempty buggy_set minus fixed_set; can count failing-set shrinkage without any new failure; Java evaluator compares failure counts/raw stdout and execution status, not explicit failing-test-set subtraction; Python input contexts/data files referenced but python_eval/data has no tracked blobs; no verified200bug sample manifest; Python temperature default0.7 differs from paper0; Reference generation includes fix-introduced code; paper explicitly acknowledges this can recreate historical defect and expose unavailable clues in buggy-input setting; No project license and no immutable API/model configuration

[Paper](https://arxiv.org/html/2602.08146v3); [source](https://github.com/jmueducn/AdverTest/tree/ef64ea33a9997796b459a3279b5bc72b7a375c17). Static source audit only.
