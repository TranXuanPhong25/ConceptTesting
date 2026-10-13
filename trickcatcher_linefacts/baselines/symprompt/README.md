# SymPrompt baseline (reimplementation)

**This is a reimplementation from the paper. There is no official code.** The user asked for it (PLAN_BASELINES.md §2, step 3; AGENTS rule 2).
The paper says SymPrompt "is currently a proprietary research prototype" (§1, contribution 2). The code follows the paper's text and figures and is adapted to the TrickCatcher setting.

Paper: G. Ryan, S. Jain, M. Shang, S. Wang, X. Ma, M. K. Ramanathan, B. Ray. *Code-Aware Prompting: A Study of Coverage-Guided Test Generation in Regression Setting using LLM*. FSE 2024 (PACMSE 1, FSE, Article 43). arXiv 2402.00097v2.

## Which part follows which paper section

| Part | Paper | Code |
|---|---|---|
| Collect paths: preorder AST walk. Each branch and loop condition is recorded on the path. A branch that is not taken is recorded inverted (`not cond`). At a `return`, the path is recorded with its return expression. Conditions stay source expressions (approximate constraints, not solved). | §3.2.1, Fig. 2 | `pathcollect.Collector` |
| Path minimization: Algorithm 5a runs after every branch or loop statement. A path is kept only if it adds a branch constraint that the linearized set does not have yet. Three if/else in a row give at most n+1 = 4 paths. | §3.2.2, Fig. 5 | `pathcollect.minimize` |
| Context: (1) imports and globals; (2) type context, meaning classes of the file used by the focal method; (3) focal class signature and constructor; (4) focal-class methods and file functions that the focal method calls; (5) the focal method. | §3.3, Fig. 6 | `prompts.context` |
| Path prompt: a test stub whose docstring has `Testcase i for <signature>`, then `where c1,\n c2, …` (all constraints must hold), then `returns: <expr>` when the path ends in a return. | §3.4, Fig. 3, 7, 11a | `prompts.stub` |
| Paths are prompted one at a time. Tests generated earlier go into the next prompt. | §3.4, Fig. 4 | `run.sample` |
| Parse repair: delete lines from the end until the output parses. | §3.4 | `prompts.parse_repair` |
| Execution context overrides model imports | §3.4 | Model imports are dropped. Assertions run in the PUT namespace (v7 evaluate). |

## Adaptations and why

1. **Chat model instead of completion.** CodeGen2 completed a file; Qwen2.5-Coder-Instruct is a chat model. One user message holds:
   - an instruction to complete the last test function, plus the assertion format `assert f(<args>) == <expected>`;
   - the test file: context, existing tests, tests so far, then the stub.

   The system message is the one every v7 arm uses (`You are an expert software tester.`). The paper used chat models (GPT-4, §4.4) the same way: path descriptions inside test docstrings.
2. **Base tests in the test file.** The TrickCatcher setting gives every method the spec (docstring), the PUT and the base `check()`. The base tests are shown under `# Existing tests` before the generated tests. The paper had no existing tests. Assertions that copy a base assertion are dropped.
3. **Output = assertions.** Each generated test function is flattened into standalone assertions, with no execution (`tc.flatten`):
   - local single assignments are substituted (`r = f(x); assert r == 3` becomes `assert f(x) == 3`);
   - `candidate` is renamed to the entry point;
   - `self.assertEqual` becomes `assert ==`;
   - a comparison helper of the existing tests (the held-out `_heldout_same(candidate(x), y, tol)`) becomes `candidate(x) == y`;
   - assertions that still depend on loop variables, mutated locals or helpers defined in the test are rejected and logged in `per_path[].rejected`.
4. **Python loops.** `for t in it` gives `t in it` (body runs) and `not it` (body skipped). `while` gives `cond` and `not cond`. A constant `while True` / `if True` adds no constraint. Loops are taken once (one-iteration unrolling); `break`, `continue` and loop `else` are handled.
   - `try`: a handler path adds `the try block raises E`.
   - `match`: a case adds `<subject> matches <pattern>`.
   - Paths that end in `raise` or fall off the end get no `returns:` line (the paper adds it only for return paths, Fig. 9).
   - Double negation is simplified (`not not x` becomes `x`).
5. **Held-out VibePass wrapper.** The entry may be `def f(*a): return Solution().m(*deepcopy(a))`. Then the paths come from `Solution.m` (the real focal method), the class block is the focal class context (Fig. 6, parts 3–5), and the wrapper (it carries the spec) ends the context. The stub signature is the wrapper's, because tests call the wrapper.
6. **Path budget.** The paper prompts every collected path. Here each sample prompts at most `--max-paths` paths (default = `--llm-budget` = 6):
   - first the paths that add an uncovered branch constraint (Algorithm 5a over the recorded set, in preorder);
   - then the other paths in preorder.

   One LLM call per path, no retries. On the 133 v7 HumanEval tasks this gives a mean of 3.84 collected paths (max 22) and 3.29 prompted paths per sample. On the 66 VibePass PUTs the mean is 17.2 collected.
7. **Test cap.** At most `--max-tests` (10) assertions per sample. They are taken round-robin over paths, so each path is represented. `n_assertions_uncapped` records the count before the cap.
8. **Regression stance kept.** Like the paper, the prompt does not say the code may be buggy. The `returns:` line guides the expected value. Scoring replaces expected values with the ref oracle anyway (PLAN §1), so only the inputs matter.
9. **Sampling.** K = 3 samples per task. Each sample uses temperature 0.7, top_p 0.95, max_tokens 1024, and seeds `20261010 + 1e9 + ((task*1000+sample)*64 + path)`. The static plan (paths, context) is the same for all samples.

No generated code runs during generation. Scoring runs it inside the v7 sandboxes.

## Commands (from the repository root)

```bash
# offline tests (scripted client, no LLM)
python -B -m unittest trickcatcher_linefacts.baselines.symprompt.test_symprompt -v

# dry run with the scripted client on 3 dev tasks
python -B -m trickcatcher_linefacts.baselines.symprompt.run \
  --tasks trickcatcher_linefacts/out/pipelines/v7/humaneval/tasks_hybrid.json \
  --out trickcatcher_linefacts/out/pipelines/v7/humaneval/baselines/symprompt_dryrun_fake --k 3 --task-ids 2 3 4 --fake

# real run (GPU endpoint; needs QWEN_BASE_URL from the user's env). Without --online it replays <out>/cache only.
python -B -m trickcatcher_linefacts.baselines.symprompt.run \
  --tasks trickcatcher_linefacts/out/pipelines/v7/humaneval/tasks_hybrid.json \
  --out trickcatcher_linefacts/out/pipelines/v7/humaneval/baselines/symprompt --k 3 --online
```

Options: `--llm-budget 6`, `--max-paths` (default = budget), `--max-tests 10`, `--max-tokens 1024`, `--workers 4`, `--task-ids …`. A rerun into the same `--out` resumes: finished samples whose `run_id` matches are reused. A changed configuration is refused, so use a fresh directory.

Score with the unchanged v7 code (`D` = the `--out` directory):

```bash
python -B -c "from pathlib import Path; from trickcatcher_linefacts.pipelines.v7 import evaluate, v4_runtime; D=Path('$D'); evaluate.evaluate(D/'tasks.json', D/'gen.jsonl', D/'eval.jsonl', v4_runtime.interpreter(None))"
python -B -c "from pathlib import Path; from trickcatcher_linefacts.pipelines.v7 import oracle_b01 as ob; D=Path('$D'); ob.collect(D, D/'oracle')"
# oracle LLM stage (GPU): same switch as pipelines/v7/run.py --online
python -B -c "from pathlib import Path; from trickcatcher_linefacts.pipelines.v7 import oracle_b01 as ob; from trickcatcher_linefacts.pipelines.v7.llm_client import Client; ob.Client=lambda d, **kw: Client(d, offline=False, **kw); D=Path('$D'); ob.llm(D, D/'oracle', workers=12)"
python -B -c "from pathlib import Path; from trickcatcher_linefacts.pipelines.v7 import oracle_b01 as ob; D=Path('$D'); ob.score(D, D/'oracle', workers=12, use_llm=True)"
```

`evaluate.report` (the v7 seven-arm o0 report) needs the full seven-arm cohort, so it does not apply to a single-arm baseline directory. Compare `eval.jsonl` and the oracle report with the v7 run instead.

## Output

- `<out>/gen.jsonl`: one row per (task, sample). It has the v7 row fields (`task, split, arm='symprompt', sample, model, facts_version, run_id, text, assertions, n_assertions, llm_calls, n_in, n_out, seconds, calls`) plus `focal, n_paths_collected, n_paths_prompted, paths, per_path, n_assertions_uncapped`.
- `<out>/tasks.json`: the input bundle, unchanged. v7 evaluate and the oracle read it.
- `<out>/plans.json`: per task, the context, signature and selected paths.
- `<out>/manifest.json`: configuration and source hashes; `run_id` is its digest.
- `<out>/cache/`: the v7 LLM cache.
- `<out>/artifacts/<task>/<sample>/`: every prompt and response, plus `result.json`.

## Files

`pathcollect.py` (Step I), `prompts.py` (Steps II–III), `run.py` (runner), `tc.py` (TrickCatcher adapter, an identical copy in `../ach/`), `fake_client.py` (scripted client), `test_symprompt.py`.
