# m7_property_oracle: relation-only (property) oracles vs example oracles

## Question
In m1-m6, oracles written from the buggy code copied the bug. m3's concept spec raised the number of methods with
≥1 M from 3 to 16, and m6's sees-code answerer gave 8 vs 2. Blind arms were safe but added nothing over the Advanced
docstring. This arm asks whether **relation-only oracles** avoid copying the bug when both arms get the same
information. Examples of such relations: `unescape(escape(x)) == x`, "overload A agrees with overload B", "result
length ≤ maxWidth". A relation does not state a concrete output that a docstring derived from the buggy code could have
baked in. It can still catch the bug when the bug breaks the relation.

## Method (pre-registered; one prompt revision allowed and used, see below)
There are two arms. Each makes one test-generation call per method (Gemini 2.5 Flash via Vertex, thinking off, T=0,
`run/gemini_shim.py`). Both arms use the same information and the same call budget, and differ only in one
assertion-form paragraph.

Prompt = the upstream **Advanced-Doc test-generation prompt**, unchanged (`content` of
`data/prompts/rq1/Gemini-2-5-flash_comment_generation_full_buggy_unified_invoked_advanced_docstring_prompt.jsonl`).
The following blocks are appended to it:
1. **Blind evidence pack**: m6's `m6_agent_oracle/out/evidence.jsonl`, which is already leak-checked, with m6's caps:
   the declaration, the method's original Javadoc, the class Javadoc, same-name methods (≤6, ≤2,500 chars each,
   ≤8,000 in total) and caller snippets from the main source dir (≤8, ≤8,000 chars). The class context that the base
   prompt already lists (constructors, fields, signatures) is not repeated (`gen.py pack`).
2. **Relation candidates** (`relations.py`, no LLM, regex over the dataset's signature lists and the pack; the class
   code field, which contains the focal body, is never read):
   - R1 inverse / round-trip partners found by verb pairs (escape/unescape, encode/decode, join/split, format/parse,
     add/remove, to/from|parse|valueOf, …). The partner must be a non-private method of the class or a `Class.method` /
     `{@link}` named in the pack. Class-level pairs (…Unescaper/…Escaper, Reader/Writer, InputStream/OutputStream) are
     listed only if the partner class is named in the pack.
   - R2 overloads (from the signature list and m6's same-name methods, closest parameter list first) and siblings
     (Any/None complement, is/isNot, Left/Right mirror, IgnoreCase variant, Date/DateTime delegating variants).
   - R3-R5 as generic families (documented invariants, metamorphic, JDK equivalent only when the Javadoc claims it).
   - Found: R1 in 20 methods, R2 in 43. Both arms see the same block.
3. **Assertion-form paragraph** (`gen.py FORM`), the only difference between the arms:
   - `m7_prop`: every assertion relates ≥2 values computed in the test. No literal expected output of the focal method,
     unless the exact input/output pair is quoted from the original Javadoc in the evidence, marked `// from Javadoc`.
     Exceptions only where the original Javadoc states them.
   - `m7_example` (control): one concrete expected value per input, from the documentation and the relation context.
   - Then a shared tail line (output format).

Leakage: the appended part of every prompt is asserted to contain no 40-char window of the focal body (m5's
`body_leaks`). The base prompt is the upstream Advanced-Doc prompt. 3 of its 78 prompts already contain a body window,
because the Advanced docstrings quote it (Lang_36, Lang_3, Lang_44 `createNumber`). They are inherited unchanged and
are in the Advanced Doc baseline too. No patch, fixed version, trigger test or fix metadata enters any prompt; those are
used only by the evaluation.

Re-asks: only for an unparsable reply (no ```java block with a public class and an @Test), at T=0.5, at most 2.
Completion records use the baseline `_with_completion.jsonl` format (Advanced-Doc record, `content` = our prompt,
`completion`, `reasoning_token_count`).

**Prompt revision (the one allowed).** In the smoke run (Cli_32, Lang_20, Lang_40), 68% of the v1 prop tests had an
unmarked LITERAL oracle, above the 30% threshold. v2 changed both paragraphs in the same way:
- an "ASSERTION STYLE (mandatory, it overrides …)" header;
- explicit allowed and forbidden assertion forms (for example `assertEquals("a,b", m(...))`, or
  `assertTrue(m("abc"))` forbidden in prop);
- "reach coverage through many inputs";
- a final self-check sentence.

v2 prop smoke: 77% unmarked LITERAL. No further changes were made. The v1 text, completions and compliance are in
`out/v1_smoke/`.

## Compliance tool (`form.py`, offline)
Each assertion of each @Test method is classified as LITERAL, RELATION or THROWS. See the module docstring for the
exact rules. In short:
- **LITERAL**: assertEquals/Same/ArrayEquals, `assertTrue(a == b)` and `a.equals(b)`, or `assertThat(a, is(b))`, where
  one side is a literal and the other side is derived from the focal method; also assertNull/True/False applied
  directly to a focal call.
  - "Literal" covers Java literals, constants, constant arrays, boxing wrappers, constructors of literals, test helpers
    with literal arguments, and local variables assigned only such values.
  - "Focal-derived" covers a focal call, a variable assigned from one, or the receiver or a mutable argument of a focal
    call (side effects).
  - A literal variable that also feeds the other side (`assertEquals(x, unescape(escape(x)))`) counts as a relation.
- **THROWS**: `fail`, `assertThrows`, `@Test(expected)`, `.expect(`, and assertions on a caught exception.
- **RELATION**: everything else, including assertNotNull and relational bounds.
- A test is "unmarked LITERAL" if it has ≥1 LITERAL without `// from Javadoc`.
- Check on the existing baselines: 75% of Advanced Doc tests have ≥1 LITERAL, 16% are THROWS-only, 9% RELATION.

## Files
- `gen.py`: prompts and test generation (container, LLM); `python3 m7_property_oracle/gen.py prompts` gives the leak
  check and sizes (host).
- `relations.py`: relation candidates; `relations.py selftest`, or `relations.py [idx]` to print the blocks.
- `form.py`: assertion-form classifier and compliance; `form.py selftest`, `form.py <FILE_POST_FIX ...>`.
- `eval_parts.py`: resumed evaluation, a copy of m6's with paths moved here. It **always passes `NO_ADC=1`**, so
  `run/dock.sh` mounts no gcloud credentials while LLM-written Java compiles and runs.
- `analyze.py`: all RESULTS.md numbers (host python, stdlib) → `out/analysis.txt`, plus `out/me_tests.txt` (every M/E
  test of both arms with its form label and source).
- `out/gen_<arm>.jsonl`: per method, the prompt, completion, calls and temperature (also the resume cache).
  `out/<fpf>_parts.json` holds the evaluation parts. Also in `out/`: consoles, and `v1_smoke/` (the prompt before the
  revision).
- Written outside this folder (all new files):
  - `data/prompts/rq1/*m7_*`;
  - `data/rq1/logs/*m7_*`;
  - `data/rq1/results_test/chatgpt/*m7_*`;
  - the pipeline's own `run/out/eval_m7_*`.

## Reproduce (from `EvalAndMitigate/`)
```bash
python3 m7_property_oracle/relations.py selftest && python3 m7_property_oracle/form.py selftest
python3 m7_property_oracle/gen.py prompts                      # leak check of every prompt (host)
# smoke (Cli_32, Lang_20, Lang_40); generation needs credentials, evaluation must not have them
bash run/dock.sh -- python3 m7_property_oracle/gen.py prop 3 33 53
bash run/dock.sh -- python3 m7_property_oracle/gen.py example 3 33 53
NO_ADC=1 FILE_POST_FIX=m7_prop_smoke bash run/dock.sh eval_env
NO_ADC=1 FILE_POST_FIX=m7_example_smoke bash run/dock.sh eval_env
python3 m7_property_oracle/form.py m7_prop_smoke m7_example_smoke
# full run, strictly one step at a time (the smoke records are reused from the cache)
bash run/dock.sh -- python3 m7_property_oracle/gen.py prop
bash run/dock.sh -- python3 m7_property_oracle/gen.py example
# Gson_14 was regenerated after fixing the parse check for `$` class names (see RESULTS.md, LLM calls)
bash run/dock.sh -- python3 m7_property_oracle/gen.py prop redo 16 17
bash run/dock.sh -- python3 m7_property_oracle/gen.py example redo 16 17
python3 m7_property_oracle/eval_parts.py m7_prop            # sets NO_ADC=1 itself
python3 m7_property_oracle/eval_parts.py m7_example
python3 m7_property_oracle/eval_parts.py m7_prop --redo 27 28   # glitched blocks (empty error report), once
python3 m7_property_oracle/eval_parts.py m7_example --redo 4
python3 m7_property_oracle/form.py
python3 m7_property_oracle/analyze.py > m7_property_oracle/out/analysis.txt
```
