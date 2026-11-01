# CHANGELOG

## 2026-10-30 — clarified concept benchmark, active run

- User clarified reference-program oracle, boundary/equivalence/CFG/def-use concepts,
  fixed PUTs generated only once, and research beyond the earlier v7/v11 framing.
- New isolated experiment: `experiments/concept_reference_v1/`; original plain code
  and v7/v11 remain intact. Libraries and secondary cross-PUT contrast documented.
- 27 engineering checks and 164/164 traced canonical checks pass; independent review
  cleared launch. Selected qwen3.5-27b-awq, 8192 context; actual 33-token probe passed.
- Full164 detached controller launched PID93111, initially building the persistent
  cohort. Check live status before any restart; do not start a duplicate generation.
- Detailed lifecycle/results are in the experiment output, not inferred from launch.

## 2026-10-30 — new standalone final pipeline

- Source: new orchestration for the user's explicit pipeline; unchanged local
  original HumanEval dataset copied into `data/`. Earlier v7/v11 code is untouched;
  this is not another arm added to those pipelines or a paper reimplementation.
- Added replaceable CoreModel, OpenAI-compatible backend, structural deduplication,
  base filtering, one-shot shared test generation, reference validation, isolated
  execution, usage tracking, immutable manifests, safe resume and result reporting.
- Added PREREG, README and engineering fixture tests. No commit/push requested.
- Review fixes: original prompt helpers, independent official-test namespace,
  normalized imports, seeded/union-traced base inputs, separate compilation for
  future imports, and original-name target calls in HumanEval/33.
- Validation: 17 engineering checks pass; 164/164 canonical base checks pass;
  independent review and follow-ups complete. Original dataset records verified
  against OpenAI HumanEval; MIT license included.
- Status: ready, awaiting user-supplied model/endpoint for all 164 HumanEval tasks.
  No real LLM invocation or generated-program benchmark result yet.
