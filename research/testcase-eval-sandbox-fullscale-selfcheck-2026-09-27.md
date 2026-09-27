# Full-scale TestCase-Eval sandbox selfcheck (2026-09-27)

## Result

Ran the complete cached `submission_lite` corpus after clearing
`testcase_eval/data/build`, using 12 workers on the 16-core host. Both runs
used the patched `testcase_eval.sandbox` and the cached pinned parquet data:

```text
python -m testcase_eval.selfcheck --type right_submission --workers 12
python -m testcase_eval.selfcheck --type wrong_submission --workers 12
```

The accepted (`right_submission`) run matched its first official sample in
2,539/2,773 runnable rows (91.6%; 2 Python-2-family rows are skipped). This
is consistent with the documented host/judge toolchain and sample-data drift;
there were no `system_error` results. The wrong-submission run completed all
10,000 rows, with 9,455 sample matches and likewise zero `system_error`s.

| language | right: match / total | wrong: match / total |
|---|---:|---:|
| C++14 | 30 / 31 | 185 / 195 |
| C++17 | 414 / 444 | 1,598 / 1,681 |
| C++20 | 963 / 1,014 | 1,590 / 1,683 |
| C++23 | 227 / 244 | 383 / 406 |
| Java 21 | 301 / 342 | 1,779 / 1,869 |
| Java 8 | 144 / 165 | 778 / 804 |
| PyPy 3 | 26 / 28 | 165 / 175 |
| PyPy 3-64 | 325 / 386 | 1,562 / 1,667 |
| Python 3 | 109 / 119 | 1,415 / 1,506 |

Skipped rows: right 2 and wrong 14 (Python 2/PyPy 2), as those language
families are deliberately outside this extension's supported table.

## Failure analysis

The concerning-looking accepted runtime clusters are not sandbox failures:
Java and PyPy 3-64 failures concentrate in interactive Codeforces problems
(including 2037E, 2032D, 2036G, 2001C, and 1999G1/G2). Their stored first
sample does not provide the interactive judge protocol, so the expected EOF
or malformed-token errors occur across independent implementations and
languages. This also explains related accepted mismatches.

The three accepted C++ compilation errors (and 11 wrong-submission compile
errors) are GCC 16 compatibility drift, including historical submissions that
do not compile under the host toolchain; they are the already-disclosed class
of drift, not a difference introduced by the patched executor. Other rare
runtime, timeout, memory-limit, and mismatch results are distributed across
historical submissions and expected for this sample-only probe.

No reproducible defect in a sandbox patch was found, so no source or test
change was warranted.

## Regression check

`python -m pytest tests/`: **81 passed**.
