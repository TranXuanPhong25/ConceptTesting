# m4_concept_inputs: concept-guided inputs, Advanced docstring as the only oracle

## Method
m3 showed that the per-concept `input → expected` rules (written from the buggy code) are good input generators but
poor oracles: their expected values mostly restate the buggy behaviour. Here the concept analysis only says **which
inputs to exercise**. The Advanced docstring stays the only behavioural specification.

1. **Input lists** (`inputs.py`, deterministic Python, no LLM). For each method, m3's spec table
   (`m3_concept_spec/out/specs_spec.jsonl`) is reduced to its input side:
   - Only the `input` field of each rule is used. The `expected` field is never read.
   - Parentheticals that contain outcome or behaviour wording are removed. Any item that still contains such wording
     is dropped whole. The wording list (`OUTCOME` in `inputs.py`) covers return/throw/exception/error/result/expect/
     should/must/will/would/fail/handle/ignore/treat/behaviour/produce/assume/convert/accept/allow/reject/truncate/
     caught…, "does not/never/always modify…", and arrows (`→ -> =>`). "valid"/"invalid" are kept as input-class
     labels. This drops 101 of 1753 concept rules (5.8%; placebo 221 of 2030, 10.9%), e.g. "An IOException occurs
     during writing" or "obj.toString() returns null", and trims a parenthetical from 16 more (placebo 8).
   - Duplicates are removed, also across facets (C1 "b is null" and C4 "b is null" count once).
   - **Cap: 12 items per method**, picked round-robin over the facets in the order C1…C8, C0. Every non-empty facet
     gets one item before any facet gets a second. Why 12: the generator writes about 15-17 tests per method, and
     after stripping and de-duplication the concept tables still hold a median of 18 items (min 4). 12 keeps the appended section
     (median 1.07k chars) at about the size of the Advanced docstring itself (median 1.15k).
   - Items are listed under neutral facet labels ("null inputs", "boundaries, indexes, lengths", "invalid or unusual
     inputs", …) and never with the concept's expected behaviour.
2. **Arm `m4_concept_inputs`**: the Advanced docstring records, with `generated_docstring` = the Advanced docstring
   byte-for-byte unchanged + an appended `//` comment section:
   ```
   // Input classes to exercise (derived from a concept checklist; expected results are intentionally not given - derive them from the specification above):
   // - null inputs: text = null, width = 10, startPos = 0
   // - boundaries, indexes, lengths: text = 'abc', width = 3, startPos = 0
   // ...
   ```
   `//` lines match the style of the rest of the test-generation prompt ("// The full method signature is: …").
   Tests are generated with the unchanged pipeline (`gen_env`, `WITH_CODE=0`, so no focal body) and evaluated with
   the resumed evaluation.
3. **Placebo arm `m4_placebo_inputs`**: identical header, format and stripping. The items come from the same
   method's placebo spec (`m3_concept_spec/out/specs_placebo.jsonl`: C0 core logic + P1-P8 naming, documentation,
   performance, thread-safety, logging, API stability, readability, dependencies). The number of items is matched per
   method: the same total (872 in both arms), and the same number of C0 items where the placebo's C0 has enough
   (C0 129 vs 122 items; P items fill the gap).
   This separates "bug-relevant input classes" from "any extra input list of the same length".

No abstain or "skip what is unstated" instruction is added (m1 showed that it destroys E).

Leakage: the only inputs are m3's spec tables (built from the buggy-code context that the Advanced docstring prompt
already uses) and the Advanced docstring. The patch, fixed version, trigger tests and `m2_concept_diag/manual_labels.json`
are used only in `analyze.py`.

Evaluation crash handling: `eval_parts.py` is a copy of `m3_concept_spec/eval_parts.py` with paths moved here. It
resumes after the transient ENOENT crashes and after the upstream `ZeroDivisionError` that happens when the first
method of a part compiles no test.

## Files
- `inputs.py`: builds both doc files and `out/items_{concept,placebo}.jsonl` (the selected items per method, with
  the section length). `python3 m4_concept_inputs/inputs.py selftest` checks the stripping on examples and on all
  78 methods of both arms: no outcome wording survives, totals match, and the Advanced docstring is a byte-exact prefix.
- `out/sample_check.txt`: both arms' sections for a random sample of 10 methods (seed 4). I read these by hand for
  outcome wording (see RESULTS).
- `run_arm.sh`: test generation → resumed evaluation for one arm.
- `eval_parts.py`: resumed evaluation (copy of m3's).
- `analyze.py`: all RESULTS.md numbers (host python, stdlib). Output in `out/analysis.txt`.
- Doc files: `data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m4_{concept,placebo}_inputs[_smoke].jsonl`.
- Completions / logs: `data/prompts/rq1/*m4_{concept,placebo}_inputs*`, `data/rq1/logs/*m4_{concept,placebo}_inputs*`,
  `data/rq1/results_test/chatgpt/*m4_*`. `run/out/{prompt,testgen,eval}_m4_*` are written by `run/pipeline.sh`.
- `out/<arm>_parts.json`: which part log covers which methods.

## Reproduce (from `EvalAndMitigate/`)
```bash
python3 m4_concept_inputs/inputs.py selftest
python3 m4_concept_inputs/inputs.py            # full doc files (both arms)
python3 m4_concept_inputs/inputs.py 3 33 53    # smoke doc files (Cli_32, Lang_20, Lang_40)
DOC_FILE=Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m4_concept_inputs_smoke.jsonl WITH_CODE=0 \
  FILE_POST_FIX=m4_concept_inputs_smoke bash run/dock.sh gen_env eval_env
bash m4_concept_inputs/run_arm.sh concept      # then, sequentially:
bash m4_concept_inputs/run_arm.sh placebo
python3 m4_concept_inputs/analyze.py > m4_concept_inputs/out/analysis.txt
```
