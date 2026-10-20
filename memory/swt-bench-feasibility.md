---
name: swt-bench-feasibility
description: User asked whether SWE-bench can evaluate current concept direction; SWT-Bench is the direct test-generation formulation
metadata:
  type: reference
---

2026-10-14: User requested feasibility advice alongside GPU resume. SWE-bench evaluates repair; SWT-Bench
provides a repository-level reproduction-test setting. Suitability is a proposal, not an authorized benchmark
launch or demonstrated concept benefit. Details, primary sources, adapter work and leakage controls:
[separate SWT-Bench notes](../trickcatcher_linefacts/research/swt_bench/NOTES.md) and
[SWE-bench notes](../trickcatcher_linefacts/research/swe_bench/NOTES.md).

**How to apply:** use author harness when implementing an authorized benchmark adapter. Freeze retrieval and
localization across concept/plain controls. Keep issue-reproduction results separate from function-level
LineFacts metrics. No SWE/SWT model run or environment build has started.

2026-10-14 (Codex): User compared SWT-Bench, BugsInPy and Defects4J for ease of analysis and
generalizing bug causes. Recommendation (not a confirmed benchmark choice): Defects4J for
controlled root-cause studies because fixes are manually minimized and triggering tests are
verified; BugsInPy for compatibility with the current Python pipeline; SWT-Bench for later
repository-level issue reproduction. Official references: https://github.com/rjust/defects4j,
https://github.com/soarsmu/BugsInPy, https://github.com/logic-star-ai/swt-bench.
Concept taxonomy should describe behavioral obligations and failure conditions rather than patch
syntax; keep fixed source/patch/golden reproducer out of generation context and use them for
evaluation/post-hoc analysis. No implementation or benchmark run authorized by this comparison.
