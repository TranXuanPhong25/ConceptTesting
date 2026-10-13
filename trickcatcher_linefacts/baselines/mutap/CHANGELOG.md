# CHANGELOG baselines/mutap

- 2026-10-14: adapter finished (Codex), offline only. Setting = TrickCatcher (spec + PUT + base tests -> assertions),
  same Qwen client (baselines/common.py, URL from env), K = 3, at most 8 LLM calls and 20 assertions per sample
  (drops recorded), at most N = 7 surviving mutants per task (mutmut, as in the paper).
  Provenance (original vs adapted) in README.md. Verified: 22/22 baselines tests pass; fake-client dry run on
  HumanEval 2-4 (tests/dry_runs/summary.json).
- Status: ready for the GPU run under the final comparison protocol (PREREG.md); no real-Qwen output yet.
