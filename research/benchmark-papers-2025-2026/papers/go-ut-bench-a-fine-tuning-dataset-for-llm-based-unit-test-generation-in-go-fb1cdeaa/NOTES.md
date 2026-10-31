# Go-UT-Bench: A Fine-Tuning Dataset for LLM-Based Unit Test Generation in Go

Reviewed 2026-10-15. Full arXiv v2 read (6,299 words, SHA-256 `19df08798d7a40390497b983758c468fcb0e5d3c49a5e1996dca004c88c2eca5`).

The authors publish 5,264 {Go source, unit-test} pairs across 10 permissively licensed repositories, with commit hashes and a 3,684/790/790 train/test/validation split. They fine-tune DeepSeek-Coder-V2-Lite-Instruct with LoRA and Llama-3.2-3B-Instruct fully, then use GPT-4o-mini as the only pairwise judge. Reported fine-tuned win rates are 81.9% and 76.7%. The paper explicitly admits the evaluation has no human triangulation, no compile/run/coverage validation, only one metric, and no significance testing.

The public HF dataset is ungated and 175 MB, but its dataset card/API has no license declaration. The authors state underlying repos are permissively licensed and include commit provenance; check per-repo terms before redistribution. No training/generation/evaluation code or fine-tuned weights were found. The method is Go code-to-test adaptation, not issue-conditioned F2P, Defects4J, BugsInPy or SWT-Bench; SWT-Bench is only related work.

**Use:** a secondary Go fine-tuning data lead, not a reliable test-quality/bug-detection benchmark. The reported judge alignment does not establish that tests compile or reveal bugs. No dataset/model run.

Structured review: [`audit/reviews/081.json`](../../audit/reviews/081.json); artifact notes: [`public_evidence/source_audit.md`](public_evidence/source_audit.md).
