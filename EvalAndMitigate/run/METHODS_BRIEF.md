# Brief for the m*_ method folders (read fully before starting)

We replicate "Evaluating and Mitigating the Misguidance Effect of Buggy Code in LLM-Generated Unit Tests"
(Zhao et al., ISSTA 2026) and try concept-based improvements inspired by ConceptCoder (arXiv 2603.23470:
models first recognise tool-computable, human-understandable "concepts", then reason with them).

Host repo: `/Users/mac/Documents/py-toy/EvalAndMitigate` (mounted at `/repo` in the container).
Each method lives in its own folder `EvalAndMitigate/m<N>_<name>/`. Touch nothing outside your folder
except writing new files under `data/prompts/` and `data/prompts/rq1/` with your own name prefix.

## Dataset (fixed, already built)
- `data/prompts/buggy_source_data_unified_invoked.jsonl`: 78 focal methods, 60 Defects4J bugs
  (Lang 51, Gson 12, Codec 7, Cli 5, Csv 3). Key fields: `extra:project_name` (e.g. `Lang_4_buggy`),
  `source:source_method_code_format` (buggy method body), `source:source_method_signature`,
  `content:source_class_code_format`, `invoking_test_cases`.
- Docstrings already generated with Gemini 2.5 Flash (thinking off), same records + `generated_docstring`:
  - basic: `data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_docstring.jsonl`
  - advanced: `data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_advanced_docstring_base_cot_code.jsonl`
- Defects4J fix metadata (patch diff + GumTree-style AST ops, trigger tests): `data/d4j2_fix_info/<Bug>/buggy_fix_info.json`
  (`fixing_changes[].diff`, `fixing_changes[].operations`). CAREFUL: these diffs run fixed → buggy (the `+` side is
  the buggy code). Hand-validated bug-concept labels for all 78 methods: `m2_concept_diag/manual_labels.json`
  (rule labels + evidence: `m2_concept_diag/labels.jsonl`). Offline use only (they derive from the patch).

## Existing configurations (baselines) and their files
Files are `data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_<FILE_POST_FIX>[_with_completion].jsonl`;
completion records have `id`, `content` (the prompt), `completion` (markdown with a ```java block), `method_signature`.

| config | FILE_POST_FIX | prompt contents |
|---|---|---|
| Doc W/ Code | `unified_invoked_docstring_code_prompt` | buggy code + basic docstring |
| Only Doc (paper's method) | `unified_invoked_docstring_prompt` | basic docstring only |
| Advanced Doc | `unified_invoked_advanced_docstring_prompt` | advanced docstring only |

Baseline numbers: see `run/BASELINES.md`.

## How to run (only through Docker; never run two evaluations at once)
- Generate tests from a docstring file you produced (same record format, your `generated_docstring`):
  `DOC_FILE=<file in data/prompts> WITH_CODE=0 FILE_POST_FIX=<m<N>_...> bash run/dock.sh gen_env eval_env`
- Evaluate a `_with_completion.jsonl` you produced yourself: `FILE_POST_FIX=<m<N>_...> bash run/dock.sh eval_env`
- Run any script in the container: `bash run/dock.sh -- python3 m<N>_<name>/your_script.py`
  (Python 3.12 venv with tree-sitter 0.21.3, javalang, numpy, google-genai; Defects4J on PATH;
  `from data.configuration import JAVA_LANGUAGE` gives the tree-sitter Java grammar).
- LLM calls: `from gemini_shim import GeminiChat` (add `/repo/run` to sys.path), then
  `GeminiChat().chat.completions.create(messages=[{"role":"user","content":p}], temperature=0)`.
  Model gemini-2.5-flash via Vertex, thinking off (`THINKING_BUDGET=0`), retries on 429 built in.
  Host python has no google-genai: run LLM scripts in the container.
- Metrics: `python3 run/summarize.py data/rq1/logs/<the highest-numbered *_<FILE_POST_FIX>_log_N.log>`
  prints M/E/FP counts and %, methods with >=1 M / >=1 E. Compile rate etc. in
  `data/rq1/results_test/chatgpt/Gemini-2-5-flash_buggy_<FILE_POST_FIX>_gen_test_results.json`.
  Use the "reported" counters (summarize.py does); the post-repair counters delete failing tests.
- Timing: test generation ~10-15 min, evaluation ~20 min per 78 methods. For a smoke test, write a
  `_with_completion.jsonl` with 2-3 records under a `..._smoke` FILE_POST_FIX and evaluate that first.
- Evaluations crash fairly often on transient ENOENT errors for checkout dirs that exist (cause unknown, likely Docker
  Desktop mount flakiness). Do not rerun all 78 methods: reuse the resume approach of `m1_test_review/eval_parts.py`
  (copy it into your folder and adapt paths); `m1_test_review/analyze.py` shows how to merge the part logs and recover
  per-test outcomes (failing-test lists per version) from a log.
- Score with the "clean" line of `run/summarize.py` (see run/BASELINES.md for why), compare arms on the intersection
  of clean methods.
- Never edit a shell script while a container is executing it (bash reads scripts incrementally).

## Definitions
M (misguided) = passes buggy, fails fixed. E (effective) = passes fixed, fails buggy.
FP = fails on both. TN = passes both. Percentages are over compiled tests.
Red-test precision = E / (E + FP): among tests that fail on the buggy (i.e. current) code, the share that are
real bug catches rather than spurious. In practice only the current code exists, so this is what a developer
sees; report it.

Shared concept vocabulary (use these ids so methods are comparable):
C1 null input · C2 empty/blank input · C3 boundary/index/length (off-by-one) · C4 error contract
(exception type / error return) · C5 escaping/normalisation/format · C6 numeric range/overflow/precision ·
C7 characters/locale/unicode · C8 state/mutation/idempotence. Add `C0 other logic` for anything else.

## Rules
1. Leakage: the fixed version, the patch, trigger tests and fix metadata must never enter any prompt.
   They may be used only for offline analysis/labels and for evaluation.
2. The test-generation prompt must not contain the focal method body (the paper's principle), unless your
   method explicitly compares against that.
3. Every method has at least one control arm (placebo or random baseline) with the same LLM call budget,
   and reports call counts per arm.
4. Only one Docker evaluation at a time. You are the only agent running now; still run your arms sequentially.
5. Do not modify upstream files or `run/`; if shared infra truly needs a change, keep it additive and
   document it in your RESULTS.md. No git commits. Do not delete others' outputs.
6. Keep code small and in the repo's style (plain Python, stdlib first).
7. Deliverables in your folder: `README.md` (method, how to reproduce, exact commands) and `RESULTS.md`
   (table of your arms next to the baselines, method-level counts, exact McNemar on methods with >=1 E
   and on methods with >=1 M vs the most relevant baseline, call counts, honest caveats: n=78 is small).
