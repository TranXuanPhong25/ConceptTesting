# m5_blind_concept_spec: code-blind Concept-Spec

## Method
m3 Concept-Spec wrote per-concept `input → expected` rules from the **buggy method body**, and the rules restated the
buggy behaviour (13 of 16 M-methods). Hypothesis: the spec copies the bug because the model sees the body. Here the
spec-generation prompt contains **no focal method body**. Everything else is m3: the same facets (C0 core logic +
C1-C8), the same JSON table and rule schema, the same parser and deterministic renderer (copied into `spec.py`), the
same re-ask policy, and the unchanged Only Doc test-generation pipeline (`WITH_CODE=0`).

1. **Prompt context** (`spec.build_prompt`). The upstream `PromptFormatter.apply_format_summarize(..., advanced_analysis=True)`
   prompt that m3 and Advanced Doc use, with its one body section ("// The following code is the method that you are
   going to summarize." + body) replaced by a declaration-only header:
   - the fully qualified signature and the method name (the same two lines the test-generation prompt has);
   - the declaration: modifiers, type parameters, return type, name, parameters and `throws`, taken with tree-sitter
     from the method node in the buggy class code (the text before the body block), e.g.
     `protected int findWrapPos(String text, int width, int startPos);`.
   The rest of the upstream context is unchanged: parameter names and classes, parameter-class and return-type
   constructors, return type, class name, class constructors, field declarations, other method signatures.
   `content:source_class_code_format` (which contains the body in 78/78 records) is used only to locate the method node,
   never put in the prompt. The class Javadoc (`content:source_class_docstring`) is **not** added: it is not in the
   upstream prompt either, so A differs from m3 by the body only, and B differs from A by the method Javadoc only.
2. **Instruction** (`spec.POSTFIX`). m3's Part 1 "critical analysis of the code" (logical mistakes, robustness
   omissions) is replaced by a contract analysis: (1) intended purpose from name, parameter names/types, return type and
   class context; (2) conventions and constraints (null, empty, boundaries, exceptions, formats) with their evidence and
   certainty, stating where the evidence does not determine the behaviour. Part 2 (facets, JSON format, rule schema) is
   m3's, minus the two lines about not quoting or narrating the code. "Unspecified" is encouraged more strongly than in
   m3: "prefer "unspecified" to an expectation that the evidence does not support".
3. **Arms**
   - **A `m5_blind_concept`**: no body, no Javadoc. The pure "remove the body" contrast against m3.
   - **B `m5_blind_concept_javadoc`**: A + the method's original Javadoc, shown under "// The original Javadoc comment of
     the method:" (or "(the method has no Javadoc comment)"), and a `javadoc` value for the rule `source` field. The
     Javadoc is re-extracted from the buggy class code: the `/** */` block comment that is the immediate previous
     sibling of the method node (tree-sitter). It matches the dataset's `source:source_method_docstring` on 75/78
     methods (whitespace/`*` normalised). The 3 others have no Javadoc: Cli_15 (the dataset field holds the
     constructor's Javadoc), Gson_12 (the field holds the line comment `// object`), Gson_8 (field empty too). A
     7-method sample was checked by hand against the class code (`out/javadoc.jsonl`, `out/javadoc_check.txt`).
     The Javadoc of the buggy version is used, never the fixed one.

Did the upstream prompts ever contain the method's original Javadoc? **No.** `apply_format_summarize` (basic and
advanced docstring generation, and m3 via the same function) and `apply_format_with_docstring` (test generation) never
read `source:source_method_docstring`, and the focal body field contains no comment preceding the method (0/78 bodies
contain `/**`). The notebooks only declare the key. So arm B is the first configuration in this replication whose
prompt contains developer-written method documentation.

Body-leak checks (`spec.body_leaks`): whitespace-normalised 40-char windows (stride 20) of the body after its
declaration. Every prompt and every rendered docstring is asserted to contain none, except windows that also occur in
the upstream non-body context (Gson_8: an anonymous class in the body overrides `newInstance`, whose signature is
listed under "Other methods"), and windows made only of words, spaces and commas. That last exception was added after
the first arm-B run stopped on the guard at Lang_63 (record 75): its rendered spec says "The duration components
(years, months, days, hours, minutes, seconds, milliseconds) are calculated …", which matched the window
`s, months, days, hours, minutes, seconds` of the body's call `format(tokens, years, months, days, hours, minutes,
seconds, milliseconds, padWithZeros)`. That is an English list of time units, not code, so it is a false positive; no
spec was changed or regenerated. With the tightened guard, all 78 prompts and rendered docstrings of both arms are
clean (re-checked; arm A had passed the stricter original guard already). No extracted Javadoc contains a body window.

Leakage: the patch, fixed version, trigger tests and `m2_concept_diag/manual_labels.json` are used only in `analyze.py`.

Controls: the matched control for A is m3 Concept-Spec itself (same schema, renderer, call budget and test pipeline;
only the body differs), and for B it is A (only the Javadoc differs). No separate placebo arm was run; m3's
placebo already measured the facet vocabulary against bug-irrelevant facets.

Prompt tuning: none. The prompt was fixed before the smoke run (Cli_32, Lang_20, Lang_40, the same 3 methods as m3's
smoke), and the smoke specs are reused in the full runs.

Evaluation crash handling: `eval_parts.py` is m4's copy (resume after the transient ENOENT crashes and after the
upstream `ZeroDivisionError` when the first method of a part compiles no test), with paths moved here and one fix.
m3/m4 counted a crashed part's last block as finished whenever it had counter lines. In arm B, ENOENT crashes also
left all-zero counter lines in the crashed block (idx 49, 50, 51, 59), so those four blocks were wrongly kept as
finished (0 tests). The fix: the last block counts as finished only if the console shows the `ZeroDivisionError` and
no `FileNotFoundError`, and the block has no "Skipping.". The four blocks were then re-evaluated with
`eval_parts.py m5_blind_concept_javadoc --redo 51 49 50 59` (part `m5_blind_concept_javadoc_redo1`), which
`analyze.py` uses in their place. Arm A was not affected (its only crash was the `ZeroDivisionError` after Cli_15).

## Files
- `spec.py`: prompt builder (tree-sitter declaration + Javadoc), spec generation, parser, renderer (container).
  `python3 m5_blind_concept_spec/spec.py selftest` (host) checks the parser/renderer/leak check;
  `spec.py javadoc` (container) writes `out/javadoc.jsonl` (declaration, extracted vs dataset Javadoc, leak checks, prompt sizes).
- `run_arm.sh`: spec generation → test generation → resumed evaluation for one arm.
- `eval_parts.py`: resumed evaluation (copy of m4's).
- `analyze.py`: all RESULTS.md numbers (host python, stdlib), output in `out/analysis.txt`; also `out/m_methods.txt`
  (M tests next to the spec rules, for the manual check).
- `out/specs_<arm>.jsonl`: per method `idx, id, method_signature, calls, temperature, prompt, reply, spec`.
- Doc files: `data/prompts/Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m5_blind_concept[_javadoc][_smoke].jsonl`.
- Completions / logs: `data/prompts/rq1/*m5_blind_concept*`, `data/rq1/logs/*m5_blind_concept*`,
  `data/rq1/results_test/chatgpt/*m5_*`; `run/out/{prompt,testgen,eval}_m5_*` are written by `run/pipeline.sh`.
- `out/<fpf>_parts.json`: which part log covers which methods (with notes on each crash).
- `out/spec_blind_concept_javadoc_run1_assert.console`: the first arm-B spec run, which made all 78 spec calls and
  stopped on the body-leak guard false positive (see above); the second run reused the cached specs (0 calls).
- `out/smoke_*.console`: smoke spec generation and test generation + evaluation.

## Reproduce (from `EvalAndMitigate/`)
```bash
python3 m5_blind_concept_spec/spec.py selftest
bash run/dock.sh -- python3 m5_blind_concept_spec/spec.py javadoc
# smoke (3 methods), both arms
for a in blind_concept blind_concept_javadoc; do
  bash run/dock.sh -- python3 m5_blind_concept_spec/spec.py $a 3 33 53
  DOC_FILE=Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m5_${a}_smoke.jsonl WITH_CODE=0 \
    FILE_POST_FIX=m5_${a}_smoke bash run/dock.sh gen_env eval_env
done
# full arms, strictly sequentially
bash m5_blind_concept_spec/run_arm.sh blind_concept
bash m5_blind_concept_spec/run_arm.sh blind_concept_javadoc
# arm B: re-evaluate the 4 blocks that ENOENT crashes left with all-zero counters (see above)
python3 m5_blind_concept_spec/eval_parts.py m5_blind_concept_javadoc --redo 51 49 50 59
python3 m5_blind_concept_spec/analyze.py > m5_blind_concept_spec/out/analysis.txt
```
