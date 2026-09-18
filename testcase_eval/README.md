# TestCase-Eval Integration

Semantic fault-exposure integration for the official ACL 2025
[TestCase-Eval](https://github.com/FlowRays/TestCase-Eval) benchmark.

The first supported slice is Task 2 on target submissions written in Python 3
or PyPy 3. It follows the official metric shape:

1. Generate one complete stdin input for a named incorrect submission.
2. Run that input on multiple accepted submissions and require a consensus.
3. Run the same input on the target incorrect submission.
4. Count the fault as exposed when the target crashes, times out, or returns an
   output different from the accepted consensus.

This subset is explicit: it is not reported as the full multi-language score.
The official sandbox supports C++, Java, Python, and PyPy; extending those
toolchains is a separate slice.

## Download

```bash
.venv/bin/python -m testcase_eval.data \
  --dataset task2 --out testcase_eval/data/task2.jsonl

.venv/bin/python -m testcase_eval.data \
  --dataset submission_lite --out testcase_eval/data/submission_lite.jsonl
```

## Generate

```bash
source scripts/vertex_env.sh

.venv/bin/python -m testcase_eval.runner \
  --in testcase_eval/data/task2.jsonl \
  --submissions testcase_eval/data/submission_lite.jsonl \
  --out testcase_eval/results/task2_baseline_python.jsonl \
  --condition baseline --python-only
```

Use `--condition concept` for the static concept-guided condition. Generation
is append-only and resumes by `(condition, submission_id)`.

## Evaluate

```bash
.venv/bin/python -m testcase_eval.oracle \
  --pred testcase_eval/results/task2_baseline_python.jsonl \
  --submissions testcase_eval/data/submission_lite.jsonl \
  --out testcase_eval/results/task2_baseline_python_exec.jsonl
```

Dataset and metric definitions are from the official repository and
[ACL paper](https://aclanthology.org/2025.acl-short.82/).
