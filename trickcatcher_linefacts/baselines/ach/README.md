# ACH baseline (reimplementation)

**This is a reimplementation from the paper. There is no official code.** ACH is Meta's internal Kotlin/Android system. The user asked for this reimplementation (PLAN_BASELINES.md §2, step 3; AGENTS rule 2). The code follows the paper's text, Figure 1 and Table 1, and is adapted to the TrickCatcher setting.

Paper: C. Foster, A. Gulati, M. Harman, I. Harper, K. Mao, J. Ritchey, H. Robert, S. Sengupta. *Mutation-Guided LLM-based Test Generation at Meta*. FSE Companion 2025 (industry). arXiv 2501.12862v1.

## Which part follows which paper section

| Step (Figure 1) | Paper | Code |
|---|---|---|
| Concern → **Make a fault** (LLM, Table 1 prompt). The mutated part is delimited by `MUTANT <START>/<END>`. | §2, Table 1 | `prompts.make_fault`, `mutants.assemble` |
| **Builds?** → **Passes** the existing tests? Faults that existing tests catch are discarded. | Fig. 1, §3 | `sandbox_worker.py` mode `mutant` |
| **Remove syntactically identical faults**, comparing after the simple pre-processing that strips the comments the generator added | §5.2–5.3, Tables 6–7 | `mutants.strip_comments`, `mutants.normal_form` |
| **Equivalence detector** (LLM-as-judge, Table 1 prompt). Only mutants the agent believes non-equivalent (`no`) go on. `yes` and unclear answers are discarded. | §2, §5, Table 2 | `prompts.equivalence`, `mutants.judge` |
| **Make a test to catch fault** (Table 1 prompt): the original, the mutant with markers and the existing tests, then "write an extended version … fail on the mutant … pass on the correct version" | §2, Table 1 | `prompts.make_test` |
| TestGen-LLM part: **Builds** → **passes on original** → **fails on the fault**. Other new tests are discarded; there is no repair loop. | Fig. 1 (dotted box) | `run.keep`, `sandbox_worker.py` mode `tests` |

## Adaptations and why

1. **Concern = the function's specification.** `CONTEXT: Faults that make the function `f` violate its specification, i.e. the behaviour that the docstring of `f` requires.` The paper's concern text was a privacy-issue summary.
   - The paper's `similar to {diff}` (an example of an earlier fault) is dropped: no earlier faults exist in this setting.
   - Kotlin class/method/test class is replaced by Python code/function/test function, and `//` markers by `#`. The rest of the Table 1 wording is unchanged.
2. **Unit under test = the PUT file.** Helpers are included; in the held-out set the `Solution` class and its wrapper are included too. As in the paper ("each method is replaced …"), the LLM may rewrite each function. Its definitions are spliced into the PUT by name, so the MUTANT comments are kept for the test prompt. A response that defines no function of the PUT does not build.
3. **One mutant per call, several per sample.** The paper makes one mutant per class and stops a class once a mutant builds and passes (footnote 3). Here each sample repeats the cycle (fault, equivalence, test = 3 calls) while:
   - fewer than `--mutants` (3) fault attempts have been made, **and**
   - at least 3 calls of `--llm-budget` (6) remain.

   A discarded fault costs one call. Mutants identical to the original, or to an earlier mutant of the same sample, are discarded before the judge.
4. **Comment stripping.** In Python, a lexical comparison of comment-free code is done on the AST (`ast.dump`), which carries no comments and ignores layout. Docstring-only changes are not removed by this rule; the judge decides them. The judge is shown both versions with `#` comments stripped, since misleading comments are the paper's main judge error (§5.2). The judge runs at temperature 0, which the paper does not specify.
5. **Test case = one assertion.** The extended `check(candidate)` is flattened into standalone assertions, with no execution (`tc.flatten`):
   - `candidate` becomes the entry point;
   - local assignments are substituted;
   - a held-out comparison helper `_heldout_same(x, y, tol)` becomes `x == y`;
   - base-test copies are dropped.

   "Builds" means the response parses and the assertion is self-contained (otherwise it is rejected and logged). One sentence asks for `assert candidate(<arguments>) == <expected>` lines in one code block.
6. **Run-check filter (`--filter`).** Every check runs the assertion on the PUT `--repeats` (5) times; TestGen-LLM requires consistent (non-flaky) passes.
   - `run` (default, as the task specifies: "keep tests that run … that kill the mutant"): the assertion **runs** on the PUT with the same outcome every time and every call returns, and the PUT and the mutant **return different results** for its inputs (the input kills the mutant). Why this is the default: the setting scores **inputs** with the ref oracle (PLAN §1). Requiring the assertion to pass on a possibly buggy PUT would throw away exactly the inputs whose spec-correct expected value differs from the buggy PUT.
   - `paper` (literal ACH/TestGen-LLM): the assertion **passes** on the PUT in all repetitions and does **not pass** on the mutant. The kept expected values are then PUT outputs (regression oracle), so o0 detection is 0 by construction.
7. **Test cap.** At most `--max-tests` (10) assertions per sample, taken round-robin over the killed mutants. `n_assertions_uncapped` records the count before the cap. A sample with no killed mutant has 0 assertions; that is ACH's real outcome, with no fallback.
8. **Sampling.** K = 3 samples per task.
   - Fault and test calls: temperature 0.7, top_p 0.95, max_tokens 2048.
   - Judge: temperature 0, max_tokens 512.
   - Seeds: `20261010 + 1.5e9 + ((task*1000+sample)*64 + stage*16 + attempt)`.
9. **Sandbox.** All model-written code (mutants, tests) runs as `timeout -k 5 T unshare -rn python -I -B sandbox_worker.py`:
   - no network, isolated interpreter;
   - environment limited to `PATH`/`LANG`, so no endpoint or keys reach it (a test checks this);
   - 4 GB address-space limit;
   - per call/assertion alarm of `--call-timeout` 5 s, plus a total timeout.

## Commands (from the repository root)

```bash
# offline tests (scripted client, no LLM; the sandbox tests need unshare)
python -B -m unittest trickcatcher_linefacts.baselines.ach.test_ach -v

# dry run with the scripted client on 3 dev tasks
python -B -m trickcatcher_linefacts.baselines.ach.run \
  --tasks trickcatcher_linefacts/out/pipelines/v7/humaneval/tasks_hybrid.json \
  --out trickcatcher_linefacts/out/pipelines/v7/humaneval/baselines/ach_dryrun_fake --k 3 --task-ids 2 3 4 --fake

# real run (GPU endpoint; needs QWEN_BASE_URL from the user's env). Without --online it replays <out>/cache only.
python -B -m trickcatcher_linefacts.baselines.ach.run \
  --tasks trickcatcher_linefacts/out/pipelines/v7/humaneval/tasks_hybrid.json \
  --out trickcatcher_linefacts/out/pipelines/v7/humaneval/baselines/ach --k 3 --online
```

Options: `--llm-budget 6`, `--mutants 3`, `--max-tests 10`, `--filter run|paper`, `--repeats 5`, `--call-timeout 5`, `--sandbox-timeout 120`, `--max-tokens 2048`, `--python` (sandbox interpreter, default the current one; the PUTs need only the stdlib), `--workers 4`, `--task-ids …`. A rerun into the same `--out` resumes matching samples. A changed configuration is refused.

Scoring uses the unchanged v7 evaluate and oracle, with the same commands as in `../symprompt/README.md` and `D` set to the ACH `--out` directory.

## Output

- `<out>/gen.jsonl`: the v7 row fields (`arm='ach'`) plus `filter`, `mutant_attempts` and `mutant_statuses`. Each attempt holds its mutant source, build/pass result, judge verdict, candidate tests, per-assertion sandbox checks and kept tests. The statuses are `does-not-build`, `killed-by-existing-tests`, `syntactically-identical`, `duplicate`, `equivalent`, `unsure`, `tests-do-not-build`, `no-new-tests`, `test-run-failed`, `not-killed` and `killed`. The row also has `n_mutants_killed` and `n_assertions_uncapped`.
- `<out>/tasks.json`, `manifest.json`, `cache/` and `artifacts/<task>/<sample>/`. The artifacts hold every prompt and response, `mutantN.py`, and the sandbox jobs and results.

## Files

`prompts.py` (Table 1 prompts), `mutants.py` (rule-based steps), `sandbox_worker.py` (sandboxed checks, standalone), `run.py` (runner), `tc.py` (TrickCatcher adapter, identical copy of `../symprompt/tc.py`), `fake_client.py` (scripted client), `test_ach.py`.
