# VibePass as a TrickCatcher held-out set: feasibility (CPU only, no LLM)

Script: `analysis/vibepass_feasibility.py` (`decode` / `run` / `report`). Output: `out/heldout_vibepass/usable.json`
(one record per VibePass row, with the flags below). Raw counts: `out/heldout_vibepass/scratch/report.txt`.

Data (downloaded, kept only under `out/heldout_vibepass/data/`, never imported):
- `Salesforce/vibepass` @ `36892367` (173 rows, 76 questions).
- `livecodebench/code_generation_lite` @ `0fe84c39`, only the 76 needed question_ids (streamed and filtered,
  `scratch/fetch_lcb.sh`). Private tests decoded as LiveCodeBench does (json, else base64 -> zlib -> pickle),
  with an unpickler that blocks every global.
- LiveCodeBench `testing_util.py` and LICENSE (`data/lcb_src/`), read only to compare harnesses.

Execution: every dataset program, `test_checker` and unpickle runs in `unshare -rn python3 -I -B` (CPython 3.12 +
sortedcontainers), empty temp cwd, 4 GB address-space limit, 10 s per test with one 60 s retry on timeout.
Comparison follows LiveCodeBench (LeetCode: JSON value equality; AtCoder: stripped lines, then Decimal tokens).
Fuzz: our own mutator over the official inputs (400 candidates per row), filtered by the row's `test_checker`,
up to 80 valid inputs per row run on silver and buggy.

## 1. Usable PUTs

| step | rows |
|---|---|
| all VibePass rows | 173 |
| buggy passes all public tests | 83 |
| ... and fails >= 1 private test | 73 (WA on 72 rows; 1 row only TLE > 60 s) |
| ... and differs from silver on >= 1 checker-valid input (private test where silver passes) | **73 usable** (30 questions) |
| usable_strict: difference is WA/RE (not only TLE) AND silver passes all public+private | **71** (28 questions) |

- Fuzz confirms a difference on 50 of the 73 rows; it found no row that private tests missed (fuzz-only = 0).
- The bugs are subtle: share of private tests the usable buggy fails, quartiles 0.025 / 0.08 / 0.23 / 0.32 / 0.95.
- Rows cluster by question: 73 rows come from 30 questions (top questions have 7, 7, 7, 5 buggy variants).
  Any statistics must be clustered/bootstrapped by question.
- The 90 rows whose buggy fails a public test are not TrickCatcher PUTs. This is expected: VibePass only requires
  the buggy to pass 10-90% of all official tests, not the public ones.

**VibePass label artifacts (10 rows).** 10 AtCoder buggy solutions pass all public AND all private tests under a
real interpreter. All 10 match one of two LiveCodeBench harness quirks: (a) `input()` mixed with
`sys.stdin.read()` (LCB patches `sys.stdin.read` to return the whole input again, so the first line is read twice:
abc307_a#11, abc372_d#28, abc378_c#42/#63/#64, abc330_b#113), or (b) `threading.Thread(target=main).start()` without
join (output printed after LCB's wrapped function returns is lost: abc369_g#19, abc371_f#20, arc196_a#35/#54).
So these rows are "buggy" only inside the LCB harness. Our harness first had the reverse problem with (b): it killed
the program's threads at exit. This is fixed now (non-daemon threads are joined; threaded code re-run), and abc371_f#20
moved from "usable" to "passes everything".

## 2. Silver solutions

- Pass all public tests: 173/173. Pass all private tests: 170/173.
- The 3 failures are TLE only (15 tests even at 60 s in CPython), rows of abc338_f and abc371_f (AtCoder; the
  silver probably relied on PyPy speed). No silver gives a wrong answer on any official test.
- On checker-valid fuzz inputs, silver is not OK only on abc338_f#16 (33 timeouts). So the checkers do not seem to
  let in inputs that crash the reference.

## 3. Format and wrapping into our HumanEval-style format

| | LeetCode (99 rows, 66 usable / 66 strict) | AtCoder (74 rows, 7 usable / 5 strict) |
|---|---|---|
| program | `class Solution: def f(self, ...)`; 7/99 have helpers outside the class | stdin script; buggy: `__main__` guard 36/74, threading 14, `exit()` 2, `stdin.buffer`/`open(0)` 5, `global` 4 |
| test input | one JSON value per line = positional args | raw stdin text |
| output check | JSON value equality | line/token compare (Decimal), not `==` |

**Minimal LeetCode wrapping (like `heldout/dataset.py`):**
- `entry_point = metadata.func_name`.
- `prompt = def f(<args from starter_code without self>): """question_content"""`.
- `canonical_solution` = `PREFIX` imports + silver class + `def f(*a): return Solution().f(*copy.deepcopy(a))`.
- PUT = the buggy class plus the same wrapper.
- `base_input` = the public tests (args = `json.loads` per line); `check()` built from public input/output pairs.
- `plus_input` = the private tests plus checker-valid fuzz inputs.
- `contract`: `assert is_valid_test(*args)`.
- Hazards: `List`/`Optional` hints need `from typing import *`; some methods mutate their args (deepcopy);
  question_content is long and keeps its own examples.
- Mutation/coverage tools on the PUT see methods inside a class. This needs checking against `mutant_source` / mutmut.

Effort: about 0.5-1 day for a LeetCode adapter plus verification (same shape as the MBPP+ held-out builder, mostly
reuse). AtCoder: +1-2 days. It needs a `solve(stdin:str)->str` runner (StringIO stdin, captured stdout, SystemExit,
thread join, `__main__`), a token-level output compare in place of `COMPARE`, and stdin-text inputs for the input
generators. We also do not know if the line-fact/mutant tools work on script-level code. That is a lot of work for
5 strict rows, so **drop AtCoder**.

**Can `test_checker` be the contract?** Yes, with caveats.
- It is a pure `is_valid_test(*args)` (LeetCode) or `is_valid_test(stdin_str)` (AtCoder) returning bool. It is
  type/range/structure checks, median 21 lines.
- It accepted every official public+private input on all 173 rows (no false rejections).
- It rejected 52% of our fuzz candidates (10,164 / 21,038 valid), so it is not a no-op. It accepted every candidate
  in only 10/83 rows.
- Caveats: GPT-5-mini wrote these checkers (per the paper), not humans. They may miss guarantees stated in prose
  (for example "an answer always exists"). Silver behaved on all valid fuzz inputs except one TLE row, so we found
  no such hole, but we did not audit them by hand.
- For our contract format: `def f(args): assert is_valid_test(args)` (or raise ValueError).

## 4. Difficulty mix of usable PUTs

| | usable (73) | strict (71) |
|---|---|---|
| LeetCode hard | 45 | 45 |
| LeetCode medium | 21 | 21 |
| AtCoder hard | 5 | 3 |
| AtCoder medium | 2 | 2 |
| easy | 0 | 0 |

LeetCode-only strict set: 66 PUTs / 24 questions, all medium/hard (VibePass kept only problems frontier models
failed). Contest dates are 2023-05 .. 2025-04; 49/73 usable rows are from contests >= 2024-10. Older problems carry
a contamination risk for Qwen2.5-era models.

The difficulty is very different from MBPP+/HumanEval+. Buggy median is 77 LOC (silver 31), and the specs are long
competitive-programming statements. A 7B generator may find it hard to even produce valid inputs, so expect low
absolute numbers. Our dev results will not transfer directly.

## 5. License caveats

- VibePass: CC-BY-4.0 (dataset card). Attribution needed (Bansal et al. 2026, arXiv 2603.15921). OK for research use
  and for redistributing derived PUT files with credit.
- LiveCodeBench `code_generation_lite`: the dataset card says only `license: cc` (variant not specified); the
  LiveCodeBench code is MIT.
- The problem statements and tests come from LeetCode/AtCoder, which keep their own terms (LeetCode content is
  copyrighted). Safe use: research evaluation, and cite both datasets. Do not republish the statements/tests in bulk
  in a public repo: keep `out/heldout_vibepass/data/` out of git and ship only the build script plus ids.
  The decoded private tests are large (~650 MB filtered jsonl); never commit them.

## Recommendation

Feasible as a secondary held-out set: **66 LeetCode strict PUTs (24 questions)**.
- Use a LeetCode-only adapter: public tests -> base `check()`, silver -> reference, `test_checker` -> contract,
  private tests + checker-valid fuzz -> scoring inputs.
- Report results clustered by question.
- Drop AtCoder (5 strict rows, high wrapping cost, LCB stdin artifacts).
- Treat it as a hard-problem stress test, separate from the MBPP+ held-out set, not pooled with it.
- Before freezing, re-verify each PUT inside our own format: the base check passes on silver and PUT, and some
  private/fuzz input makes the PUT differ.
