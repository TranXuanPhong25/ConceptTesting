# subset150: the replication on ~150 focal methods, five arms

## Question
The 78-method subset (Lang 51, Gson 12, Codec 7, Cli 5, Csv 3) is underpowered and dominated by Lang. Do the main
contrasts (Advanced Doc vs Only Doc; m9 concept vs placebo) and the A/A noise hold when about 70 methods from six other
Defects4J projects are added?

## Dataset
- **Old stratum:** the 78 existing records, unchanged (`data/prompts/buggy_source_data_unified_invoked.jsonl`, read only).
  They are the *whole* upstream selection for their five projects (155 checked-out bugs → 78 methods / 60 bugs).
- **New stratum: 68 methods / 41 bugs**: Time 15, Jsoup 12, Compress 12, Math 12, JacksonDatabind 12, Closure 5.
  Quota 12 methods per project; Closure was stopped early (below). **Total 146 methods / 101 bugs.**
- Files (new names; no existing dataset file is touched):
  - `data/prompts/buggy_source_data_unified_invoked_s150new.jsonl`: the new methods;
  - `data/prompts/buggy_source_data_unified_invoked_subset150.jsonl`: the 78 lines verbatim, then the new methods
    (this order is the method index used everywhere in `analyze.py`);
  - `manifest.json`: seed, quota, every scanned bug with its outcome, the new methods (bug, signature, index).

### Sampling plan (`plan.py` → `out/plan.json`; `sample.py`)
1. Candidates per project: every bug in `data/d4j2_fix_info`, minus the evaluation notebook's `deprecated_bugs`
   (`UT_Compile_and_Test_Project.ipynb` cell 7: JacksonDatabind_65, _89 here) and minus bugs whose fix info lists no
   changed function (cell 77 of the source-data notebook makes no record for them). Both can only yield 0 methods.
2. Order: `random.Random(150).sample(candidates, len(candidates))` per project (candidates sorted by bug number first).
3. Walk the order, one bug at a time, strictly sequential checkouts (`defects4j checkout`, a failed one is removed and
   redone once, then the bug is skipped):
   - check out the buggy version and run the upstream source-data notebook on that bug;
   - only if some buggy record is invoked by a trigger test and public/protected (necessary for the final filter):
     check out the fixed version, run the source-data notebook on it, then the upstream unify notebook;
   - the methods that come out of unify are kept, all methods of a bug together.
4. Stop a project as soon as it has ≥ 12 methods. Finally, one upstream unify run over all kept bugs builds the
   dataset files; `sample.py final` asserts it equals the per-bug results.

### What the sampling found (`out/sampling.jsonl`, `manifest.json`)
| project | candidates | scanned (buggy checkouts) | fixed checkouts | bugs kept | methods |
|---|---|---|---|---|---|
| Time | 25 | 10 | 7 | 7 | 15 (Time_3 alone: 6) |
| Jsoup | 82 | 27 | 7 | 7 | 12 (Jsoup_22: 6) |
| Compress | 47 | 19 | 10 | 10 | 12 |
| Math | 103 | 27 | 10 | 10 | 12 |
| JacksonDatabind | 108 | 15 | 3 | 3 | 12 (JacksonDatabind_31: 8 `writeNumber` overloads) |
| Closure | 172 | 147 (stopped) | 5 | 4 | 5 |

- **Closure almost never passes the upstream filter:** 5 methods from 147 scanned bugs (4 bugs). Its trigger tests
  call helpers like `test("js in", "js out")`, so the focal method is rarely invoked by name
  (`focal_method_invoked`), and many focal methods are package-private. 141 of 147 bugs had no buggy record that is
  both invoked and public/protected. The coordinator stopped Closure after 147 checkouts because host disk dropped
  from ~102 GB to 62 GB; no other project was added (JacksonCore etc.).
- Like Gson_4 (6 methods) and Cli_1 in the old stratum, three new bugs are clusters: JacksonDatabind_31 (8), Time_3 (6),
  Jsoup_22 (6). They share one bug and one test class, so their outcomes are correlated.
- One Closure checkout failed twice and was skipped (logged). The checkouts of bugs without a kept method are still in
  the `d4jproj` volume (deleting them was denied by the permission system; see RESULTS.md).

The upstream notebooks run unchanged through `run/nb2py.py` with this folder's overrides: `gen_src.ovr` (only the
sampled bug; the output goes to `out/src/<bug>_<version>_draft.jsonl` instead of `data/prompts/<version>_source_data_draft.jsonl`)
and `unify.ovr` (inputs and the cell 28 output moved to new names). Cells kept: source data 0-4, 8, 75, 77; unify
0-9, 14-18, 20, 24, 27 (the dropped cells only write files under the old names or display a value; 10-13, 19 and 25
index `[0]` and crash on a single bug with no public method, Closure_46).

## Arms (each = the reused 78-method run + the same script and settings on the new methods)
| arm | 78 old methods (reused) | new methods (this folder) | `FILE_POST_FIX` (new) |
|---|---|---|---|
| Only Doc (paper's method) | baseline `unified_invoked_docstring_prompt` | `Docstring_Generation.ipynb` (cells as `run/pipeline.sh docstring_basic`) → Only Doc tests | `s150_onlydoc` |
| Advanced | baseline `unified_invoked_advanced_docstring_prompt` | `Advanced_Docstring_Generation.ipynb` (as `docstring_advanced`) → tests | `s150_adv` |
| Adv rerun (A/A) | m9 `m9_adv_rerun` | `m9.py gen adv_rerun` (`m9new.py`) → tests | `s150_rerun` |
| m9 concept | m9 `m9_concept` | `m9.py gen concept` → tests | `s150_concept` |
| m9 placebo | m9 `m9_placebo` | `m9.py gen placebo` → tests | `s150_placebo` |

- Docstring notebooks: `docstring.ovr` = `run/docstring.ovr` + the input (the new methods) and output (`*_s150new.jsonl`) moved.
- `m9new.py` imports `m9.py` unchanged and only repoints its module globals (`SRC`, `OUT`, `DOC_OUT`, budget).
- Test generation: `generate_prompt.ipynb` + `UT_Test_Generation.ipynb` with `run/prompt.ovr` / `run/testgen.ovr`
  unchanged, `WITH_CODE=0`, upstream's call without temperature, exactly `run/pipeline.sh gen_env`.
- Evaluation: `eval_parts.py` (copy of m9's; resumes after the transient ENOENT crashes; `NO_ADC=1`); glitched
  blocks (empty error report) are redone once per arm with `--redo`.
- All calls that compile or run LLM-written code have no credentials (`NO_ADC=1`).

## Cost logging and cap
`calllog.py` wraps the shim's `generate_content` for every notebook call (docstrings, test generation): tokens, USD
($0.30 / M in, $2.50 / M out), prompt sha1, finish reason → `out/llm_calls.jsonl`. The m9 path logs through m9's own
hook into `out/m9/llm_calls.jsonl`. Hard cap **$25** over both logs, checked before every call (`calllog.py`) and
before every method (`m9.gen`). Repetition loops (65,536-token completions) are kept as upstream (no max_tokens,
no re-ask) and listed with their cost by `analyze.py`.

## Concept labels for the new methods
`labels_new.py` applies m2's rules (`m2_concept_diag/labels.py`) to the new methods and dumps their in-method fix
hunks (`out/labels_rule_new.jsonl`). `manual_labels_new.json` holds my labels (C0-C8, m2's vocabulary and
conventions), read from those hunks; `checked_by_hand` marks the ones I read myself. Offline only.

## Reproduce (from `EvalAndMitigate/`; one stage at a time, poll the console)
```bash
python3 subset150/plan.py                     # -> out/plan.json (no checkout)
python3 subset150/calllog.py selftest
nohup bash subset150/run.sh sample  > subset150/out/sample.console 2>&1 &   # checkouts, upstream filters, quota
nohup bash subset150/run.sh final   > subset150/out/final.console 2>&1 &    # dataset files, manifest, rule labels, m9 leak check
nohup bash subset150/run.sh docs    > subset150/out/docs.console 2>&1 &     # 5 docstring sets for the new methods
nohup bash subset150/run.sh tests   > subset150/out/tests.console 2>&1 &    # 5 test generations
nohup bash subset150/run.sh evals   > subset150/out/evals.console 2>&1 &    # 5 evaluations (NO_ADC=1)
#   glitched blocks, once per arm: python3 subset150/eval_parts.py s150_<arm> --redo i j ...
bash subset150/run.sh analyze                 # -> out/analysis.txt
```

## Files
- `plan.py`, `sample.py`, `gen_src.ovr`, `unify.ovr`: sampling; `manifest.json`.
- `docstring.ovr`, `m9new.py`, `s150.sh` (container steps), `run.sh` (host stages), `calllog.py` (ledger + cap).
- `eval_parts.py`, `analyze.py`, `labels_new.py`, `manual_labels_new.json`.
- `out/`: `plan.json`, `sampling.jsonl`, `src/` (per-bug drafts), `nb/` (generated notebook scripts + logs),
  `m9/` (m9-path cache `docs_<arm>.jsonl`, `llm_calls.jsonl`, `prompts_check.txt`), `llm_calls.jsonl`,
  `s150_<arm>_parts.json`, consoles, `labels_rule_new.jsonl`, `analysis.txt`.
