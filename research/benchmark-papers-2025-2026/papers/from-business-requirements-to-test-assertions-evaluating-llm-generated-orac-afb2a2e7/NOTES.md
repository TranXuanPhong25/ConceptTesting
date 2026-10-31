# From Business Requirements to Test Assertions: Evaluating LLM-Generated Oracles on Real Bugs

Reviewed: 2026-10-15. Full text read; artifact link found but not publicly downloadable in this audit. Grade: C / conditional.

Paper: [arXiv:2607.10277 v1](https://arxiv.org/abs/2607.10277), 11 July 2026; CC BY 4.0.

Uses 10 Defects4J Lang bugs (IDs 1 and 3–11). Authors manually derive business requirements and a REQ oracle from buggy/fixed diffs, then ask five LLMs to write Java oracle code from the requirement + signature only. Evaluation compares model outputs both to the manually derived REQ and to actual SUT behavior. DeepSeek-V3 macro-F1: 0.8179 on REQ / 0.7476 on SUT; Qwen3-Coder-480B: 0.7779 / 0.7030. SUT/REQ disagreement is an important point; this is requirements-to-oracle, not issue-to-BRT generation or root-cause localization.

Authors claim a 171.51 MB MIT Figshare package with requirements, REQ, generated oracles, tests and scripts. The landing page says “shared privately”; browser later returned 403 and direct download returned HTTP 202/empty. Package contents and license could not be verified, so do not assume own-Qwen evaluation is ready. Only ten bugs from Lang; results are a low-powered pilot.

No code/model run. Detailed evidence: `audit/reviews/079.json`, `public_evidence/source_audit.md`.
