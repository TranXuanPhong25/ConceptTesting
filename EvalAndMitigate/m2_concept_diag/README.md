# m2_concept_diag: bug-concept labels from the fixing patch, as a diagnostic

No test generation and no Docker evaluation. This is offline analysis only. The fixing patch, the fixed version and the
trigger tests are used here, and only here. They never enter a generation prompt.

## Method
1. `labels.py` (container, stdlib only) assigns rule-based bug-concept labels (C0-C8 from `run/METHODS_BRIEF.md`) to
   each of the 78 focal methods, using the part of the fixing patch that lies inside the method.
   - Direction: the Defects4J patches in `data/d4j2_fix_info/<Bug>/buggy_fix_info.json` go **fixed → buggy**. Their `+`
     side equals the buggy checkout, so the script inverts them. `-` = removed by the fix (buggy), `+` = added by the fix.
   - Scope: the method is located in `d4j_proj_base/<Bug>/buggy/<file>` by matching the stripped line sequence of
     `source:source_method_code_format` (78/78 found). Hunk lines are mapped with the buggy-side line numbers. 77/78
     methods contain part of the patch. Lang_30 `indexOfAny(String, String[])` does not, so it falls back to the
     whole patch (`scope: whole_patch`).
   - Rules (`RULES` in `labels.py`): a concept fires when the multiset of matched snippets of one of its regexes
     differs between the removed and the added code lines. In other words, the fix inserts, deletes or changes that
     construct. Comments are dropped and generics collapsed before matching.
     C1 null comparisons/NPE, C2 isEmpty/isBlank/`length()==0`/`""`, C3 relational operators, ±1, `++/--`,
     length/size, charAt/substring/indexOf, array index, C4 throw/catch/try/`*Exception`, C5 escape/quote/format/
     replace/trim, C6 long/double/BigDecimal, MAX_VALUE, casts, numeric literals, Math.*, NaN, C7 char/Character./
     codePoint/Locale/surrogate, char literals, toLower/UpperCase, C8 `this.f =`, class-field mutation, clone/copy/
     reset/synchronized. C0 if none fire. The evidence (pattern, counts, matched lines) is stored per concept.
   - `manual_labels.json` holds my own labels for all 78 methods (the concept the bug concerns, read from the
     in-method diff plus the trigger-test names and messages), each with a one-line note. The rules were **not**
     tuned on this reading (rule precision below is for the first rule version).
2. `judge.py` (container) asks Gemini 2.5 Flash (thinking off, temperature 0, `run/gemini_shim.py`) for each method and
   docstring set (basic `..._with_docstring.jsonl`, advanced `..._with_advanced_docstring_base_cot_code.jsonl`)
   whether the docstring, for the behaviour the fix changes, describes BUGGY, FIXED or NEITHER, with a quote.
   The prompt shows the in-method hunks (±3 lines of context), the trigger-test names and messages, and the docstring.
   `manual_judge.json` holds my verdicts on 26 cases (every 6th method × both sets), used to validate the judge.
3. `analyze.py` (host) validates both steps and joins them with per-method clean outcomes of the three baselines and the
   two m1 arms (parsed with `m1_test_review/analyze.py` `load`, glitched methods excluded per config).

## Outputs
- `labels.jsonl`: one record per method in dataset order: `idx, project, bug, sig, located, patch_in_method, scope,
  concepts` (rule labels), `evidence`, `method_hunk` (in-method hunk lines, fix direction, with context),
  `changed_functions`. Manual labels: `manual_labels.json` (key = `idx`).
- `judge.jsonl`: `idx, project, sig, docset, verdict, quote, reason, calls, raw`.
- `RESULTS.md`: numbers. `out/analysis.txt` has the full output of `analyze.py`.

## Reproduce (from `EvalAndMitigate/`)
```
bash run/dock.sh -- python3 m2_concept_diag/labels.py       # deterministic; needs the d4jproj volume
bash run/dock.sh -- python3 m2_concept_diag/judge.py        # 156 judgements, resumable (delete judge.jsonl to redo)
python3 m2_concept_diag/analyze.py > m2_concept_diag/out/analysis.txt
```
