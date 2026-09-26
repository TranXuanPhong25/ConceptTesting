# STRUT reproduction and fault-relevant seed extension

Date: 2026-09-26 (implementation), 2026-09-27 (empirical results added).
Status: implementation complete and locally verified. The Vertex DNS failure
noted below was later resolved; the Gemini 3 Flash Preview experiment (tuning
subset, then the full 40-function set, all three arms) has since run to
completion and real empirical arm scores are reported in "Results and costs".

## Paper-evidence audit

Target paper: Jinwei Liu, Chao Li, Rui Chen, Shaofeng Li, Bin Gu, and Mengfei
Yang, “STRUT: Structured Seed Case Guided Unit Test Generation for C Programs
using LLMs,” PACMSE 2 (ISSTA 2025), article ISSTA093, pp. 2113–2135,
[DOI 10.1145/3728970](https://doi.org/10.1145/3728970).

I made the following legitimate retrieval attempts before implementation:

- Direct DOI and ACM PDF requests still returned HTTP 403. No paywall bypass was
  attempted.
- The [ISSTA program](https://conf.researchr.org/track/issta-2025/issta-2025-papers)
  confirms title, authors, track, and DOI. The supplied per-paper detail URL was
  inaccessible to the browsing tool.
- General/title/DOI searches, DBLP, Semantic Scholar/OpenAlex/Crossref endpoint
  attempts, author/profile searches, GitHub searches, and searches for
  `UTBench`, `SPARCV8-SUT`, and the Data Availability wording did not locate an
  author-hosted preprint or a resolvable artifact repository. Shell access was
  DNS-blocked; web-index searches worked. The ACM text says “Our artifact is
  publicly available at [8],” but the indexed view did not expose reference [8]
  as a link, and targeted searches did not resolve it. No artifact badge/link was
  visible on the conference listing.
- Importantly, ACM’s legitimate public search index now exposes extensive paper
  text. I read the abstract, approach, implementation, experiment design,
  dataset table, RQ1–RQ4 results, conclusion, and Data Availability statement
  through that index. This is substantially more primary evidence than was
  available in the task’s initial evidence note.

### Verified from the primary paper text

- The three conceptual stages and motivation in the task statement are correct.
- Context comprises dependencies, a focal-method code slice, and interface data
  (types, parameters, globals, return and callees). The implementation used an
  ANTLR V3 commercial parser plus libclang and persisted JSON metadata.
- The structured case is a triple: Inputs, Outputs, and Stubs. An input contains
  ExprInput, Type, Value; an output contains ExprOutput, Type, Value; a stub
  identifies a called-function signature plus returned or modified values.
- STRUT uses one-shot prompting with a seed example. It asks that each case, not
  necessarily the whole suite, be valid JSON; GPT-4o JSON mode was not used.
- Translation rules declare/assign inputs, invoke the focal method, assert
  outputs, and synthesize stub bodies/effects. The industrial translator was
  about 6,400 Java lines; the simplified figure was not its complete behavior.
- After execution, focal methods below 80% coverage receive one uncovered-branch
  feedback iteration; cases adding no branch coverage are discarded. The paper
  reports this adds 4.70 percentage points line and 6.57 points branch coverage.
- The now-readable dataset table reports 1,709 focal methods: bstrlib 139,
  TheAlgorithms/C 287, klib 116, crypto-algorithms 56, xv6-riscv 211, `file`
  307, CTU02 236, C6X-16ST 120, SPARCV8-SUT 44, and UTBench 193. The last four
  include three private industrial systems and a manually constructed benchmark;
  the full artifact itself remains unavailable.
- GPT-4o STRUT results are 96.01% pass, 51.83% oracle-correct, 77.67% line, and
  63.60% branch coverage. Direct GPT-4o is 53.20% pass, 18.93% oracle-correct,
  40.33% line, and 30.58% branch. The paper’s table labels the changes +37.34 and
  +33.02 percentage points (the prose loosely says 37%/33%). DeepSeek-v3 results
  and average paper costs were also visible: STRUT(DS-v3) 91.14% pass, 43.94%
  oracle-correct, 63.60% line, 48.97% branch; average prompt/output 720/1,330
  tokens and reported cost $0.015 GPT-4o or $0.0017 DeepSeek-v3 per generation.

### Reconstructed rather than read exactly

The figures themselves were images, so the exact JSON capitalization/nesting,
the literal prompt wording in Figures 5 and 7, the complete dependency algorithm,
and the production translator’s special cases remain unavailable. This package’s
`Inputs`/`Outputs`/`Stubs` key spelling, array envelope, pointer-offset convention,
prompt prose, parser, and safe C rendering are explicitly reconstructions. The
paper reports no pointer-offset field; it is this implementation’s constrained
encoding. The package does not claim source compatibility with the authors’
artifact.

## Substitute benchmark and protocol

Codeflaws was preferred initially, but it was impractical in this environment:
there was no existing checkout, outbound shell DNS prevented a legitimate
download, and Codeflaws is whole-program contest/defect scoped rather than a
clean library interface corpus. I did not fabricate a replacement and label it
Codeflaws.

The substitute is a fixed 40-function slice of the real Picolibc/Newlib string
library installed with TinyGo 0.41.1 at
`/usr/lib/tinygo/lib/picolibc/newlib/libc/string`. It contains scalar, bounded,
string, wide-string, raw-buffer, mutable-buffer, and pointer-return interfaces.
This directly stresses setup, pointers, capacities, exact oracles, and dependency
handling. All 40 selected sources compiled with GCC 16.2.1 coverage flags. The
first 30 manifest entries are the fixed tuning subset; the full set is all 40.
The package can use another Picolibc checkout via `--picolibc-root`.

Each arm has one `gemini-3-flash-preview` call per function at temperature 0,
thinking budget 0, and maximum 2,400 output tokens:

1. `direct` asks for a complete C harness.
2. `strut` provides the paper-derived triple seed and translates JSON cases.
3. `extended` adds fault-relevant fields but has the same one-call budget.

The full set contains the tuning subset, because the requested protocol called
for subset and full results. This makes the full aggregate partly tuning-exposed;
the ten-function increment is the strictly held-out portion and should also be
reported when the run completes. The implementation does not perform the
paper’s extra below-80% feedback call because that would violate the equal
one-call budget chosen for the extension comparison; this deviation is explicit.

Execution pass is measured per generated function suite, not per individual test
case as in the paper. Coverage is macro-averaged focal-function gcov coverage.
Paired comparisons use per-function differences, a seeded 10,000-resample paired
bootstrap 95% interval, and an exact two-sided sign test with ties removed.

## Extension design and provenance

The baseline triple is extended additively with:

- `InputConstraints`: one atomic validity/boundary rule and probe family per
  argument or discovered guard. This implements AutoCode’s validator/constraint
  lesson (#125) and Specification Grounding’s “one enumerated rule, one test”
  result (#126), avoiding a vague request to “try edge cases.”
- `FaultHypotheses`: each discovered conditional gets an explicit likely
  comparison-direction/equality/termination fault and a required two-sided plus
  boundary test. This follows CodeHacker’s implementation-specific weakness
  hypothesis (#124) and KITE’s semantic bug mechanism tied to a structural
  anchor (#123).
- `PathEffects`: each detected callee is tied to a path condition and an
  observable effect request. This keeps mocks/dependencies path-specific rather
  than merely listing them, matching KITE’s context/anchor idea and grounding
  the hypothesis in an executable route.

The extractor strips comments and preprocessor lines before recognizing calls or
conditions. The translator accepts only typed JSON strings/numbers, creates fixed
capacity mutable buffers, handles numeric/string/pointer-offset oracles, and
rejects C-expression injection. Generated suites return normally on failed
checks so gcov data is flushed. Raw model output is still retained externally
for audit.

## Results and costs

### Local verification

- Repository `tests/` suite: 74 passed (`strut_concept`'s own suite grew from
  9 to 17 tests during the live run below, adding regressions for every bug
  found: escape repair, the libc-macro `#undef`, and return-offset
  normalization), including schema/extension, comment-safe extraction, JSON
  parsing, actual GCC execution and gcov, injection rejection, and paired
  statistics.
- Benchmark preparation: 40/40 selected real Picolibc sources compiled under the
  evaluator’s GCC flags.
- A real Picolibc `strcmp` translated-suite smoke test passed and recorded 4/4
  focal executable lines and 3/4 focal branches, confirming coverage is taken
  from `target.c` rather than the same-named system-header declaration.

### Bugs found and fixed during the live run

Vertex network access was restored and the full experiment (tuning, then the
full 40-function set) was run end to end. Three implementation bugs were found
and fixed along the way, each verified by compiling and executing the
previously-failing generations against the real Picolibc sources before
re-running broadly, plus a regression test:

1. **Raw output was discarded on any post-generation error.** `runner.run()`
   reset the saved raw model text to `""` whenever translation or evaluation
   raised, even if the LLM call itself had already returned content — directly
   contradicting the "raw responses ... are retained externally for audit"
   claim above and making every `generation_error` unauditable. Fixed by only
   resetting the default before the call, not inside the `except`.
2. **C-style `\0`/`\xHH` escapes inside JSON strings were an unrecoverable
   parse failure.** At temperature 0 the model deterministically produced a
   meaningful embedded-null or raw-byte probe (e.g. `"A\0B"`, `"\xff"`) using
   C string-literal syntax instead of JSON's `\u00HH`, which is invalid JSON
   and can never self-correct on retry. This silently zeroed out strut/extended
   data for `strlen`, `strnlen`, `timingsafe_memcmp`, and `memcmp`. Fixed by
   rewriting the two escape forms to valid `\u00HH` before parsing.
3. **Every pointer-returning function in the held-out 10 (`strchr`, `strrchr`,
   `strpbrk`, `strchrnul`, `memchr`, `memrchr`, `rawmemchr`, `strnstr`,
   `memmem`, `strstr`) failed 100% of the time on both structured arms**, via
   two compounding bugs invisible during tuning (none of the 30 tuning
   subjects return a pointer):
   - The model reliably kept `ExprOutput: "return"` and encoded the
     pointer-offset oracle inside `Value` itself (`"return_offset:s1+3"`,
     `"return_offset:s1:3"`, or a bare `null` for an expected NULL), rather
     than the documented `ExprOutput: "return_offset:<base>"`. This is
     unambiguous and never a C expression, so it is now normalized into the
     documented form instead of raising `ValueError: numeric input Value must
     be a JSON number`.
   - Recent glibc/gcc (gcc 16 on the evaluation host) redeclares several
     pointer-returning string/mem functions as a `_Generic`-dispatching macro
     for const-correctness. `benchmark.prepare_source` already `#undef`s the
     focal name for the target source for exactly this reason, but neither
     the translator-generated harness nor the `direct` arm's model-authored
     harness did, so both hit a hard system-header compile error
     (`expected identifier or '(' before '_Generic'`) once the return-offset
     fix above stopped the prior bug from masking it. Fixed by extracting
     `prepare_source`'s undef logic into
     `benchmark.undef_after_last_include()` and applying it to both the
     structured-arm translator output and the `direct` arm's cleaned harness,
     so all three arms face the same environment hazard rather than two of
     them being penalized for it.

   Three `direct`/`extended` result rows (`memchr`/direct, `strstr`/direct,
   `strstr`/extended) had already been cached as `compile_error` from before
   the `#undef` fix existed; `compile_error` rows are not auto-retried by the
   resume-safe runner (only `generation_error` is), so they were reconciled
   by re-running the already-fixed pipeline on the already-saved raw model
   text (no new LLM calls) rather than left stale. `rawmemchr`/direct remains
   a genuine, unrelated model mistake (uses `uintptr_t` without including
   `<stdint.h>`) and was left as `compile_error`.

Two spot checks (see the task record) confirmed the harness measures real
model behavior rather than artifacts: `strcmp`/strut's 8 cases were all
correct against the real Picolibc source, including a byte-level edge case
(`strcmp("\377","\001")` expecting the raw unsigned-byte difference 254, not a
clamped -1/0/1); `strncmp`/strut's failure was traced to a genuine model
mistake (asserted `strncmp("banana","bandana",6) == 1`, but the real value is
negative since `'a' < 'd'` at the first differing byte).

### Gemini tuning subset (30 of 40 functions, 90 calls)

All 90 (30 functions × 3 arms) completed with no residual `generation_error`.

| Arm | Suite pass (oracle-correct) | Line coverage | Branch coverage |
|---|---|---|---|
| direct | 93.3% | 100.0% | 92.7% |
| strut | 60.0% | 95.6% | 83.3% |
| extended | 66.7% | 95.6% | 82.2% |

Paired (per-function difference, seeded 10,000-resample bootstrap 95% CI,
exact two-sided sign test, n=30): strut − direct pass is −33.3pp, CI
[−50.0, −16.7], sign p=0.00195 (significant); strut − direct branch is
−9.5pp, CI [−18.1, −2.6], sign p=0.0156 (significant); strut − direct line is
not significant (p=0.25). extended − strut is not significant on any metric
at this sample size (pass +6.7pp, p=0.69; line/branch ≈0).

### Gemini full set (40 of 40 functions, 120 calls, 119 completed)

| Arm | Suite pass (oracle-correct) | Line coverage | Branch coverage | n |
|---|---|---|---|---|
| direct | 90.0% | 97.5% | 92.1% | 40 |
| strut | 56.4% | 95.8% | 84.7% | 39 |
| extended | 62.5% | 93.5% | 82.6% | 40 |

`strut`/`strchrnul` is the one permanent, non-retryable `generation_error`:
the model used its own parameter names (`s1`, `i`) instead of copying the
seed's exact declared input expressions (`s`, `c`), which the strict
translator correctly rejects (`Inputs expressions must equal ['c', 's']`).
This reproduced identically across 6 retries at temperature 0, so it is
reported as a genuine, deterministic instruction-following miss rather than
retried indefinitely.

Paired (n=39, same statistics as above): strut − direct pass is −33.3pp, CI
[−48.7, −17.9], sign p<0.001 (significant); strut − direct branch is −7.2pp,
CI [−16.0, +1.5], sign p=0.0117 (significant); strut − direct line is not
significant. extended − strut is not significant on any metric (pass +7.7pp,
CI [−7.7, +23.1], p=0.51; line/branch ≈0).

**Interpretation.** Unlike the paper, this harness scores an entire generated
suite as passing only if it compiles, links, runs to completion, *and* every
assertion in every case is true — there is no separate "oracle correctness"
score decomposed from a crash-tolerant "execution pass" the way the paper
reports both (96.01% execution pass vs. 51.83% oracle-correct for STRUT
GPT-4o). Decomposing the two by status shows why `direct` looks stronger here
than the paper's direct-GPT-4o baseline (53.20% execution pass / 18.93%
oracle-correct): all three arms compile/run to completion at a similarly high
rate, but *oracle correctness specifically* is what separates them —

| Arm | Compiles+runs to completion (crash-free) | All assertions correct (suite pass) |
|---|---|---|
| direct | 97.5% (39/40) | 90.0% (36/40) |
| strut | 100% (39/39) | 56.4% (22/39) |
| extended | 100% (40/40) | 62.5% (25/40) |

`direct` writes both the calls *and* the expected values itself, so a wrong
belief about a function's behavior tends to be self-consistent (same mistaken
value on both sides of the assertion) and does not surface as a suite
failure. The structured arms instead commit to an oracle value in the
JSON case *before* the deterministic rule-based translator renders the
assertion, so a wrong belief about behavior (as in the `strncmp` example
above, or the `memchr` case traced during spot-checking where the model
placed the found-byte offset at the position of a *different* occurrence of
the target byte than the one `memchr` actually returns first) is caught as a
real assertion failure rather than staying invisible. Suite-level pass here
is closer to the paper's oracle-correctness metric than to its execution-pass
metric, and the two structured arms' near-universal crash-free execution
(100%, vs. the paper's 77.67%/63.60% line/branch-coverage-implying gap)
suggests the translator itself is not the bottleneck; getting the oracle
value right is.

One evaluator limitation surfaced by this decomposition: `extended`/
`strchrnul` is a `runtime_failure` via a real crash (signal 6/SIGABRT, 0/2
focal lines covered) rather than an assertion failure. The model correctly
identified `strlen` as a genuine dependency to stub (Picolibc's `strchrnul`
really does call it), but the harness's full-signature stub is a plain
non-static top-level `strlen` definition, which can shadow the *entire
process's* use of `strlen` (e.g. inside libc/gcov startup paths), not just
the focal function's call — an architectural limitation of the current
global-symbol stub mechanism, not a scoring bug (the crash is still correctly
counted as a failure). A future version should isolate stubs via
`-Wl,--wrap=<name>` linker wrapping instead of a global redefinition.

### Held-out-10 subset (functions 31–40, never seen during tuning)

The tuning subset (0–29) happens to contain no pointer-returning function, so
this 10-function slice is also the only place the pointer-offset/oracle
mechanics above are exercised at all. Sample sizes are small (n=9–10) and
every CI below is wide, so treat this as directional, not conclusive:

| Arm | Suite pass | Line coverage | Branch coverage | n |
|---|---|---|---|---|
| direct | 80.0% | 90.0% | 90.0% | 10 |
| strut | 44.4% | 96.7% | 89.4% | 9 |
| extended | 50.0% | 87.5% | 83.8% | 10 |

None of the held-out-10 paired comparisons reach significance (all sign-test
p ≥ 0.375; strut − direct pass −33.3pp CI [−77.8, +11.1]; extended − strut
pass +11.1pp CI [−22.2, +44.4]). Coverage on this slice favors the structured
arms over direct more than the full/tuning aggregates do, consistent with
pointer-offset cases exercising more of the not-found/edge branches than a
self-written direct harness tends to.

### Cost

Gemini 3 Flash Preview on Vertex AI is priced at $0.50 / 1M input tokens and
$3.00 / 1M output tokens (confirmed live; same rate this repository's
`codehacker_concept/llm.py` already uses for the same model). Across the 119
successful full-set calls:

| Arm | Input tokens | Output tokens | Cost | Avg / generation |
|---|---|---|---|---|
| direct | 36,686 | 23,081 | $0.0876 | $0.00219 |
| strut | 44,533 | 46,895 | $0.1630 | $0.00418 |
| extended | 65,279 | 47,237 | $0.1744 | $0.00436 |
| **Total** | 146,498 | 117,213 | **$0.4249** | — |

For comparison, the paper reports $0.015/generation for GPT-4o and
$0.0017/generation for DeepSeek-v3; Gemini 3 Flash Preview here is
substantially cheaper per call than either (~$0.002–0.004), consistent with
it being a smaller/flash-tier model, though the structured arms cost roughly
2x direct per call since the seed and (for `extended`) the constraint/
hypothesis/path-effect fields add meaningfully to the prompt and the model
must emit a full JSON case array rather than free-form C.

## Implementation, reproducibility, and limitations

`strut_concept/` contains benchmark metadata/preparation, static extraction,
prompts, safe translation, GCC/gcov evaluation, resume-safe orchestration, and
paired statistics. `results.jsonl` is append-only and fsync'd after every unit;
successful keys are skipped, while generation-error rows are retried. Large
sources/builds/generations were kept in `/tmp/strut-concept-run` because the
sandbox made `~/.cache` read-only; nothing was added to gitignore.

Open issues:

- The authors’ artifact URL and exact figure schemas/prompts remain unresolved.
- Static parsing is intentionally conservative regex/interface metadata, not the
  paper’s industrial ANTLR/libclang analysis. It does not isolate every type,
  global, macro, or dynamically selected dependency.
- Picolibc is narrower than the paper’s ten-project/industrial benchmark. The
  translator safely dispatches per-case return effects for full-signature stubs,
  but callees whose signatures cannot be recovered remain system-linked rather
  than isolated like SunwiseAUnit; changed-pointer stub effects are not yet
  implemented. This benchmark therefore emphasizes pointer/buffer translation.
- A full-signature stub is a plain top-level (non-`static`) function
  definition, so it can shadow the *entire linked program's* use of that name,
  not just the focal function's call site — observed live as a real crash
  (`extended`/`strchrnul` stubbing `strlen`; see "Gemini full set" above). A
  future version should isolate stubs via `-Wl,--wrap=<name>` linker wrapping
  instead of a global redefinition.
- The benchmark sources come from the host installation, so a future run should
  record the exact Picolibc commit/package checksum in addition to TinyGo 0.41.1.
- Suite-level pass (requires every case's assertions to hold, and the run to
  not crash) differs from the paper's case-level pass and cannot be directly
  compared with 96.01%; it is closer in spirit to the paper's oracle-correctness
  metric than to its execution-pass metric (see the "Interpretation" paragraph
  under "Gemini full set").
- `strut`/`strchrnul` is a permanent `generation_error` (the model would not
  copy the seed's exact input parameter names across 6 retries at temperature
  0); this is reported as genuine model behavior rather than retried further.
- An unconstrained repository-root `pytest` also collects `magma/test_llm.py`,
  whose import deliberately exits when a Groq key is absent; `pytest tests` is
  the project test-suite command used here and passes 74/74.
