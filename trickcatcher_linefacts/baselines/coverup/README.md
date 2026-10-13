# CoverUp baseline

**Reimplementation/adaptation** of CoverUp (Pizzorno & Berger, FSE 2025) for
TrickCatcher. The original read-only checkout is `CoverUp_concept/vendor/coverup`,
commit `d9ca25b9282621d2779560f2be397ab0683a6733`. No author source is modified.

From the original code: `GptV2Prompter` (initial, execution-error and missing-coverage
prompts), `get_missing_coverage`, `State`, `improve_coverage`, and its extraction,
import-check and test-file helpers. Exact definitions are compiled from source to
avoid the original transport’s import-time effects. The original loop proposes a
complete pytest script, checks execution and coverage, feeds back errors or missing
coverage, and saves the first coverage-improving script for each initially missing
segment. Defaults retain 3 attempts per segment, 50-line segmentation and 5 test
repetitions. The upstream version does not reschedule partially covered segments.

Adapted parts:

- Input is the explicit spec/docstring, supplied PUT and base `check(candidate)`.
  Base tests become `test_base()` and seed the initial line/branch coverage.
- coverage.py replaces SlipCover; negative function-exit arcs become zero-exit arcs
  for original segmentation. Candidate tests repeat in fresh worker processes;
  final coverage includes base and accepted scripts. Percentages are coverage.py’s.
- The shared Qwen client replaces upstream transport. Original prompt wording is
  preserved; a context message supplies spec, full module and base tests. `get_info`
  tool calls are replaced by this upfront context. Dependency auto-install is off.
- Segments execute sequentially under the shared 8-call ceiling, including repairs.
  Assertions come only from accepted scripts, ordered by numeric save sequence and
  assertion order, deduplicated and capped at 20 during generation. Drop counts and
  raw code are retained. A fully covered base suite emits no calls or added tests.

`config.json` freezes K=3, 8 calls and 20 assertions. Shared extraction, limits,
output format and options are described in `../README.md`.

Offline example from the repository root:

```bash
CoverUp_concept/.venv/bin/python -B -m trickcatcher_linefacts.baselines.coverup.run --tasks trickcatcher_linefacts/baselines/tests/dev_tasks.json --responses trickcatcher_linefacts/baselines/tests/dev_responses.json --out trickcatcher_linefacts/baselines/tests/another_coverup_run
```

CPU dry run on 2026-10-13, fake `ScriptedClient`, HumanEval development tasks,
K=3 (values below are **per sample**, identical across the three samples):

| Task | Entry | Calls | Exported assertions | Result |
|---|---|---:|---:|---|
| 2 | truncate_number | 1 | 2 | Coverage-improving script accepted |
| 3 | below_zero | 3 | 0 | Three attempts completed without a coverage gain |
| 4 | mean_absolute_deviation | 1 | 1 | Script accepted, including an exception coverage check |

Totals: **9 output rows, 15 scripted calls, 9 assertions, 0 cap drops**. All base
suites passed. Outputs: `../tests/dry_runs/coverup/gen.jsonl`, manifest, task bundle
and complete prompt/response/coverage artifacts. `../tests/dry_runs/summary.json`
records the environment and per-sample results. These are plumbing/loop checks,
not evidence of model quality or spec correctness. Unit tests also verify native
error feedback, no-gain feedback, full-base early stop, explicit specs, the 20-test
cap and protocol rejection. The shared suite passed **22 tests**.

Remaining work is a separately authorized real-Qwen generation run and the common
ref/full scoring comparison. No endpoint call or held-out run was performed.
