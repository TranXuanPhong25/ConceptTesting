# PBT_EdgeCases pilot: results (2026-10-02)

Paper #36: arXiv 2510.25297. The authors' artifact is vendored pristine under `vendor/`; the method and commands are
in `README.md`. Model used here: **Gemini 2.5 Flash** (Vertex, default temperature, thinking off). The paper used
Claude Sonnet 4 via OpenRouter, default parameters, one generation per task, with wrong tests removed by hand.

**Bottom line:**

- Concept vs placebo, the primary comparison, is +0.08 detection rate, which is not significant (sign test p=0.29,
  permutation p=0.18).
- The sign flips (-0.10) when broken test files are scored strictly instead of import-repaired.
- Concept vs plain PBT is +0.16 (permutation p=0.050, sign test p=0.15). About half of that gain also appears with
  the placebo.
- n=16 tasks cannot separate effects of this size.

## 1. Reproduction vs paper

Detection means a test unit is valid (passes on the HumanEval+ canonical solution) and fails on the HumanEval
canonical solution (assertion, exception, or 15 s timeout).

"Majority" means a task counts as detected if its detection rate over K samples is above 0.5. "Any-of-K" means at
least one of the K samples detected it.

| setting | PBT | EBT | notes |
|---|---|---|---|
| paper (Claude Sonnet 4, 1 sample, hand filter) | 11/16 | 11/16 | union 13/16; PBT-only 55, 95; EBT-only 140, 150; both miss 49, 123, 127; McNemar p = 1.00 |
| authors' Claude files, authors' runner (here) | 11/16 | 11/16 | identical per-task sets to the paper (`results/authors_claude_vendored_runner.log`) |
| authors' Claude files, our automatic filter | 10/16 | 10/16 | the only disagreement is HumanEval/76: the authors kept assertions that contradict the HumanEval+ reference, e.g. `is_simple_power(1, 0) == False` |
| Gemini, our filter, majority (K=10 PBT / K=8 EBT) | **7/16** | **9/16** | union 11/16; per-task agreement with the paper: PBT 12/16, EBT 10/16 |
| Gemini, our filter, any-of-K | 14/16 | 14/16 | 123 and 127 are never detected by any arm or sample (the paper also missed both) |
| Gemini, mean per-task detection rate | 0.506 | 0.625 | EBT vs PBT: McNemar on majority 4 vs 2, p=0.69; sign test 11+/2-, p=0.022; permutation p=0.25 |
| Gemini, authors' runner, no filter (file fails on buggy) | 12/16 (rate 0.81) | 16/16 (rate 0.95) | inflated by invalid tests: as in the paper, raw rates need an oracle filter |

Gemini PBT majority set: 22, 44, 63, 64, 97, 122, 124. Gemini EBT majority set: 22, 44, 49, 64, 95, 97, 124, 132, 150.

How Gemini differs from the paper's single Claude run:

- 55 and 95 are only partly caught by PBT (rates 0.4 and 0.3).
- 132 and 76 are weak for PBT.
- 49 is caught by EBT (1.0), although the paper missed it with both methods.

The paper's qualitative claim holds:

- PBT and EBT catch different tasks;
- neither method dominates at the task level;
- 123 and 127 (large numeric range) are missed by both.

Unit validity, i.e. the share of test units that pass on the fixed solution: EBT 0.87, PBT 0.81. In the paper, the
hand filter removed 10% of EBT tests and 5% of PBT tests.

## 2. Concept vs placebo vs plain PBT (primary: `REPAIR=1`)

`REPAIR=1` applies two arm-blind repairs: a hypothesis-import prelude and dedent-on-syntax-error.
`REPAIR=0` (strict) is in section 3.

Per-task detection rate over K=10. Overlap = share of placebo lines identical to concept lines, after removing
parentheticals.

| task | EBT (K=8) | PBT plain | PBT + concept | PBT + placebo | placebo/concept overlap | paper P/E |
|---|---|---|---|---|---|---|
| 22 | 0.88 | 0.60 | **1.00** | 0.80 | 0.00 | P E |
| 44 | 1.00 | 1.00 | 1.00 | 0.90 | 0.17 | P E |
| 49 | 1.00 | 0.40 | 0.90 | 0.90 | 0.17 | - - |
| 55 | 0.50 | 0.40 | 1.00 | 1.00 | 1.00 | P - |
| 63 | 0.12 | 0.90 | 1.00 | 0.40 | 0.00 | P E |
| 64 | 1.00 | 0.90 | 1.00 | 1.00 | 0.00 | P E |
| 76 | 0.25 | 0.20 | 0.30 | 0.30 | 0.73 | P E |
| 95 | 0.75 | 0.30 | 0.50 | 0.20 | 0.00 | P - |
| 97 | 1.00 | 0.90 | 1.00 | 1.00 | 0.18 | P E |
| 122 | 0.38 | 1.00 | 0.80 | 1.00 | 0.07 | P E |
| 123 | 0.00 | 0.00 | 0.00 | 0.00 | 0.38 | - - |
| 124 | 1.00 | 0.80 | 0.80 | 0.70 | 0.00 | P E |
| 127 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | - - |
| 132 | 0.75 | 0.30 | 0.20 | 0.20 | 0.00 | P E |
| 140 | 0.38 | 0.20 | 0.10 | 0.30 | 0.00 | - E |
| 150 | 1.00 | 0.20 | **1.00** | 0.60 | 0.13 | - E |
| mean | 0.625 | 0.506 | **0.662** | 0.581 | | |
| majority | 9 | 7 | 10 | 9 | | |

## 3. Tests (paired at task level, n=16)

| comparison | mode | mean diff | bootstrap 95% CI | McNemar on majority (b/c, exact p) | sign test (+/-, p) | sign-flip permutation p |
|---|---|---|---|---|---|---|
| **concept vs placebo** | REPAIR=1 | **+0.081** | [-0.012, 0.181] | 1/0, p=1.00 | 6/2, p=0.29 | **0.18** |
| concept vs plain | REPAIR=1 | +0.156 | [0.037, 0.294] | 3/0, p=0.25 | 9/3, p=0.15 | 0.050 |
| placebo vs plain | REPAIR=1 | +0.075 | [-0.050, 0.200] | 3/1, p=0.63 | 8/5, p=0.58 | 0.32 |
| EBT vs PBT plain | REPAIR=1 | +0.119 | [-0.077, 0.295] | 4/2, p=0.69 | 11/2, p=0.022 | 0.25 |
| **concept vs placebo** | REPAIR=0 (strict) | **-0.100** | [-0.237, 0.044] | 1/4, p=0.38 | 3/8, p=0.23 | 0.23 |
| concept vs plain | REPAIR=0 | -0.075 | [-0.194, 0.031] | 1/2, p=1.00 | 5/7, p=0.77 | 0.28 |
| placebo vs plain | REPAIR=0 | +0.025 | [-0.081, 0.131] | 3/1, p=0.63 | 7/5, p=0.77 | 0.76 |

Strict mode means rates of concept 0.431, placebo 0.531, plain 0.506. Strict mode reverses the concept effect
because the concept block makes Gemini write `@example(...)` (55/160 files) while it keeps the template's import
`from hypothesis import given, strategies as st`.

Files without runnable tests:

| arm | REPAIR=0 | of which `NameError: example` | REPAIR=1 |
|---|---|---|---|
| concept | 62/160 | 55 | 7/160 |
| placebo | 24/160 | 10 | 14/160 |
| plain | 12/160 | 0 | 12/160 |

A human filter, as in the paper, would probably have fixed or dropped these. Which mode is "right" is a judgment
call, and the answer flips with it.

### Diagnostics

**Where the concept helped:**

- 150: concept 1.0, placebo 0.6, plain 0.2. The n=0/1 edge is the bug the paper calls a boundary miss.
- 22: concept 1.0, placebo 0.8, plain 0.6.
- 63: concept 1.0, placebo 0.4, plain 0.9. Here the "gain" over placebo is placebo harm: wrong-type list hints for
  an int parameter.
- 95: concept 0.5, placebo 0.2, plain 0.3.

**Where generic hints are enough:**

- 49: concept 0.9, placebo 0.9, plain 0.4.
- 55: concept 1.0, placebo 1.0, plain 0.4.
- These are int-typed tasks whose placebo donor is also int-typed. On 55 the placebo is identical to the concept
  (overlap 1.0), and on 76 it is 73% identical.
- The derangement placebo therefore cannot separate type-generic edge hints ("0, 1, large") from task-specific
  ones. It only tests the task-specific part (docstring constraints, format, alphabet, dict/list edges).

**Misses not recovered:**

- 123 and 127 stay at 0 in every arm. The concept listed `2**53 + 1` (float-precision edge) as an edge and a
  witness, but **0/20** concept files for these two tasks used it. Gemini kept bounded strategies.
- 140 (two trailing spaces) did not improve, although "2 and 3+ consecutive spaces" is in its concept.

**Uptake:**

| arm | files using `@example` | detect rate, units with `@example` | detect rate, units without |
|---|---|---|---|
| concept | 55/160 | 56/113 (0.50) | 221/787 (0.28) |
| placebo | 13/160 | 13/28 | 180/873 (0.21) |
| plain | 0/160 | n/a | 158/940 (0.17) |

These unit counts are clustered, so treat them as descriptive only.

**Detection mechanism (valid units failing on buggy):**

| arm | assertion/exception | timeout |
|---|---|---|
| concept | 210 | 67 |
| placebo | 162 | 31 |
| plain | 141 | 17 |

Timeout detections all come from 55 (fib) and 63 (fibfib), plus a few on 76. The concept arm has the most
(55: 39 units, 63: 26), consistent with its "large value" edges.

**Placebo matching:**

- Same line count per task (144 lines total) and same category order.
- Total characters: concept 12,963, placebo 13,014. Per task, the difference is at most 30%.
- Mean prompt tokens: concept 1,212, placebo 1,213.

**Evaluator determinism:** a re-run of 32 files gave identical unit outcomes on 31. One fib (HumanEval/55) unit
flipped: it is timing-sensitive near Hypothesis' 200 ms deadline (`results/rerun_check_pbt_k3.jsonl`).

## 4. Calls and cost

All calls went to Gemini 2.5 Flash on Vertex, sequentially (concurrency 1), with a hard cap of $3. Prices used:
$0.30 per 1M input tokens and $2.50 per 1M output tokens.

| arm | calls | input tokens | output tokens | USD |
|---|---|---|---|---|
| ebt | 128 | 103,504 | 151,029 | 0.409 |
| pbt | 160 | 151,140 | 220,676 | 0.597 |
| pbt_concept | 160 | 193,960 | 222,576 | 0.615 |
| pbt_placebo | 160 | 194,230 | 207,011 | 0.576 |
| **total** | **608** | 642,834 | 801,292 | **$2.196** |

- 21 retries (429 backoff). One response ended with MAX_TOKENS. There were no thinking tokens.
- Ledger: `gen/ledger.jsonl` (per call: arm, task, k, tokens, USD, seconds, retries, finish).
- Execution is local Docker only. The AndroB2O check used only HTTP range reads from Zenodo.

## 5. Caveats

- **Power.** n=16 tasks.
  - The smallest two-sided sign-test p with m discordant tasks is 2^(1-m), so p < 0.05 needs at least 6 discordant
    tasks all in one direction.
  - The observed concept-placebo effect (+0.08, CI crossing 0) would need several times more tasks to resolve.
    HumanEval has only 16 such canonical bugs, so a real test needs another benchmark (e.g. HumanEval+/MBPP+ seeded
    mutants).
- **Oracle filter.** The HumanEval+ canonical solution replaces the paper's hand filter.
  - It is stricter on HumanEval/76.
  - It treats the HumanEval+ reference as the spec, including spec ambiguities such as `is_simple_power(1, 0)`.
- **Repair-mode dependence.** The concept arm's sign depends on whether the missing `example` import is repaired.
  The primary mode (REPAIR=1) was fixed after seeing the NameErrors in the K=1 pilot and before the full run.
  Both modes are reported.
- **The placebo is partly informative.** For int-only tasks, generic int edges coincide (see the overlap column).
  Wrong-type placebo hints can also hurt (63). "Concept > placebo" therefore mixes concept help and placebo harm.
- **Model differs from the paper.** Gemini 2.5 Flash with thinking off, not Claude Sonnet 4. K samples instead of
  one, and per-task majority instead of a single run.
- **Granularity.** Per-unit validity: a PBT function or EBT statement with one wrong assertion is invalid as a
  whole. The authors' EBT runner stops at the first failing assert, while ours runs every statement.
- **Timeout is per unit.** The paper's 15 s timeout is per file.
- **Concept tool is mine, not the authors'.** Its rules (type edges, docstring regexes) were written from the
  16 prompts' vocabulary, which risks tailoring. They were frozen before generation and before any HumanEval+
  failing input was inspected. The task IDs and the paper's coarse bug categories were known beforehand.

## 6. AndroB2O (#67) feasibility on this arm64 Mac (read-only)

**Method.**

- Zenodo 10.5281/zenodo.15556567 `Artifact.zip` (5.4 GB, CC-BY-4.0) was inspected with HTTP Range requests only.
- All 366 APKs (deflated inside the zip) were streamed into memory once to list `lib/<abi>/*.so`. A second pass
  read `AndroidManifest.xml` `<uses-sdk>`.
- One `*_run_test.sh` per bug was read to get the AVD name.
- Nothing was installed, written to disk (except reports), or executed.
- Files: `androb2o/apk_abis.json`, `pass2.jsonl`, `summary.json`, `summarize.py`.

**APK ABIs (366 APKs):**

| class | APKs |
|---|---|
| pure Java (no `lib/*.so`) | 180 |
| include arm64-v8a | 123 |
| x86 only | 37 |
| no arm64, x86 + 32-bit ARM/mips | 5 |
| 32-bit ARM only (armeabi-v7a) | 21 |

By folder:

- buggy `fbaa_apks`: 16 x86-only, 4 32-bit-ARM-only;
- buggy `andror2plus_apks`: 8 x86-only, 3 x86+ARM32;
- `fixed_apks`: 13 x86-only, 16 ARM32-only, 2 x86+ARM32;
- `unseen_data_apks`: all arm64-compatible.

**Bug pairs.** A failure-based oracle needs the buggy and the fixed APK.

- Of 165 bugs with both, **131 (79%)** have both APKs pure Java or with arm64-v8a.
- **34 (21%)** need an x86 image or 32-bit ARM execution for at least one APK.

**API levels.**

- The run scripts boot the AVDs `Pixel_2_Android_{5.0,6.0,7.1,8.0,8.1,9.0}`, i.e. API 21, 23, 25, 26, 27, 28.
  Bug scripts per AVD: 9.0: 206, 8.0: 54, 7.1: 28, 6.0: 24, 8.1: 22, 5.0: 12.
- Per-APK minSdk ranges from 10 to 32 (64 unknown); targetSdk ranges from 21 to 34.
- The test-harness project: minSdk 18, targetSdk 30, AGP 4.1.1.

**arm64 system images.**

- Google's official SDK repository manifests list `arm64-v8a` system images, in both `default` and `google_apis`,
  for **every API level 21-29**:
  - https://dl.google.com/android/repository/sys-img/android/sys-img2-3.xml
  - https://dl.google.com/android/repository/sys-img/google_apis/sys-img2-3.xml
  - copies are in `androb2o/sysimg_*.xml`.
- API 26-28 arm64 packages require emulator >= 31.1.1, the Apple-Silicon-era emulator.
- The listing does not prove they boot under Hypervisor.framework on M-series; that was not tried.
- Google's M1 emulator preview states "32 bit ARM apps won't work" (https://github.com/google/android-emulator-m1-preview,
  now archived: "ARM64 images can now be downloaded through the SDK Manager"). M-series cores have no AArch32.

**Verdict.**

- **Running the full AndroB2O benchmark here would need x86 emulation:**
  - 42 APKs have no arm64 code but do have x86 code (37 x86-only, 5 x86 + 32-bit ARM/mips). Running them needs an
    x86 system image, i.e. x86 emulation on Apple Silicon. AGENTS rule 4 forbids this.
  - 21 more APKs are 32-bit-ARM-only and cannot run on Apple Silicon at all.
  - Together these block 34/165 bug pairs.
- **A native arm64 subset looks feasible** without emulation: 131 pairs, official arm64 images exist for all six
  API levels used. It is untested. Using it means deviating from the authors' AVD images (theirs are presumably
  x86 Pixel_2 AVDs) and dropping 21% of the bugs, so ask before trying.
