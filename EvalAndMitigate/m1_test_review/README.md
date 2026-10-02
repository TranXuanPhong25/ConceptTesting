# m1_test_review: spec-grounded review layer between test generation and evaluation

## Method
A reviewer LLM pass (Gemini 2.5 Flash, thinking off, temperature 0) runs after test generation and before evaluation.
For each generated test file it makes one call and decides per `@Test` method:

- **KEEP**: every assertion traces to a specific sentence of the spec (the generated docstring).
- **ABSTAIN**: an assertion checks behaviour the spec does not state, an expected value cannot be derived from the
  spec ("magic" value), or the test mixes specified and unspecified behaviour. Abstained methods are removed.
- **REWRITE**: only when a test explicitly contradicts the spec, or misuses the API/setup. Every changed expected
  value must be logged with the spec sentence that states or implies the new value. A rewrite that does not parse
  as a single `@Test` method is turned into ABSTAIN.

Values that follow from a spec sentence plus a well-known standard the sentence names (Base64, ISO-8601, documented
JDK semantics) or plain arithmetic count as derived. This clause was added after the first 3-record smoke run, in
which the reviewer abstained on every literal Base64 value in Codec_7 even though the spec says "Base64". That was
the only prompt change, and it was made before the full runs.

### Design constraint: the reviewer is blind to execution results and to the focal method body
Effective tests (E) are exactly the tests that **fail on the buggy code**. A reviewer that sees pass/fail on the
buggy code, and then drops or "fixes" the failing tests, erases E by construction. The upstream pipeline's own
repair loop does exactly that: its post-repair counters show E=0, while the pre-repair "reported" counters show
E=70 (Doc W/ Code). A reviewer that sees the focal method body has the same problem, because it would align the
tests with the buggy implementation (the misguidance effect this paper measures). So the reviewer input is only:

1. the test-generation prompt (`content` field of the completion record: docstring + signature/class context;
   no focal body in the docstring-only configs), and
2. the generated test file (the first ```java block of `completion`).

No fix metadata, patch, trigger test or fixed version enters any prompt.

The reviewed completion keeps the same markdown/```java format. Abstained methods are cut out of the file with
tree-sitter byte ranges and rewritten ones are spliced in, so imports, fields, `@Before` and helpers stay as they
were and the file still compiles. Three Advanced Doc completions (Lang_16, Lang_36, Lang_58) are truncated and
have no closing fence. The evaluator skips them anyway, so they pass through unchanged and get no reviewer call.

## Files
- `review.py`: the reviewer (runs in the container). `python3 m1_test_review/review.py selftest` checks the splicing.
- `analyze.py`: all RESULTS.md numbers from the evaluation logs (host python, stdlib). It recovers per-test outcomes
  from the "Reported execution results" failing-test lists, so the baseline categories of the abstained tests
  come from the existing baseline logs and need no extra evaluation.
- `eval_parts.py`: runs `run/dock.sh eval_env` for an arm and resumes after the evaluator's transient crashes.
- `out/<arm>_decisions.jsonl`: per-test decision log (id, method_signature, test, decision, reason, spec_quote,
  value_changes, note).
- `out/<arm>_raw.jsonl`: raw reviewer replies (also a resume cache, keyed by id|method_signature).
- Reviewed completions: `data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_<arm>_with_completion.jsonl`.

## Reproduce (from `EvalAndMitigate/`)
```bash
# smoke test (3 records)
bash run/dock.sh -- python3 m1_test_review/review.py unified_invoked_docstring_prompt m1_review_onlydoc_smoke Cli_1_buggy Codec_7_buggy Csv_4_buggy
FILE_POST_FIX=m1_review_onlydoc_smoke bash run/dock.sh eval_env
# arm 1: Only Doc
bash run/dock.sh -- python3 m1_test_review/review.py unified_invoked_docstring_prompt m1_review_onlydoc
python3 m1_test_review/eval_parts.py m1_review_onlydoc       # = FILE_POST_FIX=m1_review_onlydoc bash run/dock.sh eval_env, resumed after crashes
python3 m1_test_review/eval_parts.py m1_review_onlydoc --redo 1 57   # blocks whose run failed with an empty error report
python3 m1_test_review/analyze.py unified_invoked_docstring_prompt m1_review_onlydoc
# arm 2: Advanced Doc
bash run/dock.sh -- python3 m1_test_review/review.py unified_invoked_advanced_docstring_prompt m1_review_advdoc
python3 m1_test_review/eval_parts.py m1_review_advdoc
python3 m1_test_review/analyze.py unified_invoked_advanced_docstring_prompt m1_review_advdoc
```
`review.py` caches reviewer replies in `out/<arm>_raw.jsonl`, so a rerun rebuilds the reviewed completions without
new LLM calls. `eval_parts.py` records which log blocks count in `out/<arm>_parts.json` (see its docstring). The
Only Doc plan was seeded by hand from the first whole-arm log that crashed after 38 finished blocks.

The control (random abstention at the same per-config rate r) needs no LLM calls and no evaluation. Every test is
dropped independently with probability r, so the expected M/E/FP counts are the baseline counts times (1 - r),
red-precision stays the same, and the expected number of methods with ≥1 E is Σ_i (1 - r^{E_i}) over the
baseline per-method E counts (the same formula gives ≥1 M). `analyze.py` computes all of these.
