# TestCase-Eval Task 2 (Python/PyPy subset) — results

Third benchmark slice alongside `bench/` (Juliet) and `magma/` (real-CVE). Uses
the official [TestCase-Eval](https://github.com/FlowRays/TestCase-Eval)
(ACL 2025) Task 2 dataset and metric: generate one stdin input for a wrong
submission, run it on a consensus of accepted submissions and on the wrong
submission, count the fault exposed on divergence (crash, timeout, or output
mismatch vs. consensus). See `testcase_eval/README.md` for the pipeline.

Model: `gemini-3-flash-preview` (native Vertex, `LLM_THINKING_BUDGET=0`,
temperature 0). Conditions: `baseline` (problem statement only) vs `concept`
(problem statement + `static_fault_concepts`, the same tree-sitter-free
static-regex concept extractor used for the Juliet/Magma `concept_static`
condition, ported to competitive-programming source).

## Run: n=113 paired problems

One target (wrong) submission sampled per distinct `problem_id`
(`--one-per-problem`), first 113 problems in official file order that have a
Python 3/PyPy 3 target, both conditions on the identical 113
`(problem_id, submission_id)` pairs.

| cond | fault_exposure (n=113) | fault_exposure&#124;valid | valid_inputs |
|---|---|---|---|
| baseline | 10.6% (12/113) | 36.4% (12/33) | 33 |
| concept_static | 8.8% (10/113) | 31.2% (10/32) | 32 |

McNemar (exact, paired on submission_id): concept-only=2, baseline-only=4,
**p=0.69 (ns)**.

**Concept did not beat baseline here** — opposite direction from the Juliet
result (57%→69%) and consistent with the Magma finding that annotation
*content* stops mattering once any bug-specific context is present (here
*both* conditions already see the full submission source via the problem
prompt, so `concept_static`'s marginal addition is a small regex-tagged hint
on top of source the model can already read — unlike Juliet/Magma blind,
which withholds source entirely). n is too small and effect too close to
null to draw a causal conclusion either way; unlike the Magma ablation this
slice has no `concept_shuffle` placebo run yet.

## Honest limitation: validity is capped by `submission_lite`, not by generation quality

Only 35/113 sampled problems (31%) have **any** Python 3/PyPy 3
`right_submission` in the official `submission_lite` split — the rest have
zero, so a Python-only oracle can never form a consensus for them regardless
of test quality:

- 78/113 invalid records (both conditions) → zero Python right_submissions
  for that problem in `submission_lite` (dataset composition, not our bug).
- 2–3/113 invalid records → a Python right_submission exists but no
  2-way output consensus formed, or the generated input mis-executed.

When a Python consensus *is* available, generation is almost always valid
(33/35 baseline, 32/35 concept) — the oracle's low overall validity is a
property of `submission_lite`'s per-problem language mix under a
Python-only restriction, not of `testcase_eval/runner.py`. A wider sample
(or Task 2's full non-lite submission pool) would raise n of *valid* pairs
without changing this ratio.

## Reproduce

```bash
source scripts/vertex_env.sh
.venv/bin/python -m testcase_eval.runner --in testcase_eval/data/task2.jsonl \
  --submissions testcase_eval/data/submission_lite.jsonl \
  --out testcase_eval/results/task2_baseline_python_n100.jsonl \
  --condition baseline --python-only --one-per-problem --limit 113 --rpm 20
.venv/bin/python -m testcase_eval.runner --in testcase_eval/data/task2.jsonl \
  --submissions testcase_eval/data/submission_lite.jsonl \
  --out testcase_eval/results/task2_concept_python_n100.jsonl \
  --condition concept --python-only --one-per-problem --limit 113 --rpm 20

.venv/bin/python -m testcase_eval.oracle --pred testcase_eval/results/task2_baseline_python_n100.jsonl \
  --submissions testcase_eval/data/submission_lite.jsonl \
  --out testcase_eval/results/task2_baseline_python_n100_exec.jsonl
.venv/bin/python -m testcase_eval.oracle --pred testcase_eval/results/task2_concept_python_n100.jsonl \
  --submissions testcase_eval/data/submission_lite.jsonl \
  --out testcase_eval/results/task2_concept_python_n100_exec.jsonl

.venv/bin/python -m testcase_eval.stats \
  --baseline testcase_eval/results/task2_baseline_python_n100_exec.jsonl \
  --concept testcase_eval/results/task2_concept_python_n100_exec.jsonl
```

## Open

- Add a **true-blind** condition (strip the buggy source out of the official
  prompt entirely) so this slice tests the same axis as Juliet/Magma
  (source vs. no source), not "source + hint" vs. "source alone" — the
  current `baseline` already contains full source (see landscape note
  below), so the null above is not comparable to Juliet's 57%→69%.
- Run `concept_shuffle` (placebo, mislabeled concepts) on the same 113 pairs
  to test whether the (currently null, underpowered) concept result would
  replicate the Magma "shuffle ≥ concept_static" null, or whether it's just
  noise at n=113/valid=33.
- Scale beyond `submission_lite` for problems with zero Python
  right_submissions to raise valid n without relaxing the Python-only oracle.

## Where this sits in the test-gen benchmark landscape (2024–2026)

Naming note: this slice uses **TestCase-Eval** (ACL 2025, Codeforces, Fault
Coverage/Fault Exposure) — **not** TestEval (NAACL Findings 2025, 210
LeetCode-style problems, line/branch/path coverage). Same-sounding name,
different benchmark, different metric family (semantic fault detection vs.
structural coverage). `bench/RELATED_WORK.md` (22-source lit review, done
before this slice) is scoped to C/C++ memory-safety + ASAN; it does **not**
cover this competitive-programming/logic-fault space, so cross-referencing
it here would be misleading.

Actually run in this repo (implemented + executed, numbers above/elsewhere):
Juliet (`bench/`), Magma real-CVE (`magma/`), TestCase-Eval Task 2 Python
subset (here).

Cited in `bench/RELATED_WORK.md` but **not implemented**: VulEUT/VULEUT
(FORGE 2025, reachability/param-transfer analysis for vulnerability-
triggering tests, 64.5%→78.4%) and MultiFileTest (dropping the coverage
requirement *increased* coverage — cited as corroboration for our own
negative coverage-steering result).

Not yet read or tried (surfaced by user literature scan, 2026-09-17, not in
the original 22-source review): **TestExplora** (Microsoft, Feb 2026,
repo-level Fail-to-Pass — buggy commit + generated test = FAIL, fixed commit
+ same test = PASS; closest existing benchmark to this project's red/green
framing, SOTA F2P ~16% for non-agentic models), **TestGenEval** (ICLR 2025,
1,210 real Python file pairs, adds mutation score), **ULT/UnLeakedTestbench**
(2025/TOSEM 2026, 3,909 real functions, targets LeetCode-contamination —
average LLM coverage there is much lower than on TestEval-style benchmarks),
**TestBench** (2025, Java class-level, real projects). None of these are run
or cited anywhere in this repo yet — no results to report.
