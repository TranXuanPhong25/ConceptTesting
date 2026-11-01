# Validation — 2026-10-30

Historical validation of the initial plain-only implementation. Current active
concept/reference run, real endpoint readiness and live lifecycle are documented
in `final/experiments/concept_reference_v1/validation/REPORT.md`; the no-model-call
statement below applies to the earlier initial validation, not the later run.

- Python 3.11.14, Linux bubblewrap sandbox: preflight PASS.
- Engineering checks: **17 passed** (`final/tests/test_pipeline.py`). Fixtures cover
  structural renames/import padding, sandbox privacy/timeouts, predicate validation,
  non-unique-output properties, prompt helpers, direct target calls, future imports,
  seeded base inputs, accurate incremental-failure counts, and checkpoint replay.
- Dataset provenance: all 164 JSON records match the original OpenAI HumanEval
  `data/HumanEval.jsonl.gz` from `openai/human-eval` exactly as parsed. Original MIT
  license copied into `final/data/LICENSE`. Local byte checksum remains frozen.
- Full canonical-only harness preflight: **164/164 pass**; see
  `reference_base.json`. The first preflight (163/164, HumanEval/33 direct-name
  binding issue) is preserved as `reference_base_initial.json`; fixed prospectively
  in PREREG Amendment 2 before any LLM invocation.
- Independent read-only Codex review and two follow-up reviews completed. All
  must-fixes resolved; final review reports no remaining must-fix in scope.
- **0 real model calls.** No generated-program benchmark results exist. Synthetic
  fixture failures are engineering evidence only. User chose all 164 tasks and
  will supply model/endpoint before the real run.
