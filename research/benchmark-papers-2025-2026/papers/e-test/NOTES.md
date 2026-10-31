# E-Test: E’er-Improving Test Suites

Reviewed: 2026-10-14. Evidence: primary_source_reviewed. Grade: B.

Paper/record: [E-Test: E’er-Improving Test Suites](https://arxiv.org/abs/2510.19860)

Year/venue: 2026 ICSE; preprint 2025

Dataset: Defects4J + 1,975 execution scenarios; RQ5 uses 673 bugs

Input setting: method/test suite + scenario; RQ5 scenarios from trigger tests

Model: Llama3 8B/70B, DeepSeek-R1 distills including 1.5B/7B, GPT family

Artifact: https://github.com/ketaiq/E-Test-package

License: Apache-2.0 reported in repository; release audit pending

Concept hook (research judgment): Concept = behavioral scenario chưa được existing tests kiểm tra.

Limitation: RQ5 được cấp scenarios tương ứng golden trigger tests; không được xem như tự tìm fault hypothesis. Repo needs packaging/config audit.

Local reproduction: **not performed**. No author source modified.


### Full-text/source audit 2026-10-15T08:31:21.692357+07:00

Good public scenario-classification/partition prior work with offline original-output route. Conditional as a base: public best model access and fixed-version false-alarm validation unresolved; keep separate from test-input generation.

Blockers: Fresh best-model inference depends on author-owned closed fine-tune or paid retraining; no access verified; RQ5 source explicitly tells model to change assertions to make test fail; current validity loop breaks when any failing test is found and does not itself demonstrate fixed-pass/buggy-fail correctness; Given failure-triggering candidate input;83.2%reportedfailure result not end-to-end unknown-bug discovery; Need-test/error-prone twins differ by fixed/buggy method; split by scenarios can correlate near-duplicates, no strongerheldoutprojectclaim verified; Ollama aliases/tokenizer mapping inconsistent:DeepSeeksizevariants mappedtofullDeepSeekR1 HF tokenizer;Llama3.2-3B mapsMeta-Llama3-8B; No author model call or notebook/evaluator run

Sources: https://arxiv.org/html/2510.19860v1, https://github.com/ketaiq/E-Test-package/tree/9bb95c1bf252a752f7ac8758e306d6f694a8a8dd
