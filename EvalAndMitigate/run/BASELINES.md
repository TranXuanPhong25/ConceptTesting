# Baselines (Gemini 2.5 Flash, thinking off, 78 methods / 60 bugs, run 2026-09-29/30)

Percentages over compiled tests. Red-precision = E / (E + FP). Numbers from `python3 run/summarize.py <log>`.

**Use the "clean" numbers.** Some evaluation runs fail as a whole but leave an empty error report
("buggy/fixed passed False" + "<side> error empty"); the upstream counters then score every test passing on the other
version as M (or E). `run/summarize.py` flags these methods as glitched and prints raw and clean lines. When comparing two
configs, compare on the intersection of their clean methods (per-method data: see m1_test_review/analyze.py `parse`).

| config | FILE_POST_FIX | log (data/rq1/logs/…) | generated / compiled | glitched | clean M | clean E | clean FP | red-prec | ≥1 M | ≥1 E |
|---|---|---|---|---|---|---|---|---|---|---|
| Doc W/ Code | `unified_invoked_docstring_code_prompt` | `*_docstring_code_prompt_log_2.log` | 1013 / 858 | 0 | 20 (2.33%) | 70 (8.16%) | 166 (19.35%) | 0.297 | 8 | 20 |
| Only Doc (paper's method) | `unified_invoked_docstring_prompt` | `*_unified_invoked_docstring_prompt_log_1.log` | 1326 / 1222 | 1 (Lang_11) | 10 (0.83%) | 77 (6.41%) | 300 (24.98%) | 0.204 | 5 | 27 |
| Advanced Doc | `unified_invoked_advanced_docstring_prompt` | `*_advanced_docstring_prompt_log_1.log` | 1308 / 1138 | 3 (Cli_8, Lang_11, Lang_4) | 9 (0.84%) | 95 (8.89%) | 268 (25.07%) | 0.262 | 3 | 30 |

Raw Advanced M was 33; 24 of those came from the glitched Cli_8/Lang_4 runs.

Paper, Gemini 2.5 Flash, full 318 methods: Doc W/ Code M 3.23% E 4.08%; Only Doc M 2.39% E 4.60%;
Advanced Doc M 1.67% E 4.46%.

Per-method breakdowns: parse the logs (each `INFO - Processing Project:` block; the "reported" counters are
cumulative, so per-method values are differences between consecutive blocks — see `run/summarize.py`).
Note: per-test pass/fail files inside the Defects4J checkouts (`d4j_proj_base/<Bug>/fixed/generated_tests/…`)
are overwritten by each new evaluation of the same method, so they reflect only the most recent run.
