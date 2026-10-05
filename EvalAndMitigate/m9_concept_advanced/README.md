# m9_concept_advanced: a concept checklist inside the Advanced prompt's bug hunt (Part 1)

## Question
Advanced Doc is the best config (RESULTS.md). Our untested guess is that its Part 2 helps: the model writes a corrected
implementation first and then documents that. m3 replaced Parts 2 and 3 and copied the bug, so the open question is
whether a concept checklist helps the bug-hunting step when everything else stays as upstream.

## Method
The upstream Advanced docstring prompt is kept **verbatim**, all three parts. One item is inserted into Part 1, right
after "2. Robustness Omissions" and before "Your analysis should be very detailed…". The docstring is still written
from the Part 2 corrected implementation, as upstream. Three arms run through the same script (`m9.py`). They have the
same call, settings and parsing; only the inserted item differs:

| arm (`FILE_POST_FIX`) | inserted item |
|---|---|
| `m9_adv_rerun` | none (A/A re-run of Advanced Doc; controls for script and run-to-run noise) |
| `m9_concept` | `3. **Checklist Review:**` + C1 null · C2 empty/blank · C3 boundary/index/length · C4 error contract · C5 escaping/normalisation/format · C6 numeric · C7 characters/locale/unicode · C8 state/mutation; for each, the finding or "No issues found." |
| `m9_placebo` | the same header and format with m3's eight bug-irrelevant facets (P1 naming · P2 documentation · P3 performance · P4 thread-safety · P5 logging · P6 API stability · P7 readability · P8 dependencies) |

The facet names and one-line definitions are m3's (`m3_concept_spec/spec.py` `FACETS`, C0 dropped), imported, not
copied. The concept item has 1,404 chars / 200 words; the placebo item has 1,256 chars / 203 words. Each has 8 facets.
The full texts are in `out/prompts_check.txt`.

**Faithfulness to `Advanced_Docstring_Generation.ipynb`** (cells 16 and 20, the ones `run/pipeline.sh docstring_advanced` runs):
- Prompt: `PromptFormatter().apply_format_summarize(record, 'chatgpt', strategy='generation', formatting='comment',
  ignore_feature='full', project_name=bug_id, advanced_analysis=True, is_base=True, base_cot=True, corrected_code=True)`,
  as in the notebook. The restored formatter ignores the last three flags (see its `ponytail:` comment). The
  `adv_rerun` prompt is asserted equal to the formatter output. Each concept/placebo prompt is asserted equal to it once
  the static item is removed.
- Call: `openai_client.chat.completions.create(model="gpt-4.1", messages=[user prompt], temperature=0)`, through
  `run/gemini_shim.py`, exactly what the notebook passes. That means T=0 and **no max_tokens**. The shim gives
  gemini-2.5-flash on Vertex, location global, thinking off (`THINKING_BUDGET` unset → 0). These are the same
  settings that produced the Advanced Doc baseline docstrings. The completion is `.strip()`ped as in the notebook.
  There is one call per method and arm, sequential (concurrency 1). The shim backs off on 429 (8 attempts, up to 60 s
  apart); like the notebook, `m9.py` retries a failed call, here up to 10 times, 60 s apart. There are no re-asks on
  content.
- Docstring: the notebook's own parsing code (cell 16, identical to the cell 20 loop; checked at run time) runs via
  `exec`. It takes the last `/** … */` block; if there is none, the last ```java block; if neither, the whole text.
- Records: the source record plus `generated_docstring`, the same format as
  `data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_advanced_docstring_base_cot_code.jsonl`. They
  also carry the full completion in `m9_completion`, which `run/prompt.ovr` ignores.
- Tests and evaluation: the unchanged pipeline. `gen_env` uses `WITH_CODE=0`, the Only Doc / Advanced Doc
  test-generation prompt, and upstream's call without a temperature, so every m9 arm also matches the baseline's
  test-generation settings. The evaluation is `eval_parts.py`, a copy of m7's: it resumes after crashes and always
  sets `NO_ADC=1`.

**Leakage.** The inserted text is static and has no per-method content. `m9.py prompts` builds all 234 prompts and
asserts:
- no m9 prompt contains a fixed-side patch line or a trigger test (class or method) name that is not already in the
  upstream prompt;
- each prompt differs from upstream only by the item.

Result: 0 leaks. The 26 hits inherited from the upstream prompt are fixed-side lines that also occur unchanged in the
buggy code (moved lines, `return false;`); the Advanced Doc baseline has them too. The test-generation prompt contains
only the docstring. `analyze.py` reports docstrings that quote ≥40-char windows of the focal body (m5's `body_leaks`),
as upstream Advanced docstrings sometimes do (3/78 in the baseline).

## Mechanism (offline, no LLM): `fixrate.py`
For each arm and method, the first ```java block that declares the focal method (same name and arity) is taken as
Part 2:
1. It replaces the focal method in a **scratch copy** of the buggy source file. The byte span comes from m8's
   `out/mutants.jsonl`. New helper members of the block (names/arity not already declared in the file) and missing
   imports are added; non-ASCII becomes `\u` escapes.
2. The file is compiled alone against the checkout's `cp.test`.
3. The bug's trigger tests are run on it.

Fix = it compiles and all trigger tests pass. Per bug: the Part 2s of all its focal methods are substituted together
(11 bugs have 2-6 focal methods, always in one file).

m8's harness is reused read-only: `phase0.py` (`compile_file`, `run_tests`, `export_cp`, `load_env`), `M8Runner.java`,
`out/env.json` (classpaths, trigger tests) and the `mutate.py` parser. m8's `out/phase0_base.json` shows that every
trigger test fails on the recompiled buggy original and passes on the fixed checkout, for all 78 methods.

`fixrate.py check` validates the harness first: substituting the fixed checkout's focal methods must fix the bug
(except where the patch also changes other code), and substituting the buggy methods must not.

Everything runs in `dock9.sh`, a copy of m8's final sandbox (outputs go through a top-level `/m9out` mount): no credentials, no network, the repo and the d4jproj checkouts
read-only, scratch in the `m9scratch` volume. Each run ends by asserting `git diff --quiet HEAD -- <main src dir>` on
all 120 shared checkouts. Trigger tests and the fixed version are used only here.

`analyze.py` then reports:
- the fix rate per arm, with exact McNemar for concept vs placebo and concept vs rerun, per method and per bug;
- ≥1 E and ≥1 M among methods with a fixed vs a not-fixed Part 2;
- whether Part 1 names the bug's concept (`m2_concept_diag/manual_labels.json`). For the concept arm this is the
  checklist flag of the labelled concept; for all arms it is a keyword proxy on items 1-2, which is weak and saturates
  on null/exception.

## Pre-registered metrics (`analyze.py`)
- Scope: the clean intersection with Advanced Doc.
- For every arm: M / E / FP and %, red-precision, ≥1 M, ≥1 E.
- **Primary:** exact McNemar on ≥1 E and on ≥1 M, concept vs placebo.
- Secondary: concept vs rerun, and concept vs the original Advanced Doc run.
- A/A noise: rerun vs Advanced Doc, with the discordant methods listed.
- Sensitivity: everything again without Gson_4 and Cli_1.
- Calls and cost per arm.

## Budget and security
- Hard cap: $5 of Vertex spend.
  - Every docstring API attempt is logged to `out/llm_calls.jsonl` with its tokens and USD. The hook on the shim's
    genai client records the `usage_metadata` that the shim drops. Price: $0.30 / M input and $2.50 / M output tokens.
  - `m9.py gen` stops above $3.90 of docstring spend, or when the total reaches the cap. This was $2.50 in phase A;
    it was raised in phase B because 65,536-token repetition loops cost about $0.165 each.
  - The shim does not expose test-generation tokens, so `m9.py cost` estimates them from the m9 rq1 files. Digits
    count as one token each and other characters at 4 per token; this is within 4% of `count_tokens` on the baseline
    (`out/count_tokens_baseline_testgen.json`).
  - `run.sh` checks the remaining budget before each test generation, reserving $1.1 per arm.
- Actual spend: docstrings $3.54. Test generation measured on the baseline is about $0.97 per arm. See RESULTS.md.
- Credentials and code execution:
  - LLM calls run in `run/dock.sh`, with credentials.
  - Everything that compiles or runs LLM-written code has no credentials: evaluations via `eval_parts.py`
    (`NO_ADC=1`), Part 2 code via `dock9.sh`.
- arm64 image `evalmitigate`.

## Files
- `m9.py`: the prompts, leak check (`prompts`), generation (`gen`), `selftest` and spend ledger (`cost`).
- `fixrate.py`: the Part 2 fix rate (`selftest`, `check`, `run <arm>`).
- `dock9.sh`: the sandbox.
- `eval_parts.py`: copy of m7's, paths moved.
- `analyze.py`: every RESULTS.md number.
- `run.sh`: the phase B stages.
- `out/`:
  - `prompts_check.txt`;
  - `docs_<arm>.jsonl`: per method `idx, id, method_signature, arm, is_public, prompt, completion, generated_docstring`; also the resume cache;
  - `llm_calls.jsonl`;
  - `fixrate_check.json`, `fixrate_<arm>.json`;
  - `m9_<arm>_parts.json`;
  - consoles, `analysis.txt`.
- Outside this folder, all new files with the `m9_` name:
  - `data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m9_<arm>[_smoke].jsonl`;
  - `data/prompts/rq1/*m9_*`;
  - `data/rq1/logs/*m9_*`;
  - `data/rq1/results_test/chatgpt/*m9_*`;
  - the pipeline's `run/out/{prompt,testgen,eval}_m9_*`.

## Reproduce (from `EvalAndMitigate/`)
```bash
# phase A (no LLM, no evaluation)
python3 m9_concept_advanced/m9.py selftest
NO_ADC=1 bash run/dock.sh -- python3 -W ignore m9_concept_advanced/m9.py prompts      # leak check + sizes
bash m9_concept_advanced/dock9.sh python3 -W ignore m9_concept_advanced/fixrate.py selftest
# phase B, strictly one stage at a time (each: poll the console until it ends)
nohup bash m9_concept_advanced/run.sh smoke   > m9_concept_advanced/out/smoke.console 2>&1 &   # idx 3 33 53, all arms
nohup bash m9_concept_advanced/run.sh docs    > m9_concept_advanced/out/docs.console 2>&1 &    # 3 x 78 calls (smoke reused)
nohup bash m9_concept_advanced/run.sh tests   > m9_concept_advanced/out/tests.console 2>&1 &
nohup bash m9_concept_advanced/run.sh evals   > m9_concept_advanced/out/evals.console 2>&1 &
#   glitched blocks (empty error report), once per arm: python3 m9_concept_advanced/eval_parts.py m9_<arm> --redo i j ...
nohup bash m9_concept_advanced/run.sh fixrate > m9_concept_advanced/out/fixrate.console 2>&1 &
bash m9_concept_advanced/run.sh analyze                                                       # -> out/analysis.txt
```
