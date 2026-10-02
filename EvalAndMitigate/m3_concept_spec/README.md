# m3_concept_spec: Concept-Spec (concepts as a mandatory intermediate specification)

## Method
The free-text docstring of Only Doc / Advanced Doc is replaced by a specification that is structured by the shared
concept vocabulary, so the spec has to take a position on every bug-relevant behaviour class instead of silently
skipping it (m1 found docstrings are silent exactly on null/empty/unstated-mode cases).

1. **Spec generation** (one Gemini 2.5 Flash call per focal method, thinking off, temperature 0). The prompt is the
   Advanced Doc prompt: same buggy-code context from `PromptFormatter.apply_format_summarize(..., advanced_analysis=True)`,
   same Part 1 critical analysis (logical mistakes, robustness omissions). Only the instruction postfix is replaced:
   instead of a corrected implementation + free-text docstring, the model outputs a JSON table with `purpose` and one
   key per facet: C0 core logic plus C1 null · C2 empty/blank · C3 boundary/index/length · C4 error contract ·
   C5 escaping/normalisation/format · C6 numeric · C7 characters/locale/unicode · C8 state/mutation. Each facet is
   `"not applicable"` or a list of rules `{input (class + concrete examples), expected (return value / exception
   type / state, or "unspecified"), source: name-context | type | framework | assumed}`. "Unspecified" is explicitly
   allowed and encouraged; the model is told not to quote or narrate the implementation.
2. **Rendering** (deterministic Python, `spec.render`): Javadoc comment with the purpose line, one section per facet
   listing `input → expected`, and a final `Unspecified (do not assume):` section. Not-applicable facets are omitted;
   the `source` field is kept in the JSON only. The result goes into `generated_docstring` of a copy of the source
   records, and tests are generated and evaluated with the unchanged Only Doc pipeline (`WITH_CODE=0`, same
   test-generation prompt; only the docstring content differs).
3. **Placebo arm** `m3_concept_placebo`: identical prompt skeleton, JSON format, parser and renderer; C0 core logic is
   kept, and C1-C8 are replaced by eight bug-irrelevant facets with equally worded definitions (P1 naming,
   P2 documentation, P3 performance, P4 thread-safety, P5 logging, P6 API stability, P7 readability, P8 dependencies).

Re-asks: a reply without a parsable JSON table is re-asked (at T=0 a re-ask would repeat the same reply, so re-asks
use T=0.5; a second run over cached failures uses T=1.0). All failures were Gemini repetition loops
(`bbbb…`, `0000…`) inside the analysis; `max_tokens=10000` caps them. Calls per method are logged.

Evaluation crash handling: the upstream evaluator crashes with `ZeroDivisionError` (`reported_passed_on_fixed /
test_compiled`) right after a finished block while the *cumulative* compiled-test count is still 0, i.e. when the
first evaluated method has no compiling test (Cli_15 in the Concept-Spec arm). `eval_parts.py` (otherwise a copy of
m1's) therefore counts a crashed part's last block as finished when its counter lines ("Total test generated") were
written, and resumes at the next method. Record order and `run/` are unchanged. Blocks cut by the transient ENOENT
crash have no counter lines and are re-run as before.

Prompt tuning: one round, on the 3 smoke methods (Cli_32, Lang_20, Lang_40) of the Concept-Spec arm, before any
evaluation: an explicit "state outcomes as a caller would observe them; do not mention the code's variables or
steps" line was added because the first version justified outcomes by the code ("due to text.charAt(pos)"). The
first-version replies are kept in `out/smoke_v1_specs_spec.jsonl`. The renderer was fixed twice before the full runs
(whitespace inside examples was collapsed; `"expected": ""` was read as unspecified instead of the empty string).

Leakage: prompts contain only the buggy-code context the docstring prompts already use. The patch, fixed version,
trigger tests and `m2_concept_diag/manual_labels.json` are used only in `analyze.py`.

## Files
- `spec.py`: spec generation + parser + renderer (container). `python3 m3_concept_spec/spec.py selftest` checks parser/renderer.
- `run_arm.sh`: spec generation → test generation → resumed evaluation for one arm.
- `eval_parts.py`: copy of `m1_test_review/eval_parts.py` with paths moved to this folder (resume after evaluator crashes).
- `analyze.py`: all RESULTS.md numbers (host python, stdlib), output in `out/analysis.txt`.
- `out/specs_spec.jsonl`, `out/specs_placebo.jsonl`: per method `idx, id, method_signature, calls, temperature, reply,
  spec` (spec = parsed JSON table: `purpose`, facet keys → rules or "not applicable", `missing_keys`). Reused by the next method.
- Docstring files: `data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m3_concept_{spec,placebo}.jsonl`.
- Completions / logs: `data/prompts/rq1/*m3_concept_{spec,placebo}*`, `data/rq1/logs/*m3_concept_{spec,placebo}*`,
  `data/rq1/results_test/chatgpt/*m3_concept_*`. The pipeline's own `run/out/{prompt,testgen,eval}_m3_concept_*` files
  are written by `run/pipeline.sh`, not by hand.
- `out/m3_concept_spec_parts.json`, `out/m3_concept_placebo_parts.json`: which part log covers which methods.
  `out/crashed_m3_concept_spec_part2_log_1.log` is an unused crashed attempt (see RESULTS caveats).

## Reproduce (from `EvalAndMitigate/`)
```bash
python3 m3_concept_spec/spec.py selftest
# smoke (3 methods)
bash run/dock.sh -- python3 m3_concept_spec/spec.py spec 3 33 53
DOC_FILE=Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m3_concept_spec_smoke.jsonl WITH_CODE=0 \
  FILE_POST_FIX=m3_concept_spec_smoke bash run/dock.sh gen_env eval_env
# full arms, sequentially
bash m3_concept_spec/run_arm.sh spec
bash m3_concept_spec/run_arm.sh placebo
python3 m3_concept_spec/analyze.py > m3_concept_spec/out/analysis.txt
```
