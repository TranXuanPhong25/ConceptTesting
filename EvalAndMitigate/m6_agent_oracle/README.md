# m6_agent_oracle: an answering agent in place of the human

## Question
When a test writer meets an ambiguous input ("what should `join(arr, ',', -1, 2)` do?"), a human would normally answer.
Can another agent answer instead? Earlier evidence: a spec written from the buggy body copies the bug (m3: methods with
≥1 M 3 → 16 vs Advanced Doc); hiding the body halves that (m5 A: 9), and adding the method's own Javadoc brings it back
to the baseline (m5 B: 3). Hypothesis: an answering agent helps only if it never sees the focal body and has to cite
independent evidence; one that reads the body copies the bug.

## Method (question → independent answer → clarified spec → tests)
All LLM calls: gemini-2.5-flash, thinking off, temperature 0 (re-asks only for unparsable replies, at T=0.5).

1. **Questions** (`oracle.py questions`, one call per method, shared by both arms). The upstream Advanced docstring
   prompt (`apply_format_summarize(..., advanced_analysis=True)`, so the buggy body and the same context), with its
   Part 1 "Critical Analysis" kept verbatim and Parts 2-3 replaced by: at most 6 neutral questions for the author about
   intended behaviour on ambiguous or bug-prone inputs, each with one concrete input, JSON
   `{id, concept (C0-C8), input, question}`. A deterministic guard (`question_issues`) rejects a question that
   - contains a 40-char window of the focal body (m5's `body_leaks`, copied unchanged);
   - uses wording that states or hints at the code (`WORDING`: currently, as implemented, implementation, the code /
     loop / condition / check, instead, still, bug, incorrect(ly), wrong, "the method returns/throws/…", …);
   - names an identifier that occurs in the focal body but nowhere in the blind evidence pack (camelCase or
     snake_case tokens; `*Exception`/`*Error` names are allowed).
   If any question is rejected, the method is re-asked once with the rejected questions and reasons appended; the
   attempt with more accepted questions is used and rejected questions are dropped.
2. **Evidence pack** (`oracle.py evidence`, container, no LLM), built from the buggy checkout in the `d4jproj` volume:
   fully qualified signature and declaration; the method's original Javadoc (m5's re-extraction,
   `m5_blind_concept_spec/out/javadoc.jsonl`); the class Javadoc (`content:source_class_docstring`); constructors,
   fields and other method signatures (the dataset's lists, deduplicated; the class code field is never used because it
   contains the focal body); **same-name methods** in the focal file (overloads, and same-name methods of nested
   classes) with their Javadoc and code, closest parameter count first, at most 6, ≤2,500 chars each, ≤8,000 in total;
   **caller snippets**: every line matching `\bname\s*\(` in the tracked `.java` files of the main source directory
   (`defects4j export -p dir.src.classes`, `git ls-files`; the test directory is never read, and it is asserted that no
   snippet file lies in it), ±5 lines, excluding the focal method (with its Javadoc) and the included same-name
   methods, windows clipped so that no focal line is shown, overlapping windows merged; ranked: unqualified /
   `this.` / `Class.` calls in the focal file, then `Class.name(` in other files, then other files that mention the
   class, then other calls in the focal file, then the rest; **cap: 8 snippets and 8,000 chars per method**.
   Strict blindness: a same-name method or snippet that shares any 40-char window with the focal body is dropped
   (31 items in 15 methods, e.g. the other buggy `join` overload of Lang_20, which duplicates the focal code). It is
   asserted that no blind pack contains a focal-body window, and that the tracked main sources are unmodified
   (`git diff --quiet HEAD`). Note: the checkouts' git history contains the fixed version; only the working tree is read.
3. **Answers** (`oracle.py answers <arm>`, one call per method and arm). Identical prompt (`ANSWER_PROMPT`) and pack;
   the arms differ only in the section "// The method's implementation:" with the focal body:
   - `oracle_blind`: pack only;
   - `oracle_sees_code`: pack + focal body (control).
   The answerer is "the author of the library"; for each question it gives `{id, reasoning, expected, evidence:[{source,
   quote}]}`, sources `javadoc | caller | overload | class_context | naming | standard | implementation`, and writes
   `UNDETERMINED` when the evidence does not determine the outcome. `implementation` was added to the requested source
   list in both arms ("only if it is shown above") so that the control's reliance on the body is measurable; the prompt
   text is identical in both arms. An answer without any evidence item counts as UNDETERMINED (did not occur).
4. **Docstring** (`oracle.py docs <arm>`): the Advanced docstring unchanged, then
   `// Clarified requirements (answers to questions about the intended behaviour; input → expected):` with one
   `// - <question input> → <expected>` line per determined answer, and `// Undetermined (do not assume):` with
   `// - <input>: <question>` per undetermined one. So m4 (same base + inputs without outcomes) and Advanced Doc are the
   natural references. Tests: unchanged pipeline, `gen_env`, `WITH_CODE=0`.
5. **Evaluation**: `eval_parts.py` (copy of m5's, with its fixed resume logic; paths moved here).
6. **Offline judge** (`judge.py`; the patch is used here only): per method, the questions with both arms' answers as
   A/B in a seeded random order, the buggy body, the in-method fix hunk (m2's `patch_text`) and the trigger tests; per
   question: buggy and fixed behaviour on that input, whether they differ (`relevant`), and BUGGY / FIXED / NEITHER
   (relevant) or SAME / NEITHER (not relevant) per answer. v1 (thinking off, m2-style) over-labelled relevance in my
   check and is kept only for reference (`out/judge_v1.jsonl`); v2 (used) asks for the per-input traces first and runs
   with dynamic thinking (`THINKING_BUDGET=-1`). My own verdicts for validation: `manual_judge.json`.

Leakage: the patch, the fixed version, trigger tests and labels are used only in `judge.py` and `analyze.py`. No
prompt of the method reads anything from a test directory.

## Files
- `oracle.py`: evidence, questions, answers, docstrings, selftest (`python3 m6_agent_oracle/oracle.py selftest`, host).
- `judge.py`: offline judge. `analyze.py`: all RESULTS.md numbers (host python, stdlib) → `out/analysis.txt`,
  plus `out/m_methods.txt` (M tests next to the clarified requirements) and `out/judge_sample.txt`.
- `eval_parts.py`, `run_arm.sh` (docs → test generation, and/or resumed evaluation, for one arm).
- `out/evidence.jsonl` (per method: files, line ranges, same-name methods, snippets, dropped items, leak checks),
  `out/questions.jsonl` (prompt, every attempt with the guard's verdicts, final questions, calls),
  `out/answers_<arm>.jsonl` (prompt, reply, parsed answers, calls), `out/judge.jsonl`, `out/judge_v1.jsonl`,
  `out/<fpf>_parts.json` (evaluation parts), consoles of every step.
- Written outside this folder: `data/prompts/*m6_oracle_*.jsonl`, `data/prompts/rq1/*m6_*`, `data/rq1/logs/*m6_*`,
  `data/rq1/results_test/chatgpt/*m6_*`, and the pipeline's own `run/out/{prompt,testgen,eval}_m6_*`.

## Reproduce (from `EvalAndMitigate/`)
```bash
python3 m6_agent_oracle/oracle.py selftest
bash run/dock.sh -- python3 m6_agent_oracle/oracle.py evidence
# smoke (Cli_32, Lang_20, Lang_40)
bash run/dock.sh -- python3 m6_agent_oracle/oracle.py questions 3 33 53
for a in oracle_blind oracle_sees_code; do
  bash run/dock.sh -- python3 m6_agent_oracle/oracle.py answers $a 3 33 53
  python3 m6_agent_oracle/oracle.py docs $a 3 33 53
  DOC_FILE=Gemini-2-5-flash_buggy_source_data_unified_invoked_with_m6_${a}_smoke.jsonl WITH_CODE=0 \
    FILE_POST_FIX=m6_${a}_smoke bash run/dock.sh gen_env eval_env
done
# full run (the smoke questions/answers are cached and reused)
bash run/dock.sh -- python3 m6_agent_oracle/oracle.py questions
for a in oracle_blind oracle_sees_code; do bash run/dock.sh -- python3 m6_agent_oracle/oracle.py answers $a; done
bash m6_agent_oracle/run_arm.sh oracle_blind gen; bash m6_agent_oracle/run_arm.sh oracle_sees_code gen
bash m6_agent_oracle/run_arm.sh oracle_blind eval  # never two evaluations at once
bash m6_agent_oracle/run_arm.sh oracle_sees_code eval
THINKING_BUDGET=-1 bash run/dock.sh -- python3 m6_agent_oracle/judge.py
python3 m6_agent_oracle/analyze.py > m6_agent_oracle/out/analysis.txt
```
