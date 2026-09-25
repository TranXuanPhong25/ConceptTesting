# TestEval targeted-line comparison: official prompt + concepts

Evaluated 2026-09-24 with the official TestEval checkout at commit
`6f67dee71de6ccda1767b8c219a93f4ae0a7ce90`. The first 100 records in
`data/leetcode-py.jsonl` supply 639 target lines. Both arms used native Vertex
AI (`gemini-3-flash-preview`, location `global`), temperature 0 and a 256-token
output cap. `testeval_py.paper_runner` constructed the official Gemini
targeted-line prompt and applied the official `format.py` rules. The concept arm
appended AST-derived reachability facts; no other prompt text changed.

The predictions are `testeval_py/paper_protocol_baseline.jsonl` and
`testeval_py/paper_protocol_concept.jsonl`. Both were scored with the official
`eval_linecov.py` in separate temporary evaluation directories.

| Metric | Baseline | Concept |
| --- | ---: | ---: |
| Targets | 639 | 639 |
| Nonempty formatted tests | 633 | 631 |
| Syntax correctness (official evaluator) | 639/639 (100%) | 639/639 (100%) |
| Executable correctness | 633/639 (99.06%) | 631/639 (98.75%) |
| Selected target line covered | 582/639 (91.08%) | 592/639 (92.64%) |

The target-line gain is 10/639, or **+1.56 percentage points**. Paired by
`(task_num, target_line)`, 572 targets were covered by both, 20 by concept
only, 10 by baseline only, and 37 by neither. The exact two-sided McNemar
`p = 0.098737`; this is not significant at 0.05. The official syntax count
includes empty strings, which compile successfully, so the nonempty and
executable counts are more informative for generation reliability.

This is a controlled prompt ablation on a 100-task subset with Gemini 3 Flash.
It does not reproduce the paper's published model scores or full 210-task
aggregate. Earlier `paper100_vertex_*` results used custom prompts and are
not comparable to these paper-protocol results.
