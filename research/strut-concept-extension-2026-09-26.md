# STRUT reproduction and fault-relevant seed extension

Date: 2026-09-26. Status: implementation complete and locally verified; the
Gemini experiment is blocked before generation by DNS failure to the official
Vertex endpoint. Consequently, no empirical arm scores are claimed.

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

- Repository `tests/` suite: 66 passed, including 9 new package tests
  (schema/extension, comment-safe extraction, JSON
  parsing, actual GCC execution and gcov, injection rejection, paired stats).
- Benchmark preparation: 40/40 selected real Picolibc sources compiled under the
  evaluator’s GCC flags.
- A real Picolibc `strcmp` translated-suite smoke test passed and recorded 4/4
  focal executable lines and 3/4 focal branches, confirming coverage is taken
  from `target.c` rather than the same-named system-header declaration.

### Gemini tuning subset

Not obtained. The first completed request unit (`strcmp`, direct) and the second
(`strcmp`, STRUT) each exhausted five attempts with Vertex HTTP 503 caused by DNS
resolution failure for the official endpoint. The process was stopped before
the extended arm and remaining functions to avoid repeating an environmental
failure. No response content or usage tokens were returned.

### Gemini full set

Not run, because the required tuning phase did not produce generations. It would
be misleading to report zero coverage/pass as model results: these are missing
data, not negative model outcomes.

### Cost

Observed token usage is 0 input and 0 output tokens and observed billable cost is
$0. Google’s current pricing page states that non-200 responses are not charged.
When resumed, the journal captures provider token metadata per arm and function;
cost should be calculated from the then-current official Vertex price rather
than frozen into code. This experiment substitutes Gemini 3 Flash Preview for
the paper’s GPT-4o, as required.

## Implementation, reproducibility, and limitations

`strut_concept/` contains benchmark metadata/preparation, static extraction,
prompts, safe translation, GCC/gcov evaluation, resume-safe orchestration, and
paired statistics. `results.jsonl` is append-only and fsync'd after every unit;
successful keys are skipped, while generation-error rows are retried. Large
sources/builds/generations were kept in `/tmp/strut-concept-run` because the
sandbox made `~/.cache` read-only; nothing was added to gitignore.

Open issues:

- Vertex DNS/network access must be restored, then `tune`, prompt freeze review,
  and `full` must be run. No empirical extension conclusion is possible yet.
- The authors’ artifact URL and exact figure schemas/prompts remain unresolved.
- Static parsing is intentionally conservative regex/interface metadata, not the
  paper’s industrial ANTLR/libclang analysis. It does not isolate every type,
  global, macro, or dynamically selected dependency.
- Picolibc is narrower than the paper’s ten-project/industrial benchmark. The
  translator safely dispatches per-case return effects for full-signature stubs,
  but callees whose signatures cannot be recovered remain system-linked rather
  than isolated like SunwiseAUnit; changed-pointer stub effects are not yet
  implemented. This benchmark therefore emphasizes pointer/buffer translation.
- The benchmark sources come from the host installation, so a future run should
  record the exact Picolibc commit/package checksum in addition to TinyGo 0.41.1.
- Suite-level pass differs from the paper’s case-level pass and cannot be directly
  compared with 96.01%.
- An unconstrained repository-root `pytest` also collects `magma/test_llm.py`,
  whose import deliberately exits when a Groq key is absent; `pytest tests` is
  the project test-suite command used here and passes 64/64.
