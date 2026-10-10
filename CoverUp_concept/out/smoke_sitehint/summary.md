# Site-hint smoke (string_utils, flutils)

Target mutants: survived seed-1 stock CoverUp tests. Killed = by seed-1 tests + the arm's new tests.

| subset | n | control | hint | placebo | hint vs placebo (only/only, p) | hint vs control (only/only, p) |
|---|---|---|---|---|---|---|
| all | 337 | 129 | 178 | 82 | 103/7, p=5.25e-23 | 83/34, p=6.78e-06 |
| semantic | 212 | 62 | 106 | 34 | 77/5, p=1.2e-17 | 60/16, p=3.85e-07 |
| semantic, line has a hint | 62 | 29 | 34 | 14 | 21/1, p=1.1e-05 | 10/5, p=0.302 |
| semantic, no hint on line | 150 | 33 | 72 | 20 | 56/4, p=9.08e-13 | 50/11, p=4.59e-07 |
| message-only | 125 | 67 | 72 | 48 | 26/2, p=3.03e-06 | 23/18, p=0.533 |

Hint compliance (suggested literal inputs that appear in the new tests; same literals checked in every arm):

- control: 40/98
- hint: 82/98
- placebo: 39/98

Generation:

- control: 48/53 functions with passing tests
- hint: 52/53 functions with passing tests
- placebo: 45/53 functions with passing tests

Cost: {"control": {"calls": 691, "errors": 498, "in": 413547, "out": 226663, "usd": 0.6745}, "placebo": {"calls": 633, "errors": 429, "in": 506978, "out": 281701, "usd": 0.8412}, "hint": {"calls": 689, "errors": 488, "in": 515210, "out": 257562, "usd": 0.7806}}
