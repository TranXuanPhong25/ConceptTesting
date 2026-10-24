# v56: fresh LiveCodeBench cohort (conditional on completed v55)

2026-10-24, before mining PUTs or reading any new hidden-test outcomes.
This registration permits infrastructure/metadata preparation only until the
v55 writer transport and review gates pass. No completed v55 baseline exists.

## Cohort and fixed mining cap

Use official livecodebench/code_generation_lite, newest available release;
resolve and record revision before retrieving problem data. Prefer post-writer
cutoff dates only when the exact writer cutoff can be documented. Otherwise
explicitly label contamination risk; do not call the cohort post-cutoff.
Exclude all 76 original VibePass question IDs using identity metadata only,
including both dev and held-out, plus exact normalized statement duplicates.
Do not inspect or execute VibePass held-out source/tests/outcomes. The current
local LCB files are filtered to VibePass and are unsuitable as a fresh cohort.

Choose the newest 60 nonoverlapping functional LeetCode problems (contest_date
descending, question_id lexical tie-break), with parseable signatures and at
least one public and one hidden test. Eligibility uses metadata/schema only.
Two independently generated plausible solution attempts/problem, fixed at 120
PUT calls, no targeted bug injection and no hidden-test feedback to generators.
GPU endpoint first if available, model label/config recorded before calls;
otherwise Codex PUT generator is an explicitly allowed deviation, with the
same prompt-only isolation as v55. Use all attempts passing every public test
and failing >=1 hidden test, at most the first such attempt/problem. Include
empty/low-yield cohort as a result; never add more problems or calls to rescue
it. Separate public failure, hidden pass, hidden fail, timeout, and harness
error. Only ordinary wrong-value/exception hidden failures establish a buggy
PUT; ambiguous harness failures are not retained.

## Frozen comparison (not yet activated)

Before mining execution, an append-only amendment must pin source revision,
60-problem manifest hashes, generation config, and independently reviewed
adapter for official LCB tests into the v53 machinery. A second freeze before
pipeline calls pins v55's Codex writer configuration: plain input generator,
open validity filter, k=3 defn oracle, public filtering/quorum/cap20. Include
v55 interpretation only if its registered promising gate passes. Controls:
Codex defn and matched placebo, all freshly generated, paired on identical
new inputs/filter. Do not reuse Sonnet answers or select based on new pipeline
outcomes. A fresh cohort has no pre-existing v49 universe: register a fixed
public-seeded tool input pool as a separate control before execution.

Report cohort yield, confirmed tasks, confirmed tests, precision, FA invalid
vs wrong-value vs unknown, common-mode and abstention; paired task wins/losses
and problem-level exact paired sign test, with absolute differences. No claim
from a missing arm or incomplete writer batch. Independent Codex review before
mining/evaluation outcomes. Check Codex 5h quota before each large batch; <15%
remaining means checkpoint, commit, stop and report reset. No paid API fallback,
Kaggle notebook edits, automatic endpoint wait loop or VibePass held-out run.
